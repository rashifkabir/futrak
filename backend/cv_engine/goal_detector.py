import cv2
import os
import numpy as np
from ultralytics import YOLO
from dotenv import load_dotenv
from models.onnx_detector import get_local_model

load_dotenv(dotenv_path=".env")

# Custom model (bump version for v5 later) — same model that
# detects the ball; class "goalpost" is class 1.
ROBOFLOW_MODEL_ID   = "propathfc-detection/4"
GOALPOST_CONFIDENCE = 0.50

# ─────────────────────────────────────────────────────
# FA STANDARD GOAL DIMENSIONS
# ─────────────────────────────────────────────────────

GOAL_SIZES = {
    "5-a-side small (12x4ft)": {
        "width_m":  3.66,
        "height_m": 1.22,
        "ratio":    3.00
    },
    "5-a-side large (16x4ft)": {
        "width_m":  4.88,
        "height_m": 1.22,
        "ratio":    4.00
    },
    "7-a-side (12x6ft)": {
        "width_m":  3.66,
        "height_m": 1.83,
        "ratio":    2.00
    },
    "9-a-side (16x7ft)": {
        "width_m":  4.88,
        "height_m": 2.13,
        "ratio":    2.29
    },
    "11-a-side youth (21x7ft)": {
        "width_m":  6.40,
        "height_m": 2.13,
        "ratio":    3.01
    },
    "11-a-side standard (24x8ft)": {
        "width_m":  7.32,
        "height_m": 2.44,
        "ratio":    3.00
    }
}

PERSON_CLASS = 0


