import cv2
import numpy as np
import os
import subprocess
from dotenv import load_dotenv
from models.onnx_detector import get_local_model

load_dotenv(dotenv_path=".env")

# ── Custom model config (bump version for v5 later) ──
ROBOFLOW_MODEL_ID   = "propathfc-detection/4"
BALL_CONFIDENCE     = 0.35   # lower — catches near-goal balls
GOALPOST_CONFIDENCE = 0.50


class BallDetector:

    def __init__(self):
        print("Loading local ProPath model (ONNX, no credits)...")
        self.model = get_local_model()  # local ONNX, no credits
        print("Custom model ready")

    def get_actual_fps(self, video_path: str) -> float:
        """
        Detects real capture fps of iPhone slow-mo files.
        iPhone saves 240fps as 30fps playback — this
        extracts the real capture rate for accurate
        speed calculations.
        """
        result = subprocess.run([
            "ffprobe", "-v", "0",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "csv=p=0",
            video_path
        ], capture_output=True, text=True)

        if result.returncode == 0:
            try:
                num, den = result.stdout.strip().split("/")
                real_fps = float(num) / float(den)

                # TEMPORARY OVERRIDE for baked-in slow-mo testing
                # Android/iPhone slow-mo often saves as 30fps with
                # the slow motion rendered in, so ffprobe reads 30.
                # Force 240 so speed maths is correct for slow-mo.
                # TODO: replace with user-selected fps on upload
                SLOWMO_OVERRIDE = 240.0
                if real_fps < 60:
                    print(f"[DEBUG] File reports {real_fps}fps - "
                          f"overriding to {SLOWMO_OVERRIDE} "
                          f"(slow-mo test mode)")
                    return SLOWMO_OVERRIDE

                print(f"[DEBUG] Real capture fps: {real_fps}")
                return real_fps
            except Exception:
                pass

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        # TEMPORARY: slow-mo override on fallback path too
        if fps < 60:
            print(f"[DEBUG] Fallback {fps}fps - overriding to 240")
            fps = 240.0
        cap.release()
        print(f"[DEBUG] Fallback fps: {fps}")
        return fps

    def detect_in_frame(self, frame: np.ndarray) -> dict | None:
        """
        Detects the ball using the custom ProPath model.
        Returns the highest-confidence ball detection, or None.
        Uses BALL_CONFIDENCE threshold (lower, to catch
        small/near-goal balls).
        """
        results = self.model.infer(
            frame, confidence=BALL_CONFIDENCE
        )[0]

        best      = None
        best_conf = 0
        for p in results.predictions:
            if p.class_name != "ball":
                continue
            conf = float(p.confidence)
            if conf > best_conf:
                best_conf = conf
                cx = int(p.x)
                cy = int(p.y)
                w  = int(p.width)
                h  = int(p.height)
                best = {
                    "cx":         cx,
                    "cy":         cy,
                    "diameter":   w,
                    "confidence": round(conf, 3),
                    "bbox":       (cx - w // 2, cy - h // 2,
                                   cx + w // 2, cy + h // 2)
                }
        return best

    def detect_all_balls(self, frame: np.ndarray) -> list:
        """Return ALL ball detections (not just the best), each a
        dict like detect_in_frame's output. Used so the tracker
        can pick the ball on the SHOT trajectory rather than the
        highest-confidence ball (which may be a stationary
        background ball once the shot ball shrinks with distance)."""
        results = self.model.infer(frame, confidence=BALL_CONFIDENCE)[0]
        balls = []
        for p in results.predictions:
            if p.class_name != "ball":
                continue
            cx, cy = int(p.x), int(p.y)
            w, h = int(p.width), int(p.height)
            balls.append({
                "cx": cx, "cy": cy, "diameter": w,
                "confidence": round(float(p.confidence), 3),
                "bbox": (cx - w // 2, cy - h // 2,
                         cx + w // 2, cy + h // 2),
            })
        return balls

    def pick_trajectory_ball(self, frame, expected, max_dist):
        """Pick the ball detection closest to `expected` (x,y),
        within `max_dist`. Returns None if no ball is close enough
        (so a far-off stationary background ball is rejected).
        If expected is None, falls back to highest-confidence."""
        balls = self.detect_all_balls(frame)
        if not balls:
            return None
        if expected is None:
            # Initial pick (no trajectory yet): prefer the ball
            # that's both confident AND LARGE. A larger ball is
            # closer to the camera = the shooter's ball; a smaller
            # one is further away (e.g. a second ball downfield or
            # near a keeper). Weighting by diameter favors the
            # shooter's ball over a distant one, while confidence
            # still filters false detections.
            return max(balls, key=lambda b: b["confidence"]
                       * (b.get("diameter", 1) ** 0.5))
        ex, ey = expected
        best = None
        best_d = None
        for b in balls:
            d = ((b["cx"] - ex) ** 2 + (b["cy"] - ey) ** 2) ** 0.5
            if best_d is None or d < best_d:
                best_d = d
                best = b
        if best_d is not None and best_d <= max_dist:
            return best
        return None

    def track_across_video(self, video_path: str, mode: str = "shooting") -> list:
        cap          = cv2.VideoCapture(video_path)
        fps          = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        detections   = []
        frame_num    = 0
        prev_gray       = None
        optical_flow_pt = None
        last_yolo_frame = None
        shot_pos        = None      # persistent shot-ball pos
        shot_vel        = (0, 0)    # persistent shot-ball velocity
        shot_last_frame = None

        print(f"Tracking ball across {total_frames} frames "
              f"at {fps}fps...")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # FINISHING: pick the ball on the SHOT trajectory, not
            # the highest-confidence ball — once the shot ball
            # shrinks with distance, a stationary BACKGROUND ball
            # can win on confidence and steal the tracker. Predict
            # the shot ball's next position from recent detections
            # and pick the closest detection within a gate; reject
            # far-off balls (the background ball).
            if mode == "finishing":
                # Use a PERSISTENT last-known shot position +
                # velocity that survives tracking gaps. Looking
                # only at the last few frames fails after a gap
                # (all None) -> expected becomes None -> fallback
                # grabs the stationary background ball. Instead we
                # keep predicting from the last KNOWN shot ball.
                expected = None
                if shot_pos is not None:
                    expected = (shot_pos[0] + shot_vel[0],
                                shot_pos[1] + shot_vel[1])
                # gate widens slightly while the ball is lost (we
                # are less sure where it is), but never enough to
                # admit the far-off background ball.
                gaps = (frame_num - (shot_last_frame or frame_num))
                grow = 1.0 + min(gaps, 8) * 0.10   # up to +80%
                max_dist = frame.shape[1] * 0.22 * grow
                if expected is not None:
                    yolo_ball = self.pick_trajectory_ball(
                        frame, expected, max_dist)
                else:
                    # no shot history yet -> highest confidence
                    # (the shot ball starts big/close = top conf)
                    yolo_ball = self.detect_in_frame(frame)
                # update the persistent shot tracker on a hit
                if yolo_ball is not None:
                    if shot_pos is not None:
                        shot_vel = (yolo_ball["cx"] - shot_pos[0],
                                    yolo_ball["cy"] - shot_pos[1])
                        # clamp velocity to plausible (avoid a
                        # bad detection injecting a huge velocity)
                        vmax = frame.shape[1] * 0.15
                        shot_vel = (
                            max(-vmax, min(vmax, shot_vel[0])),
                            max(-vmax, min(vmax, shot_vel[1])),
                        )
                    shot_pos = (yolo_ball["cx"], yolo_ball["cy"])
                    shot_last_frame = frame_num
            else:
                yolo_ball = self.detect_in_frame(frame)

            if yolo_ball is not None:
                ball            = yolo_ball
                ball["method"]  = "yolo"
                optical_flow_pt = np.array(
                    [[float(yolo_ball["cx"]),
                      float(yolo_ball["cy"])]],
                    dtype=np.float32
                ).reshape(1, 1, 2)
                last_yolo_frame = frame_num

            elif optical_flow_pt is not None \
                    and prev_gray is not None:
                frames_since_yolo = (
                    frame_num - (last_yolo_frame or 0)
                )
                if frames_since_yolo <= 12:  # generous; foot-glue filter handles drift
                    new_pt, status, _ = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray,
                        optical_flow_pt, None,
                        winSize=(21, 21),
                        maxLevel=3,
                        criteria=(
                            cv2.TERM_CRITERIA_EPS |
                            cv2.TERM_CRITERIA_COUNT,
                            10, 0.03
                        )
                    )
                    if status is not None and status[0][0] == 1:
                        cx = int(new_pt[0][0][0])
                        cy = int(new_pt[0][0][1])

                        # These checks assume FINISHING geometry
                        # (ball travels UP toward the goal).
                        # In SHOOTING the ball stays low and can
                        # move any direction, so only apply them
                        # for finishing mode.
                        frame_h = gray.shape[0]
                        in_player_zone = False
                        reversed_dir   = False

                        if mode == "finishing":
                            in_player_zone = cy > frame_h * 0.50

                            if len(detections) >= 3:
                                recent = [
                                    d["ball"]["cy"]
                                    for d in detections[-3:]
                                    if d["ball"] is not None
                                ]
                                if (len(recent) >= 2 and
                                        min(recent) < cy - 20):
                                    reversed_dir = True

                        if in_player_zone or reversed_dir:
                            ball            = None
                            optical_flow_pt = None
                        else:
                            optical_flow_pt = new_pt
                            prev_diam = (
                                detections[-1]["ball"]["diameter"]
                                if detections and
                                detections[-1]["ball"]
                                else 20
                            )
                            ball = {
                                "cx":         cx,
                                "cy":         cy,
                                "diameter":   prev_diam,
                                "confidence": 0.4,
                                "method":     "optical_flow"
                            }
                    else:
                        ball            = None
                        optical_flow_pt = None
                else:
                    ball            = None
                    optical_flow_pt = None
            else:
                ball = None

            detections.append({
                "frame":     frame_num,
                "timestamp": round(frame_num / fps, 3),
                "ball":      ball
            })

            if frame_num % 30 == 0:
                if ball:
                    method = ball.get("method", "yolo")
                    status = (f"({ball['cx']},{ball['cy']}) "
                              f"[{method}]")
                else:
                    status = "not detected"
                print(f"  Frame {frame_num}/{total_frames}: "
                      f"{status}")

            prev_gray = gray
            frame_num += 1

        cap.release()

        yolo_count = sum(
            1 for d in detections
            if d["ball"] and d["ball"].get("method") == "yolo"
        )
        flow_count = sum(
            1 for d in detections
            if d["ball"]
            and d["ball"].get("method") == "optical_flow"
        )
        print(f"\nYOLO: {yolo_count} | "
              f"Optical flow: {flow_count} | "
              f"Total: {yolo_count + flow_count}/{total_frames}")

        return detections

    def get_first_trajectory_only(self,
                                  detections: list,
                                  fps: float) -> list:
        max_gap_frames   = int(fps * 1.0)
        first_trajectory = []
        last_detected    = None
        ball_seen_once   = False

        for d in detections:
            if d["ball"] is not None:
                if ball_seen_once and last_detected is not None:
                    gap = d["frame"] - last_detected
                    if gap > max_gap_frames:
                        print(f"Replay detected at frame "
                              f"{d['frame']} "
                              f"(gap {round(gap/fps,1)}s)"
                              f" — stopping")
                        break
                ball_seen_once = True
                last_detected  = d["frame"]
            first_trajectory.append(d)

        detected = sum(
            1 for d in first_trajectory
            if d["ball"] is not None
        )
        print(f"First trajectory: {len(first_trajectory)} "
              f"frames, ball visible in {detected}")
        return first_trajectory

    def estimate_power_score(self,
                             detections: list,
                             fps: float,
                             contact_frame: int = None) -> dict:
        """
        Estimates shot power using the STABLE POST-IMPACT
        VELOCITY PLATEAU.

        Anchored to the contact frame (when known) so it
        measures the actual launch, ignoring later events
        like the ball hitting the net.

        Physics of why early frames are skipped:
          contact+1 : ball deforming against foot (distorted)
          contact+2 : acceleration artifact / motion blur
          contact+3 onward : true free flight (measure here)

        Speed is found by LINE-FITTING ball position vs time
        across the stable plateau (tolerates missing frames,
        averages pixel noise). Lateral/vertical only for now;
        depth correction is a TODO (see note).
        """
        valid = [d for d in detections if d["ball"] is not None]
        if len(valid) < 4:
            print("[DEBUG] Not enough detections for power")
            return {"power_grade": None, "power_range": None, "angle_confidence": None, "speed_kmh": None}

        # Scale is calibrated LATER from the plateau frames
        # (the ball's size at the exact frames/distance where
        # speed is measured) — NOT a whole-video median, which
        # would mix close-ball and far-ball frames and distort
        # the scale.

        # ── Determine where measurement starts ──
        # If contact frame known: start at contact+3 (skip
        # deformation + acceleration). Else: fall back to the
        # global velocity spike (legacy behaviour).
        if contact_frame is not None:
            measure_start_frame = contact_frame + 3
            print(f"[DEBUG] Power anchored to contact "
                  f"{contact_frame}, measuring from frame "
                  f"{measure_start_frame}")
        else:
            # Legacy: find the velocity spike
            vels = []
            for i in range(1, len(valid)):
                fgap = valid[i]["frame"] - valid[i-1]["frame"]
                if fgap <= 0 or fgap > 4:
                    continue
                dx = valid[i]["ball"]["cx"] - valid[i-1]["ball"]["cx"]
                dy = valid[i]["ball"]["cy"] - valid[i-1]["ball"]["cy"]
                vels.append((i, (dx*dx + dy*dy) ** 0.5 / fgap))
            if not vels:
                return {"power_grade": None, "power_range": None, "angle_confidence": None, "speed_kmh": None}
            peak_i, _ = max(vels, key=lambda v: v[1])
            measure_start_frame = valid[peak_i]["frame"] + 3
            print(f"[DEBUG] No contact frame; spike-anchored "
                  f"measure from {measure_start_frame}")

        # ── Build the plateau window: measure_start_frame
        #    to +9 frames (early flight, before drag decay) ──
        PLATEAU_LEN = 9
        window = [
            d for d in valid
            if measure_start_frame <= d["frame"]
               <= measure_start_frame + PLATEAU_LEN
        ]
        if len(window) < 4:
            print(f"[DEBUG] Plateau too sparse "
                  f"({len(window)} frames) — power unavailable")
            return {"power_grade": None, "power_range": None, "angle_confidence": None, "speed_kmh": None}

        # ── Calibrate scale from PLATEAU frames only ──
        # The ball's diameter in these exact frames reflects
        # its real size at the measurement distance.
        plateau_diam = [
            d["ball"]["diameter"] for d in window
            if d["ball"]["diameter"] > 5
        ]
        if not plateau_diam:
            print("[DEBUG] No diameter in plateau — unavailable")
            return {"power_grade": None, "power_range": None, "angle_confidence": None, "speed_kmh": None}
        px_per_metre = np.median(plateau_diam) / 0.22
        print(f"[DEBUG] Scale (plateau): "
              f"{round(px_per_metre, 1)} px/m "
              f"(ball ~{int(np.median(plateau_diam))}px)")

        # ── Reject false-object outliers (teleport / net) ──
        # When the model briefly latches onto the goal net or
        # another object, the "ball" teleports and its diameter
        # collapses. These corrupt the line fit. We identify the
        # dominant smooth cluster (the real ball) and reject
        # points that don't belong to it.
        window = sorted(window, key=lambda d: d["frame"])
        if len(window) >= 4:
            median_diam = np.median([d["ball"]["diameter"]
                                     for d in window])

            # Diameter-collapse rejection: the net was diam 8 vs
            # real ball ~28. A point under half the median
            # diameter is a different object.
            kept = [d for d in window
                    if d["ball"]["diameter"] >= median_diam * 0.5]
            for d in window:
                if d["ball"]["diameter"] < median_diam * 0.5:
                    print(f"[DEBUG] Rejected frame {d['frame']} "
                          f"(diameter {d['ball']['diameter']} << "
                          f"median {median_diam:.0f} — false object)")
            window = kept

        if len(window) >= 4:
            # Teleport rejection: find median frame-to-frame jump
            # among remaining points; drop any single point that
            # sits far off the smooth trajectory (big jump in AND
            # out of it).
            jumps = [0.0]  # jumps[k] = motion from window[k-1] to k
            for k in range(1, len(window)):
                df = window[k]["frame"] - window[k-1]["frame"]
                dx = window[k]["ball"]["cx"] - window[k-1]["ball"]["cx"]
                dy = window[k]["ball"]["cy"] - window[k-1]["ball"]["cy"]
                jumps.append(((dx*dx + dy*dy) ** 0.5 / df)
                             if df > 0 else 0.0)
            pos_jumps = [j for j in jumps[1:] if j > 0]
            median_jump = np.median(pos_jumps) if pos_jumps else 0

            cleaned = []
            for k in range(len(window)):
                jin  = jumps[k] if k > 0 else 0
                jout = jumps[k+1] if k + 1 < len(window) else 0
                # A point is a teleport outlier if the jump TO it
                # is huge (it appeared from nowhere). Keep the
                # first point always.
                is_outlier = (median_jump > 0 and
                              jin > 3.0 * median_jump and
                              jin > 15)
                if is_outlier:
                    print(f"[DEBUG] Rejected frame "
                          f"{window[k]['frame']} "
                          f"(jump {jin:.0f}px/f vs median "
                          f"{median_jump:.0f} — teleport)")
                    continue
                cleaned.append(window[k])
            window = cleaned

        if len(window) < 4:
            print(f"[DEBUG] Too few clean frames after outlier "
                  f"rejection ({len(window)}) — power unavailable")
            return {"power_grade": None, "power_range": None, "angle_confidence": None, "speed_kmh": None}

        # ── Line-fit position vs time across the plateau ──
        # frame numbers as x, cx and cy as y; slope = px/frame
        frames = np.array([d["frame"] for d in window], dtype=float)
        cxs    = np.array([d["ball"]["cx"] for d in window], dtype=float)
        cys    = np.array([d["ball"]["cy"] for d in window], dtype=float)

        # slope via least squares
        vx_px_per_frame = np.polyfit(frames, cxs, 1)[0]
        vy_px_per_frame = np.polyfit(frames, cys, 1)[0]

        speed_px_per_frame = (vx_px_per_frame**2 +
                              vy_px_per_frame**2) ** 0.5

        # ── DEPTH correction (toward/away from camera) ──
        # Lateral pixel speed misses motion ALONG the camera axis
        # (a shot toward goal/camera barely moves in pixels). The
        # ball SHRINKS as it recedes, so the rate of change of its
        # diameter across the plateau gives the depth speed in the
        # same normalized units. We add it in quadrature to recover
        # the true 3D launch speed.
        diam_fit = np.polyfit(
            frames,
            [d["ball"]["diameter"] for d in window], 1)
        diam0 = float(np.median([d["ball"]["diameter"] for d in window]))
        ddiam_per_frame = diam_fit[0]
        v_depth_px_per_frame = (abs(ddiam_per_frame) / max(diam0, 1)
                                * px_per_metre * 0.22)

        speed_lat_px_f   = speed_px_per_frame
        speed_total_px_f = (speed_lat_px_f**2 +
                            v_depth_px_per_frame**2) ** 0.5

        # ── ANGLE confidence: TWO independent depth signals. ──
        # (1) ON-SCREEN trajectory (PRIMARY): how much the ball
        #     moves ACROSS the frame (|vx|) vs UP/down it (|vy|).
        #     A side-on shot crosses the frame (high across_ratio);
        #     a shot heading toward goal/horizon moves up-the-frame
        #     with little across. Works from the first frames and
        #     does NOT need the ball to shrink — catches SLOW
        #     into-screen shots the diameter signal misses.
        # (2) DIAMETER shrink (SECONDARY/fallback): catches FAST
        #     into-screen shots where the ball recedes quickly
        #     enough to shrink measurably (depth_fraction), even
        #     if the on-screen angle looks moderate.
        # We take the MORE CAUTIOUS of the two: if EITHER says the
        # shot is depth-dominant, confidence drops. This is honest
        # — each signal covers the other's blind spot.
        across_ratio = (abs(vx_px_per_frame) /
                        max(abs(vx_px_per_frame) +
                            abs(vy_px_per_frame), 1e-6))
        depth_fraction = (v_depth_px_per_frame /
                          max(speed_total_px_f, 1e-6))
        # on-screen confidence
        # Calibrated to real clips: shots naturally rise as they
        # travel, so even a good side-on shot has notable vertical
        # motion (fin14shot2 side-on = 0.63; sh6laces diagonal =
        # 0.59). across_ratio can't finely separate those, so we
        # only flag the CLEARLY into-screen case (mostly up-frame,
        # little across). The filming manual handles the rest.
        if across_ratio > 0.55:
            conf_angle = "high"      # decent across motion = OK
        elif across_ratio > 0.38:
            conf_angle = "medium"    # noticeably diagonal
        else:
            conf_angle = "low"       # mostly into-screen — flag
        # diameter-shrink confidence (fast receding ball)
        if depth_fraction < 0.30:
            conf_diam = "high"
        elif depth_fraction < 0.60:
            conf_diam = "medium"
        else:
            conf_diam = "low"        # shrinking fast = receding fast
        # combine: most cautious wins
        _rank = {"high": 2, "medium": 1, "low": 0}
        angle_confidence = min([conf_angle, conf_diam],
                               key=lambda x: _rank[x])
        print(f"[DEBUG] across_ratio {across_ratio:.2f} ({conf_angle}) "
              f"| depth_frac {depth_fraction:.2f} ({conf_diam}) "
              f"-> {angle_confidence}")

        speed_px_per_sec = speed_total_px_f * fps
        speed_m_per_sec  = speed_px_per_sec / px_per_metre
        speed_kmh        = speed_m_per_sec * 3.6
        if speed_kmh > 140:
            print(f"[DEBUG] Raw {round(speed_kmh,1)} km/h "
                  f"exceeds realistic range — flagging, cap 140")
            speed_kmh = 140.0

        print(f"[DEBUG] Plateau frames "
              f"{int(frames[0])}-{int(frames[-1])} "
              f"({len(window)} pts)")
        power_grade = speed_to_grade(speed_kmh)

        # ── Honest presentation (MVP) ──
        # Depth-normalized power SCORE /100 is the headline.
        # km/h is kept but APPROXIMATE (diameter scale is noisy;
        # true km/h is a post-MVP upgrade). Report a RANGE, WIDER
        # when angle confidence is low (depth-dominant shots are
        # less certain because depth is inferred from noisy
        # diameter shrink).
        spread = {"high": 4, "medium": 7, "low": 12}[angle_confidence]
        grade_low  = max(1,   power_grade - spread)
        grade_high = min(100, power_grade + spread)
        print(f"[DEBUG] Plateau frames "
              f"{int(frames[0])}-{int(frames[-1])} ({len(window)} pts)")
        print(f"[DEBUG] lateral {speed_lat_px_f:.1f} + depth "
              f"{v_depth_px_per_frame:.1f} px/f | angle conf "
              f"{angle_confidence} (depth {depth_fraction:.2f})")
        print(f"[DEBUG] Power grade {power_grade}/100 "
              f"(range {grade_low}-{grade_high}); "
              f"~{round(speed_kmh,1)} km/h approx")
        return {
            "power_grade":      power_grade,
            "power_range":      (grade_low, grade_high),
            "angle_confidence": angle_confidence,
            "speed_kmh":        round(speed_kmh, 1),
            "speed_kmh_note":   "approximate — depth-normalized, "
                                "true km/h is a post-MVP upgrade",
            "power_note": {
                "high":   "Good side-on angle — power reading is reliable.",
                "medium": "Shot was slightly diagonal — power may read a "
                          "little low. Film side-on (ball crossing the "
                          "frame) for best accuracy.",
                "low":    "Shot travelled toward the goal/camera — power "
                          "likely under-reads. Film from the side so the "
                          "ball crosses the frame left-to-right.",
            }[angle_confidence],
        }

    def track_shot_only(self,
                        video_path: str,
                        mode: str = "shooting") -> tuple[list, float]:
        fps             = self.get_actual_fps(video_path)
        all_detections  = self.track_across_video(video_path, mode=mode)
        shot_detections = self.get_first_trajectory_only(
                            all_detections, fps
                          )
        return shot_detections, fps


def speed_to_grade(speed_kmh: float) -> int:
    if speed_kmh < 10:
        return max(1, int(speed_kmh * 2))
    elif speed_kmh < 30:
        return int(10 + (speed_kmh - 10) * 0.75)
    elif speed_kmh < 50:
        return int(25 + (speed_kmh - 30) * 1.0)
    elif speed_kmh < 70:
        return int(45 + (speed_kmh - 50) * 1.0)
    elif speed_kmh < 90:
        return int(65 + (speed_kmh - 70) * 0.75)
    elif speed_kmh < 110:
        return int(80 + (speed_kmh - 90) * 0.6)
    else:
        return min(100, int(92 + (speed_kmh - 110) * 0.4))


def estimate_shot_speed(detections: list,
                        fps: float,
                        mode: str = "standard",
                        angle_degrees: float = 0.0
                        ) -> float | None:
    LOW_CUT  = 20.0 if mode == "power" else 15.0
    HIGH_CUT = 160.0 if mode == "power" else 100.0

    ball_frames = [
        d for d in detections if d["ball"] is not None
    ]
    if len(ball_frames) < 4:
        return None

    diameters = [
        d["ball"]["diameter"]
        for d in ball_frames[:5]
        if d["ball"]["diameter"] > 5
    ]
    if not diameters:
        return None

    px_per_metre = np.median(diameters) / 0.22
    best_jump      = 0
    kick_frame_idx = None

    for i in range(1, len(ball_frames)):
        prev = ball_frames[i - 1]
        curr = ball_frames[i]
        if curr["frame"] - prev["frame"] > 4:
            continue
        dx           = (curr["ball"]["cx"]
                        - prev["ball"]["cx"])
        dy           = (curr["ball"]["cy"]
                        - prev["ball"]["cy"])
        displacement = np.sqrt(dx**2 + dy**2)
        if displacement > best_jump:
            best_jump      = displacement
            kick_frame_idx = i - 1

    if kick_frame_idx is None:
        return None

    kick_frame = ball_frames[kick_frame_idx]
    start_cx   = kick_frame["ball"]["cx"]
    start_cy   = kick_frame["ball"]["cy"]
    look_ahead = kick_frame["frame"] + 30
    flight     = [
        f for f in ball_frames
        if kick_frame["frame"] < f["frame"] <= look_ahead
    ]
    if not flight:
        return None

    best_frame = max(
        flight,
        key=lambda f: np.sqrt(
            (f["ball"]["cx"] - start_cx)**2 +
            (f["ball"]["cy"] - start_cy)**2
        )
    )

    frame_span = best_frame["frame"] - kick_frame["frame"]
    time_secs  = frame_span / fps
    if time_secs == 0:
        return None

    displacement_px = np.sqrt(
        (best_frame["ball"]["cx"] - start_cx)**2 +
        (best_frame["ball"]["cy"] - start_cy)**2
    )
    displacement_m = displacement_px / px_per_metre
    speed_kmh      = (displacement_m / time_secs) * 3.6

    if angle_degrees != 0:
        speed_kmh = speed_kmh / np.cos(
            np.radians(angle_degrees)
        )

    return round(speed_kmh, 1)
