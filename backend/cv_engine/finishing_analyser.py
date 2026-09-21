"""
Finishing analysis for ProPath FC.

Determines the OUTCOME of a shot on goal (goal / woodwork /
save / miss), the ENTRY POINT on the goal face, and the net
ZONE + score, using the ball's trajectory relative to the
custom-model goal bbox.

Key design choices:
  - Outcome is judged by the ball's NET PROGRESS toward the
    goal (distance-to-goal over time), NOT instantaneous
    direction — so a curling/knuckling shot (wobbles but still
    progresses toward goal) is NOT mistaken for a woodwork
    reversal.
  - The ball disappearing into the net is an EXPECTED goal
    signature (handles far 11-a-side goals where the ball is
    lost on entry).
  - Placement = where the ball first BREAKS THE NET (forward
    progress into the goal stops), not the first mouth crossing
    (a rising shot crosses low then climbs to where it hits net).
  - Stray/teleport detections (incl. a background/second ball)
    are rejected.
  - Requires a STATIC camera; camera motion is detected and
    rejected.
"""
import cv2
import numpy as np
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.goal_detector import GoalDetector


def _reject_strays(detections):
    """Null out teleport detections (jump >> median motion)."""
    pts = [(i, d["frame"], d["ball"]["cx"], d["ball"]["cy"])
           for i, d in enumerate(detections) if d["ball"] is not None]
    if len(pts) < 4:
        return detections
    jumps = []
    for k in range(1, len(pts)):
        df = pts[k][1] - pts[k-1][1]
        if df <= 0:
            jumps.append(0)
            continue
        dx = pts[k][2] - pts[k-1][2]
        dy = pts[k][3] - pts[k-1][3]
        jumps.append((dx*dx + dy*dy) ** 0.5 / df)
    pos = [j for j in jumps if j > 0]
    med = np.median(pos) if pos else 0
    if med <= 0:
        return detections
    for k in range(1, len(pts)):
        jin = jumps[k-1]
        if jin > 4.0 * med and jin > 30:
            detections[pts[k][0]]["ball"] = None
    return detections


def _classify_zone(cx, cy, gx1, gy1, gx2, gy2, goal_type):
    """Map placement (cx,cy) to a named zone + score.
    Three difficulty tiers (bigger goal = corner harder = more):
      'large'  = 11-a-side (24x8ft):       9 zones, full points
      'medium' = 9-a-side (16x7ft) & 7-a-side (12x6ft): 9 zones,
                 reduced points
      'small'  = 5-a-side (12x4ft, short): 6 zones (no middle
                 row), lowest points
    Assumes correct-side filming (left/right flip added later)."""
    w = max(gx2 - gx1, 1)
    h = max(gy2 - gy1, 1)
    fx = (cx - gx1) / w
    col = "left" if fx < 1/3 else "centre" if fx < 2/3 else "right"
    fy = (cy - gy1) / h

    if goal_type in ("small", "five"):
        row = "top" if fy < 0.5 else "bottom"
        zone = f"{row}-{col}"
        score = {"top-left": 6, "top-right": 6, "top-centre": 4,
                 "bottom-left": 4, "bottom-right": 4,
                 "bottom-centre": 2}.get(zone, 2)
    elif goal_type in ("medium", "seven", "nine"):
        row = "top" if fy < 1/3 else "middle" if fy < 2/3 else "bottom"
        zone = f"{row}-{col}"
        score = {"top-left": 8, "top-right": 8, "bottom-left": 8,
                 "bottom-right": 8, "top-centre": 6, "bottom-centre": 6,
                 "middle-left": 4, "middle-right": 4,
                 "middle-centre": 2}.get(zone, 2)
    else:
        row = "top" if fy < 1/3 else "middle" if fy < 2/3 else "bottom"
        zone = f"{row}-{col}"
        score = {"top-left": 10, "top-right": 10, "bottom-left": 10,
                 "bottom-right": 10, "top-centre": 7, "bottom-centre": 7,
                 "middle-left": 5, "middle-right": 5,
                 "middle-centre": 3}.get(zone, 3)
    return zone, score