class GoalDetector:

    def __init__(self):
        print("Loading YOLO for goalkeeper detection...")
        self.model = YOLO("yolov8n.pt")
        print("Loading local ProPath model for goalposts (ONNX)...")
        self.custom_model = get_local_model()  # local ONNX, no credits
        print("GoalDetector ready")

    # ─────────────────────────────────────────
    # MAIN — SCAN VIDEO FOR BEST GOAL FRAME
    # ─────────────────────────────────────────

    def find_goal_in_video(
        self,
        video_path:       str,
        player_height_cm: float = 170.0
    ) -> dict:
        cap          = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        best_result  = None
        best_conf    = 0.0
        frame_num    = 0

        print(f"Scanning {total_frames} frames for goal...")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % 10 == 0:
                result = self.detect_goal_in_frame(
                    frame, player_height_cm
                )
                if (result["detected"] and
                        result["confidence"] > best_conf):
                    best_conf   = result["confidence"]
                    best_result = result
                    best_result["frame"] = frame_num
                    print(f"  Goal at frame {frame_num} "
                          f"— conf {best_conf:.2f} "
                          f"— {result.get('goal_type','?')}")

                    if best_conf > 0.85:
                        print("High confidence — stopping early")
                        break

            frame_num += 1

        cap.release()

        if not best_result:
            print("No goal detected")
            return {
                "detected":   False,
                "reason":     "No goal found — ensure the full "
                              "goal is visible in frame",
                "goalkeeper": {"present": False}
            }

        print(f"Initial detection: {best_result['goal_type']} "
              f"(conf {best_result['confidence']:.2f})")

        # ── Goalkeeper detection on best frame ───
        cap2 = cv2.VideoCapture(video_path)
        cap2.set(
            cv2.CAP_PROP_POS_FRAMES,
            best_result.get("frame", 0)
        )
        ret, frame = cap2.read()
        cap2.release()

        if ret:
            gk = self.detect_goalkeeper(
                frame, best_result["bbox"]
            )
            best_result["goalkeeper"] = gk

            # ── Goalkeeper-anchored refinement ───────
            # If goalkeeper detected, recompute goal bbox
            # from their position — far more accurate than
            # white structure detection alone
            if gk.get("present"):
                keeper_anchored = self.goal_from_goalkeeper(
                    gk,
                    goal_type_hint=best_result.get(
                        "goal_type",
                        "11-a-side standard (24x8ft)"
                    )
                )
                if keeper_anchored:
                        if best_result.get("post_left") is not None:
                            keeper_anchored["post_left"]  = best_result["post_left"]
                            keeper_anchored["post_right"] = best_result["post_right"]
                            keeper_anchored["bbox"] = (
                                best_result["post_left"],
                                keeper_anchored["crossbar_y"],
                                best_result["post_right"],
                                keeper_anchored["ground_y"]
                            )
                        keeper_anchored["zones"] = \
                            self._calculate_zones(keeper_anchored)
                        keeper_anchored["goalkeeper"] = gk
                        best_result.update(keeper_anchored)
                        print(f"[Goal] Hybrid bbox: "
                              f"x={keeper_anchored['post_left']}-"
                              f"{keeper_anchored['post_right']} "
                              f"y={keeper_anchored['crossbar_y']}-"
                              f"{keeper_anchored['ground_y']}")

        return best_result

    # ─────────────────────────────────────────
    # GOALKEEPER-ANCHORED GOAL BBOX
    # ─────────────────────────────────────────

    def goal_from_goalkeeper(
        self,
        goalkeeper:     dict,
        goal_type_hint: str = "11-a-side standard (24x8ft)"
    ) -> dict | None:
        """
        Computes goal bounding box from goalkeeper position.

        More reliable than white structure detection because:
        - Goalkeeper is large and clearly detected by YOLO
        - Goalkeeper is definitionally inside the goal
        - Keeper height gives accurate px/metre calibration
        - Works on any background — no colour dependency

        Uses keeper height to calibrate pixels per metre,
        then derives crossbar and post positions from
        known FA goal dimensions.
        """
        if not goalkeeper.get("present"):
            return None

        px1, py1, px2, py2 = goalkeeper["bbox"]
        keeper_height_px    = py2 - py1

        if keeper_height_px < 10:
            return None

        # Average goalkeeper height 185cm
        keeper_height_cm = 185.0
        px_per_cm        = keeper_height_px / keeper_height_cm
        px_per_m         = px_per_cm * 100

        dims = GOAL_SIZES.get(
            goal_type_hint,
            GOAL_SIZES["11-a-side standard (24x8ft)"]
        )
        goal_w_m = dims["width_m"]
        goal_h_m = dims["height_m"]

        goal_h_px  = int(goal_h_m * px_per_m)
        goal_w_px  = int(goal_w_m * px_per_m)

        # Keeper feet = goal ground level
        ground_y   = py2
        crossbar_y = py2 - goal_h_px

        # Use keeper HEIGHT only to calculate goal HEIGHT
        # Do NOT use keeper for goal width — too unreliable
        # at distance. Goal X positions come from the
        # crossbar detection which is accurate.
        keeper_cx  = (px1 + px2) // 2
        post_left  = keeper_cx - goal_w_px // 2
        post_right = keeper_cx + goal_w_px // 2

        print(f"[Goal] Keeper-anchored: "
              f"x={post_left}-{post_right} "
              f"y={crossbar_y}-{ground_y} "
              f"({goal_w_px}x{goal_h_px}px)")

        return {
            "detected":      True,
            "bbox":          (post_left, crossbar_y,
                              post_right, ground_y),
            "post_left":     post_left,
            "post_right":    post_right,
            "crossbar_y":    crossbar_y,
            "ground_y":      ground_y,
            "goal_type":     goal_type_hint,
            "goal_width_m":  goal_w_m,
            "goal_height_m": goal_h_m,
            "confidence":    0.90
        }

    # ─────────────────────────────────────────
    # SINGLE FRAME DETECTION
    # ─────────────────────────────────────────

    def detect_goal_via_custom_model(
        self,
        frame: np.ndarray,
        w: int,
        h: int,
        player_height_cm: float = 170.0
    ) -> dict:
        """
        PRIMARY goal detector — custom ProPath goalpost model.
        Far more reliable than white-structure methods. Returns
        the highest-confidence goalpost bbox, or {"detected": False}.
        """
        try:
            results = self.custom_model.infer(
                frame, confidence=GOALPOST_CONFIDENCE
            )[0]
        except Exception as e:
            print(f"[goal] custom model inference failed: {e}")
            return {"detected": False, "confidence": 0.0}

        best = None
        best_conf = 0
        for p in results.predictions:
            if p.class_name != "goalpost":
                continue
            if p.confidence > best_conf:
                best_conf = p.confidence
                cx, cy, bw, bh = p.x, p.y, p.width, p.height
                best = (int(cx - bw/2), int(cy - bh/2),
                        int(cx + bw/2), int(cy + bh/2),
                        int(bw), int(bh))
        if best is None:
            return {"detected": False, "confidence": 0.0}

        x1, y1, x2, y2, bw, bh = best
        return {
            "detected":   True,
            "confidence": round(float(best_conf), 3),
            "goal_type":  "custom_model",
            "bbox":       (x1, y1, x2, y2),
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "width_px":  bw,
            "height_px": bh,
            "method":    "custom_model",
        }

    def detect_goal_in_frame(
        self,
        frame:            np.ndarray,
        player_height_cm: float = 170.0
    ) -> dict:
        h, w = frame.shape[:2]

        # PRIMARY: custom goalpost model (reliable, ~0.9 conf)
        r0 = self.detect_goal_via_custom_model(
            frame, w, h, player_height_cm
        )
        if r0["detected"] and r0["confidence"] > GOALPOST_CONFIDENCE:
            return r0


        r1 = self._detect_via_crossbar(
            frame, w, h, player_height_cm
        )
        if r1["detected"] and r1["confidence"] > 0.40:
            return r1

        r2 = self._detect_via_contours(
            frame, w, h, player_height_cm
        )
        if r2["detected"] and r2["confidence"] > 0.50:
            return r2

        r3 = self._detect_via_hough(
            frame, w, h, player_height_cm
        )

        results = [r for r in [r1, r2, r3] if r["detected"]]
        if results:
            return max(results,
                       key=lambda r: r["confidence"])

        return {"detected": False, "confidence": 0.0}

    # ─────────────────────────────────────────
    # METHOD 1 — CROSSBAR-FIRST
    # ─────────────────────────────────────────

    def _detect_via_crossbar(
        self,
        frame:            np.ndarray,
        frame_w:          int,
        frame_h:          int,
        player_height_cm: float
    ) -> dict:
        roi_top   = int(frame_h * 0.05)
        roi_frame = frame[roi_top:, :]

        hsv   = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv,
                            np.array([0,   0, 185]),
                            np.array([180, 45, 255]))
        mask2 = cv2.inRange(hsv,
                            np.array([0,   0, 155]),
                            np.array([180, 38, 255]))
        white_mask = cv2.bitwise_or(mask1, mask2)

        kernel     = np.ones((3, 3), np.uint8)
        white_mask = cv2.morphologyEx(
            white_mask, cv2.MORPH_CLOSE, kernel, iterations=2
        )

        contours, _ = cv2.findContours(
            white_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 80:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            if h == 0:
                continue
            ratio = w / h
            if ratio > 2.0 and w > frame_w * 0.08:
                candidates.append({
                    "x1": x, "x2": x + w,
                    "y":  y + h // 2,
                    "y1": y, "y2": y + h,
                    "w":  w, "h": h,
                    "ratio": ratio, "area": area
                })

        if not candidates:
            return {"detected": False, "confidence": 0.0}

        merged = self._merge_crossbar_fragments(
            candidates, frame_w
        )

        if not merged:
            return {"detected": False, "confidence": 0.0}

        best      = None
        best_conf = 0.0

        for cb in merged:
            goal_w     = cb["x2"] - cb["x1"]
            crossbar_y = cb["y"] + roi_top

            if goal_w < frame_w * 0.08:
                continue

            # Reject detections wider than 90% of frame
            # These are walls, fences or pitch markings
            if goal_w > frame_w * 0.90:
                continue
            
            if goal_w > frame_w * 0.9:
                continue

            post_height = self._estimate_post_height(
                roi_frame, cb["x1"], cb["x2"],
                cb["y"], frame_h - roi_top
            )

            if post_height and post_height > goal_w * 0.15:
                goal_h_px = post_height
            else:
                goal_h_px = int(goal_w / 3.0)

            ground_y = min(crossbar_y + goal_h_px, frame_h)
            conf     = min(0.75, 0.45 + (goal_w / frame_w) * 0.5)

            if conf > best_conf:
                best_conf = conf
                size_hint = self._best_width_guess(
                    goal_w, frame_w, frame_h, player_height_cm
                )
                best = {
                    "detected":      True,
                    "bbox":          (cb["x1"], crossbar_y,
                                      cb["x2"], ground_y),
                    "post_left":     cb["x1"],
                    "post_right":    cb["x2"],
                    "crossbar_y":    crossbar_y,
                    "ground_y":      ground_y,
                    "confidence":    conf,
                    "goal_type":     size_hint.get(
                                         "goal_type", "detected"
                                     ),
                    "goal_width_m":  size_hint.get("goal_width_m"),
                    "goal_height_m": size_hint.get("goal_height_m"),
                    "detected_w_m":  None,
                    "detected_h_m":  None
                }

        if best:
            best["zones"] = self._calculate_zones(best)
        return best or {"detected": False, "confidence": 0.0}

    # ─────────────────────────────────────────
    # POST HEIGHT ESTIMATOR
    # ─────────────────────────────────────────

    def _estimate_post_height(
        self,
        roi_frame:      np.ndarray,
        left_x:         int,
        right_x:        int,
        crossbar_y_roi: int,
        max_height:     int
    ) -> int | None:
        h, w   = roi_frame.shape[:2]
        sw     = max(8, int((right_x - left_x) * 0.05))
        best_h = 0

        for post_x in [left_x, right_x]:
            x0 = max(0, post_x - sw)
            x1 = min(w, post_x + sw)
            if x1 <= x0:
                continue

            strip = roi_frame[crossbar_y_roi:, x0:x1]
            if strip.size == 0:
                continue

            hsv   = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
            mask1 = cv2.inRange(hsv,
                                np.array([0,   0, 170]),
                                np.array([180, 50, 255]))
            mask2 = cv2.inRange(hsv,
                                np.array([0,   0, 145]),
                                np.array([180, 40, 255]))
            white      = cv2.bitwise_or(mask1, mask2)
            row_sums   = np.sum(white, axis=1) / 255
            threshold  = sw * 0.3
            white_rows = np.where(row_sums > threshold)[0]

            if len(white_rows) > 3:
                ph = int(white_rows[-1])
                if ph > best_h:
                    best_h = ph

        return best_h if best_h > 10 else None

    # ─────────────────────────────────────────
    # CROSSBAR FRAGMENT MERGER
    # ─────────────────────────────────────────

    def _merge_crossbar_fragments(
        self,
        candidates: list,
        frame_w:    int
    ) -> list:
        if not candidates:
            return []

        candidates.sort(key=lambda c: c["x1"])
        groups = []
        used   = [False] * len(candidates)

        for i, c in enumerate(candidates):
            if used[i]:
                continue
            group   = [c]
            used[i] = True

            for j, d in enumerate(candidates):
                if used[j] or i == j:
                    continue
                if abs(c["y"] - d["y"]) < 25:
                    gap = max(
                        d["x1"] - c["x2"],
                        c["x1"] - d["x2"],
                        0
                    )
                    if gap < frame_w * 0.25:
                        group.append(d)
                        used[j] = True

            groups.append(group)

        merged = []
        for group in groups:
            x1      = min(c["x1"] for c in group)
            x2      = max(c["x2"] for c in group)
            y       = int(np.mean([c["y"] for c in group]))
            total_w = x2 - x1

            if total_w > frame_w * 0.08:
                merged.append({
                    "x1": x1, "x2": x2, "y": y,
                    "w":  total_w,
                    "n_fragments": len(group)
                })

        merged.sort(key=lambda m: m["w"], reverse=True)
        return merged

    # ─────────────────────────────────────────
    # METHOD 2 — FULL CONTOUR
    # ─────────────────────────────────────────

    def _detect_via_contours(
        self,
        frame:            np.ndarray,
        frame_w:          int,
        frame_h:          int,
        player_height_cm: float
    ) -> dict:
        roi_top   = int(frame_h * 0.05)
        roi_frame = frame[roi_top:, :]

        hsv   = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv,
                            np.array([0,   0, 185]),
                            np.array([180, 45, 255]))
        mask2 = cv2.inRange(hsv,
                            np.array([0,   0, 155]),
                            np.array([180, 38, 255]))
        white_mask = cv2.bitwise_or(mask1, mask2)

        kernel     = np.ones((3, 3), np.uint8)
        white_mask = cv2.morphologyEx(
            white_mask, cv2.MORPH_CLOSE, kernel, iterations=2
        )

        contours, _ = cv2.findContours(
            white_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        best      = None
        best_conf = 0.0
        min_area  = frame_w * frame_h * 0.001

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            x, y, cw, ch = cv2.boundingRect(cnt)
            y_actual = y + roi_top

            if ch == 0:
                continue

            ratio = cw / ch
            if not (1.3 <= ratio <= 5.5):
                continue

            match, conf = self._match_goal_size_full(
                cw, ch, frame_w, frame_h, player_height_cm
            )

            if match and conf > best_conf:
                best_conf = conf
                best = {
                    "detected":      True,
                    "bbox":          (x, y_actual,
                                      x + cw, y_actual + ch),
                    "post_left":     x,
                    "post_right":    x + cw,
                    "crossbar_y":    y_actual,
                    "ground_y":      y_actual + ch,
                    "confidence":    conf,
                    **match
                }

        if best:
            best["zones"] = self._calculate_zones(best)
            return best

        return {"detected": False, "confidence": 0.0}

    # ─────────────────────────────────────────
    # METHOD 3 — HOUGH LINES
    # ─────────────────────────────────────────

    def _detect_via_hough(
        self,
        frame:            np.ndarray,
        frame_w:          int,
        frame_h:          int,
        player_height_cm: float
    ) -> dict:
        roi_top   = int(frame_h * 0.05)
        roi_frame = frame[roi_top:, :]

        gray    = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blurred, 40, 120)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=40,
            minLineLength=frame_h * 0.03,
            maxLineGap=15
        )

        if lines is None:
            return {"detected": False, "confidence": 0.0}

        vertical_lines   = []
        horizontal_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(
                np.arctan2(y2 - y1, x2 - x1)
            ))
            if angle < 25 or angle > 155:
                horizontal_lines.append(line[0])
            elif 65 < angle < 115:
                vertical_lines.append(line[0])

        if len(vertical_lines) < 2 or \
                len(horizontal_lines) < 1:
            return {"detected": False, "confidence": 0.0}

        vertical_lines.sort(
            key=lambda l: (l[0] + l[2]) / 2
        )

        best      = None
        best_conf = 0.0

        for i in range(len(vertical_lines)):
            for j in range(i + 1, len(vertical_lines)):
                lx = int((vertical_lines[i][0] +
                           vertical_lines[i][2]) / 2)
                rx = int((vertical_lines[j][0] +
                           vertical_lines[j][2]) / 2)
                cw = rx - lx

                if cw < frame_w * 0.03:
                    continue

                for hl in horizontal_lines:
                    hx1, hy1, hx2, hy2 = hl
                    hxmin = min(hx1, hx2)
                    hxmax = max(hx1, hx2)

                    if not (hxmin <= lx + cw * 0.3 and
                            hxmax >= rx - cw * 0.3):
                        continue

                    crossbar_y = (
                        int((hy1 + hy2) / 2) + roi_top
                    )
                    ch = frame_h - crossbar_y

                    if ch <= 0:
                        continue

                    ratio = cw / ch
                    if not (1.3 <= ratio <= 5.5):
                        continue

                    match, conf = self._match_goal_size_full(
                        cw, ch, frame_w, frame_h,
                        player_height_cm
                    )

                    if match and conf > best_conf:
                        best_conf = conf
                        best = {
                            "detected":      True,
                            "bbox":          (lx, crossbar_y,
                                              rx, frame_h),
                            "post_left":     lx,
                            "post_right":    rx,
                            "crossbar_y":    crossbar_y,
                            "ground_y":      frame_h,
                            "confidence":    conf,
                            **match
                        }

        if best:
            best["zones"] = self._calculate_zones(best)
        return best or {"detected": False, "confidence": 0.0}

    # ─────────────────────────────────────────
    # SIZE MATCHING
    # ─────────────────────────────────────────

    def _match_goal_size_full(
        self,
        pixel_w:          int,
        pixel_h:          int,
        frame_w:          int,
        frame_h:          int,
        player_height_cm: float
    ) -> tuple[dict | None, float]:
        best_match = None
        best_conf  = 0.0

        for hf in [0.40, 0.50, 0.55, 0.60,
                   0.65, 0.70, 0.75, 0.80, 0.85]:
            px_per_m     = (frame_h * hf /
                            player_height_cm) * 100
            detected_w_m = pixel_w / px_per_m
            detected_h_m = pixel_h / px_per_m

            for name, dims in GOAL_SIZES.items():
                w_diff     = abs(detected_w_m - dims["width_m"])
                h_diff     = abs(detected_h_m - dims["height_m"])
                total_diff = w_diff + h_diff

                conf = max(0.0, 1.0 - (total_diff / 2.5))
                conf = round(min(conf, 0.95), 2)

                if conf > best_conf:
                    best_conf  = conf
                    best_match = {
                        "goal_type":     name,
                        "goal_width_m":  dims["width_m"],
                        "goal_height_m": dims["height_m"],
                        "detected_w_m":  round(detected_w_m, 2),
                        "detected_h_m":  round(detected_h_m, 2)
                    }

        if best_conf < 0.15:
            return None, 0.0

        return best_match, best_conf

    # ─────────────────────────────────────────
    # WIDTH GUESS
    # ─────────────────────────────────────────

    def _best_width_guess(
        self,
        goal_w_px:        int,
        frame_w:          int,
        frame_h:          int,
        player_height_cm: float
    ) -> dict:
        width_fraction = goal_w_px / frame_w

        if width_fraction > 0.70:
            name = "11-a-side standard (24x8ft)"
        elif width_fraction > 0.50:
            name = "11-a-side youth (21x7ft)"
        elif width_fraction > 0.35:
            name = "9-a-side (16x7ft)"
        elif width_fraction > 0.20:
            name = "7-a-side (12x6ft)"
        else:
            name = "5-a-side small (12x4ft)"

        dims = GOAL_SIZES[name]
        return {
            "goal_type":     name,
            "goal_width_m":  dims["width_m"],
            "goal_height_m": dims["height_m"]
        }

    # ─────────────────────────────────────────
    # ZONE COORDINATES — FULL NAMES
    # ─────────────────────────────────────────

    def _calculate_zones(self, goal: dict) -> dict:
        x1 = goal["post_left"]
        x2 = goal["post_right"]
        y1 = goal["crossbar_y"]
        y2 = goal["ground_y"]
        w  = x2 - x1
        h  = y2 - y1
        w3 = w / 3
        h3 = h / 3

        return {
            "Top Left":   (x1,            y1,
                           x1 + w3,       y1 + h3),
            "Top Centre": (x1 + w3,       y1,
                           x1 + 2 * w3,   y1 + h3),
            "Top Right":  (x1 + 2 * w3,   y1,
                           x2,            y1 + h3),
            "Mid Left":   (x1,            y1 + h3,
                           x1 + w3,       y1 + 2 * h3),
            "Mid Centre": (x1 + w3,       y1 + h3,
                           x1 + 2 * w3,   y1 + 2 * h3),
            "Mid Right":  (x1 + 2 * w3,   y1 + h3,
                           x2,            y1 + 2 * h3),
            "Bot Left":   (x1,            y1 + 2 * h3,
                           x1 + w3,       y2),
            "Bot Centre": (x1 + w3,       y1 + 2 * h3,
                           x1 + 2 * w3,   y2),
            "Bot Right":  (x1 + 2 * w3,   y1 + 2 * h3,
                           x2,            y2),
        }

    # ─────────────────────────────────────────
    # GOALKEEPER DETECTION
    # ─────────────────────────────────────────

    def detect_goalkeeper(
        self,
        frame:     np.ndarray,
        goal_bbox: tuple
    ) -> dict:
        """
        Detects goalkeeper by finding the person who is
        highest in frame and smallest — goalkeeper is
        always further from camera than the shooter in
        finishing drills filmed from behind.
        Does NOT rely on goal bbox accuracy.
        """
        h, w    = frame.shape[:2]
        results = self.model(frame, verbose=False)[0]

        candidates = []

        for box in results.boxes:
            if int(box.cls[0]) != PERSON_CLASS:
                continue

            conf = float(box.conf[0])
            if conf < 0.35:
                continue

            px1, py1, px2, py2 = [
                int(v) for v in box.xyxy[0].tolist()
            ]

            pcx      = (px1 + px2) // 2
            pcy      = (py1 + py2) // 2
            person_h = py2 - py1

            # Goalkeeper is in upper 70% of frame
            # Shooter is always lower (closer to camera)
            if pcy > h * 0.70:
                continue

            if person_h < 20:
                continue

            candidates.append({
                "bbox":   (px1, py1, px2, py2),
                "pcx":    pcx,
                "pcy":    pcy,
                "height": person_h,
                "conf":   conf
            })

        if not candidates:
            return {"present": False}

        # Goalkeeper is highest in frame (smallest pcy)
        candidates.sort(key=lambda c: c["pcy"])
        gk = candidates[0]

        print(f"Goalkeeper detected at "
              f"({gk['pcx']},{gk['pcy']}) "
              f"height={gk['height']}px "
              f"(conf {gk['conf']:.2f})")

        return {
            "present":    True,
            "center_x":   gk["pcx"],
            "center_y":   gk["pcy"],
            "bbox":       gk["bbox"],
            "confidence": round(gk["conf"], 2)
        }