def analyse_finishing(video_path, player_height_cm=170.0,
                      goal_type="large", has_keeper=False):
    """
    Returns a dict with: outcome (goal/woodwork/save/miss/
    rejected/unclear), confidence, entry_point (net placement),
    zone, zone_score, goal_type, goal_bbox, and diagnostics.
    """
    # ── 1. Goal geometry + camera-motion check ──
    gd = GoalDetector()
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    sample_frames = [int(total * p) for p in (0.1, 0.25, 0.4, 0.55, 0.7)]
    samples = []
    for fn in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
        ret, fr = cap.read()
        if ret:
            g = gd.detect_goal_in_frame(fr)
            if (g["detected"] and g.get("method") == "custom_model"
                    and g.get("x2") is not None):
                samples.append(g)
    cap.release()

    if len(samples) < 2:
        return {"outcome": "unclear", "confidence": 0.0,
                "entry_point": None, "zone": None, "zone_score": 0,
                "goal_type": goal_type, "goal_bbox": None,
                "crossing_tracked": False,
                "reason": "goal not detected reliably"}

    widths = [s["x2"] - s["x1"] for s in samples]
    cxs = [(s["x1"] + s["x2"]) / 2 for s in samples]
    cys = [(s["y1"] + s["y2"]) / 2 for s in samples]

    w_med = np.median(widths)
    w_var = (max(widths) - min(widths)) / w_med if w_med > 0 else 1
    cx_var = (max(cxs) - min(cxs)) / W
    cy_var = (max(cys) - min(cys)) / H

    if w_var > 0.20 or cx_var > 0.18 or cy_var > 0.15:
        return {"outcome": "rejected", "confidence": 0.0,
                "entry_point": None, "zone": None, "zone_score": 0,
                "goal_type": goal_type, "goal_bbox": None,
                "crossing_tracked": False,
                "reason": (f"camera movement detected "
                           f"(goal size var {w_var*100:.0f}%, "
                           f"x-shift {cx_var*100:.0f}%, "
                           f"y-shift {cy_var*100:.0f}%) — "
                           f"film with a STATIC camera, goal in "
                           f"frame throughout")}

    gx1 = int(np.median([s["x1"] for s in samples]))
    gy1 = int(np.median([s["y1"] for s in samples]))
    gx2 = int(np.median([s["x2"] for s in samples]))
    gy2 = int(np.median([s["y2"] for s in samples]))
    print(f"[finishing] static goal confirmed: "
          f"({gx1},{gy1})-({gx2},{gy2})")

    # ── GOAL-FRAMING GATE ──
    # The camera must be positioned so the WHOLE goal is in frame
    # and big enough for reliable zone scoring + ball tracking.
    goal_w = gx2 - gx1
    goal_h = gy2 - gy1
    goal_w_frac = goal_w / W
    # 1) Goal too SMALL (camera too far) -> ball will be tiny and
    #    get lost, zones unreliable.
    if goal_w_frac < 0.20:
        return {"outcome": "rejected", "confidence": 0.0,
                "entry_point": None, "zone": None, "zone_score": 0,
                "goal_type": goal_type,
                "goal_bbox": (gx1, gy1, gx2, gy2),
                "crossing_tracked": False,
                "reason": (f"The goal is too small in frame "
                           f"({goal_w_frac*100:.0f}% of width) — "
                           f"you're too far away. Move closer (or "
                           f"zoom) so the goal fills more of the "
                           f"frame, while still keeping the WHOLE "
                           f"goal visible, then re-film.")}
    # 2) Goal CUT OFF at a frame edge (partial goal) -> zone
    #    scoring would be wrong. Allow a small margin (within ~1.5%
    #    of an edge counts as cut off).
    # Only flag as cut off if the goal bbox is essentially AT
    # the frame boundary (clipped), not merely near the edge.
    # A goal sitting near an edge but fully visible (e.g. fin10,
    # framed to one side as the ball comes in diagonally) is FINE.
    mx, my = int(W * 0.005), int(H * 0.005)   # ~a few px
    cut = []
    if gx1 <= mx:          cut.append("left post")
    if gx2 >= W - mx:      cut.append("right post")
    if gy1 <= my:          cut.append("crossbar/top")
    if gy2 >= H - my:      cut.append("bottom")
    if cut:
        return {"outcome": "rejected", "confidence": 0.0,
                "entry_point": None, "zone": None, "zone_score": 0,
                "goal_type": goal_type,
                "goal_bbox": (gx1, gy1, gx2, gy2),
                "crossing_tracked": False,
                "reason": (f"The goal is cut off at the frame edge "
                           f"({', '.join(cut)}) — fit the WHOLE goal "
                           f"in frame (reposition or step back) so "
                           f"all four sides are visible, then "
                           f"re-film.")}

    goal_cx = (gx1 + gx2) / 2
    goal_cy = (gy1 + gy2) / 2

    # ── 2. Ball trajectory + stray rejection ──
    bd = BallDetector()
    detections = bd.track_across_video(video_path, mode="finishing")
    detections = _reject_strays(detections)

    track = [(d["frame"], d["ball"]["cx"], d["ball"]["cy"],
              d["ball"].get("diameter", 0))
             for d in detections if d["ball"] is not None]
    if len(track) < 5:
        return {"outcome": "unclear", "confidence": 0.0,
                "entry_point": None, "zone": None, "zone_score": 0,
                "goal_type": goal_type,
                "goal_bbox": (gx1, gy1, gx2, gy2),
                "crossing_tracked": False,
                "reason": "ball not tracked enough"}

    # ── 3. Distance-to-goal over time (net progress) ──
    dist = [((bx - goal_cx)**2 + (by - goal_cy)**2) ** 0.5
            for (_, bx, by, _) in track]

    # ── 4. ENTRY = first STRICT mouth crossing. Ball must be in
    #    the goal FACE: x between posts, y within goal height
    #    (small UPWARD tolerance for ball radius, NO downward
    #    margin — below the goal line is not in the goal). ──
    y_up = (gy2 - gy1) * 0.08
    def in_mouth(bx, by):
        return (gx1 <= bx <= gx2 and (gy1 - y_up) <= by <= gy2)

    first_cross_i = None
    for i, (fn, bx, by, dia) in enumerate(track):
        if in_mouth(bx, by):
            first_cross_i = i
            break

    entered_mouth = first_cross_i is not None
    if entered_mouth:
        cross = track[first_cross_i]
        entry_i = first_cross_i
        entry_dist = dist[first_cross_i]

        # PLACEMENT = where the ball first BREAKS THE NET (forward
        # progress into the goal stops). Walk forward through
        # CONTINUOUS in-goal points, rejecting sudden jumps OUT
        # (a background/second ball).
        step_tol = (gx2 - gx1) * 0.5
        net_i = first_cross_i
        prev = track[first_cross_i]
        for j in range(first_cross_i + 1, len(track)):
            fn_j, bx_j, by_j, _ = track[j]
            if not in_mouth(bx_j, by_j):
                break
            step = ((bx_j - prev[1])**2 + (by_j - prev[2])**2) ** 0.5
            if step > step_tol:
                break
            net_i = j
            prev = track[j]

        nb = track[net_i]
        cx, cy = nb[1], nb[2]            # net-break / rest -> used for FATE
        placement_frame = nb[0]
        # PLACEMENT (zone) = where the ball FIRST crossed the goal
        # mouth, NOT where it rolled to rest. (cx,cy stays for fate.)
        px, py = cross[1], cross[2]
        placement_frame = cross[0]
    else:
        entry_i = int(np.argmin(dist))
        cross = track[entry_i]
        cx, cy = cross[1], cross[2]
        px, py = cx, cy                 # no clean crossing -> same point
        entry_dist = dist[entry_i]
        placement_frame = cross[0]

    # ── 5. DEPTH cue: did the ball SHRINK approaching the goal? ──
    approach = [d for (_, _, _, d) in track[max(0, entry_i-8):entry_i+1]
                if d and d > 0]
    shrank = False
    if len(approach) >= 4:
        hh = len(approach) // 2
        early_d = float(np.median(approach[:hh]))
        late_d = float(np.median(approach[hh:]))
        if early_d > 0 and late_d < early_d * 0.75:
            shrank = True

    # ── 6. DEFLECTION (save / woodwork): SHARP net-progress
    #    reversal AWAY from goal near the closest approach. ──
    deflected_away = False
    deflect_at_edge = False
    deflect_inside_mouth = False
    near_min_i = int(np.argmin(dist))
    if near_min_i + 2 < len(dist):
        post_min = dist[near_min_i+1:near_min_i+4]
        if post_min and (max(post_min) - dist[near_min_i]) > (gx2-gx1)*0.30:
            deflected_away = True
            dxb, dyb = track[near_min_i][1], track[near_min_i][2]
            edge_tol = (gx2 - gx1) * 0.15
            at_post = (abs(dxb-gx1) < edge_tol or abs(dxb-gx2) < edge_tol)
            at_bar = abs(dyb-gy1) < (gy2-gy1)*0.20
            deflect_at_edge = at_post or at_bar
            # WHERE did the reversal happen relative to the mouth?
            # inside the goal mouth, at an edge, or outside it.
            deflect_inside_mouth = (gx1 <= dxb <= gx2 and
                                    gy1 <= dyb <= gy2 and
                                    not deflect_at_edge)

    # ── 7. DISAPPEARANCE + BALL FATE + DEPTH signals ──
    last_tracked_frame = track[-1][0]
    last_pos = (track[-1][1], track[-1][2])
    disappeared = (total - last_tracked_frame) > 3

    def insideness(bx, by):
        if not (gx1 <= bx <= gx2 and gy1 <= by <= gy2):
            return 0.0
        ex = min(bx-gx1, gx2-bx) / max((gx2-gx1)/2, 1)
        ey = min(by-gy1, gy2-by) / max((gy2-gy1)/2, 1)
        return min(ex, ey)
    max_inside = max((insideness(bx, by) for (_, bx, by, _) in track),
                     default=0.0)

    # Judge the ball's FATE on the NET-BREAK placement (cx,cy),
    # which is the real ball's last CONTINUOUS in-goal position
    # (background-ball jumps already rejected). The raw last_pos
    # can be a background ball grabbed after a gap.
    # "ended_outside" = exited the SIDES (beyond a post) or OVER
    # the bar. Dropping DOWN within the posts = ball in the net
    # settling = NOT outside (still a goal).
    ended_outside = (cx < gx1 or cx > gx2
                     or cy < gy1 - (gy2-gy1)*0.10)

    extrap_out = None
    tail = track[-5:]
    if len(tail) >= 2:
        dfn = tail[-1][0] - tail[0][0]
        if dfn > 0:
            vx = (tail[-1][1] - tail[0][1]) / dfn
            vy = (tail[-1][2] - tail[0][2]) / dfn
            speed = (vx*vx + vy*vy) ** 0.5
            if speed > (gx2 - gx1) * 0.01:
                px = tail[-1][1] + vx * 15
                py = tail[-1][2] + vy * 15
                extrap_out = not (gx1 <= px <= gx2 and gy1 <= py <= gy2)

    # CONTINUOUS EXIT (save signal): after the ball was deepest
    # inside, did the REAL ball (continuous path, no big jumps)
    # travel to OUTSIDE the posts? On-target shot kept out = save.
    exited_continuous = False
    _deep_i, _deep_v = 0, -1
    for _i, (_, _bx, _by, _) in enumerate(track):
        _iv = insideness(_bx, _by)
        if _iv > _deep_v:
            _deep_v, _deep_i = _iv, _i
    if _deep_v > 0:
        _stol = (gx2 - gx1) * 0.5
        _prev = track[_deep_i]
        for _j in range(_deep_i + 1, len(track)):
            _fn, _bx, _by, _ = track[_j]
            if ((_bx - _prev[1])**2 + (_by - _prev[2])**2) ** 0.5 > _stol:
                break
            if _bx < gx1 or _bx > gx2:
                exited_continuous = True
                break
            _prev = track[_j]

    # ── 8. Classify outcome (layered: most-accurate first,
    #    fallback to "unclear" when data can't support a call) ──
    crossing_tracked = entered_mouth
    confidence = 0.5
    outcome = "unclear"
    DEEP = 0.30
    DEEP_CROSS = 0.3

    # last continuous in-goal position = the net-break placement
    # (cx,cy). Did the ball END genuinely INSIDE the goal there?
    ended_inside = (gx1 <= cx <= gx2 and gy1 <= cy <= gy2)
    end_inside_depth = insideness(cx, cy)   # how deep the END was

    cross_depth = insideness(px, py) 
    crossed_and_receded = (entered_mouth and cross_depth >= 0.12
                           and (shrank or disappeared or max_inside >= DEEP_CROSS)) 
     
    if deflected_away:
        # Tier 1: tracked SHARP reversal away from goal.
        if deflect_at_edge:
            # hit the post/bar -> woodwork (keeper-independent).
            outcome = "woodwork"; confidence = 0.55
        elif deflect_inside_mouth:
            # reversal happened INSIDE the goal mouth.
            if has_keeper:
                # a keeper could have clawed it out -> save.
                outcome = "save"; confidence = 0.55
            else:
                # no keeper: the only thing that sends a ball back
                # from INSIDE the net is the fence behind it ->
                # the ball went IN -> GOAL.
                outcome = "goal"; confidence = 0.6
        else:
            # reversal happened OUTSIDE the mouth (ball was wide/
            # short and hit something).
            if has_keeper:
                outcome = "save"; confidence = 0.6
            else:
                # no keeper -> hit the fence/ground wide -> MISS.
                outcome = "miss"; confidence = 0.6
    elif not entered_mouth:
        # Tier 2: never crossed the strict mouth -> miss.
        outcome = "miss"; confidence = 0.6
    elif crossed_and_receded:
        # Ball cleanly crossed the mouth at depth and receded into
        # the goal -> GOAL, regardless of later roll/exit.
        outcome = "goal"; confidence = 0.8 
    elif (ended_outside or exited_continuous) and not crossed_and_receded:
        # Tier 3: the ball EXITED the posts (placement outside, OR
        # the continuous path went inside->outside).
        if has_keeper:
            # on-target shot kept out by the keeper -> SAVE.
            outcome = "save"; confidence = 0.6
        else:
            # no keeper: an on-target shot that ends up outside the
            # posts went WIDE / was kept out by nothing -> MISS.
            outcome = "miss"; confidence = 0.6
    elif ended_inside and end_inside_depth >= DEEP and (shrank or disappeared):
        # Tier 4 (most confident GOAL): ball ENDED deep inside
        # AND showed depth-into-net (shrank / vanished deep).
        outcome = "goal"; confidence = 0.85
    elif ended_inside and end_inside_depth >= DEEP:
        # Tier 5: ended deep inside, tracked, no deflection/exit
        # -> goal, slightly lower confidence.
        outcome = "goal"; confidence = 0.72
    elif disappeared and extrap_out is True:
        # Tier 6: vanished, extrapolation shows heading OUT.
        outcome = "miss"; confidence = 0.5
    elif disappeared and extrap_out is False and end_inside_depth >= DEEP:
        # Tier 7: vanished heading IN and ended deep -> likely goal.
        outcome = "goal"; confidence = 0.6
    else:
        # Fallback: ball reached the mouth EDGE then vanished with
        # NO depth progression and NO reliable extrapolation
        # (e.g. f6s1miss: ended at the edge, curl-out not tracked).
        # Honestly UNCLEAR, not a false confident goal.
        outcome = "unclear"; confidence = 0.35

    entry_point = (int(px), int(py)) if entered_mouth else None

    # ── 9. Net-corner ZONE + score (goal only; uses net-break
    #    placement). Left/right NOT yet mirror-flipped for
    #    wrong-side clips (camera-side detection added later). ──
    if outcome == "goal" and entered_mouth:
        zone, zone_score = _classify_zone(px, py, gx1, gy1,
                                          gx2, gy2, goal_type)
    else:
        zone, zone_score = None, 0

    return {
        "outcome":          outcome,
        "confidence":       round(confidence, 2),
        "entry_point":      entry_point,
        "zone":             zone,
        "zone_score":       zone_score,
        "goal_type":        goal_type,
        "goal_bbox":        (gx1, gy1, gx2, gy2),
        "crossing_tracked": crossing_tracked,
        "entry_frame":      cross[0],
        "placement_frame":  placement_frame,
        "shrank":           shrank,
        "deflected_away":   deflected_away,
        "closest_dist_px":  round(float(dist[near_min_i]), 1),
    }


if __name__ == "__main__":
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else "data/new_videos/fin45.mp4"
    gtype = sys.argv[2] if len(sys.argv) > 2 else "standard"
    print(f"\nAnalysing finishing: {video} (goal_type={gtype})\n")
    result = analyse_finishing(video, goal_type=gtype)
    print("\n" + "="*50)
    print("FINISHING RESULT")
    print("="*50)
    for k, v in result.items():
        print(f"  {k}: {v}")
