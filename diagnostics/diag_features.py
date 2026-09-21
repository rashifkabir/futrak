"""
Shot-type feature diagnostic — STABLE 2D-vector feature set
(corrected spec). No 3D biomechanics; only image-plane motion
vectors + temporal relationships. Auto-detects contact.

HEADLINE feature: FOOT-vs-BALL DEVIATION — does the ball leave
ALONG the foot's motion line (laces/toe = push-through) or OFF
it (inside-curl/trivela = wrapped/sliced)? Plus supporting
stable vector/timing features.

All clips MUST be the same camera side relative to the kicking
foot (so signed angles are comparable).
"""
import cv2, sys, math
sys.path.append(".")
from backend.cv_engine.pose_extractor import extract_landmarks_from_video
from backend.cv_engine.angle_calculator import get_coords
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index, filter_foot_glued_optical_flow,
)

CLIPS = [
    ("sh6laces        [LACES]",   "data/new_videos/sh6laces.mp4",        True),
    ("sh2instep_laces [LACES]",   "data/new_videos/sh2instep_laces.mp4", True),
    ("fin14shot2      [LACES]",   "data/test_videos/fin14shot2.mp4",     True),
    ("sh1finesse      [FINESSE]", "data/new_videos/sh1finesse.mp4",      True),
    ("sh7finesse      [FINESSE]", "data/new_videos/sh7finesse.mp4",      True),
    ("fin51shot10     [FINESSE]", "data/new_videos/fin51shot10.mp4",     True),
    ("s1              [FINESSE-bad]", "data/new_videos/s1.mp4",          True),
    ("sh2toepoke      [TOEPOKE]", "data/new_videos/sh2toepoke.mp4",      True),
    ("sh5trivela      [TRIVELA]", "data/new_videos/sh5trivela.mp4",      True),
    ("sh8trivela      [TRIVELA]", "data/new_videos/sh8trivela.mp4",      True),
    ("s6              [TRIVELA]", "data/new_videos/s6.mp4",              True),
]
ROWS = []

def ang(dx, dy):
    return math.degrees(math.atan2(dy, dx))

def signed_diff(a, b):
    d = a - b
    while d > 180: d -= 360
    while d < -180: d += 360
    return d

def vec_from(pts):
    """Net direction + magnitude of a list of (x,y) points."""
    if len(pts) < 2: return None, 0.0
    dx, dy = pts[-1][0]-pts[0][0], pts[-1][1]-pts[0][1]
    return ang(dx, dy), (dx*dx+dy*dy)**0.5

def analyse(label, video, kicking_right):
    cap = cv2.VideoCapture(video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    frames = extract_landmarks_from_video(video, draw_skeleton=False)
    valid = [f for f in frames if f["landmarks"] is not None]
    if len(valid) < 5:
        print(f"\n{label}: too little pose data\n"); return
    lm_by = {f["frame"]: f["landmarks"] for f in valid}
    det = BallDetector()
    detections, fps = det.track_shot_only(video)
    detections = filter_foot_glued_optical_flow(valid, detections, W, H)
    ball_by = {d["frame"]: d["ball"] for d in detections if d.get("ball")}

    result = find_contact_frame_index(valid, detections, video)
    if result is None or isinstance(result, dict):
        reason = "rejected (camera angle)" if isinstance(result, dict) else "none"
        print(f"\n{label}: contact detection {reason} — skipping\n"); return
    contact_idx, kr_det = result
    contact = valid[contact_idx]["frame"]
    ankle_idx = 28 if kicking_right else 27
    def ankle(fn):
        lm = lm_by.get(fn)
        if not lm: return None
        a = get_coords(lm, ankle_idx)
        return (a[0]*W, a[1]*H) if a else None
    def ball(fn):
        b = ball_by.get(fn)
        return (b["cx"], b["cy"]) if b else None

    print(f"\n{'='*64}\n{label}  | contact {contact} | foot {'R' if kr_det else 'L'}")
    print('='*64)

    # ── FOOT MOTION VECTOR at contact (avg over the frames just
    #    BEFORE contact — the swing direction into the ball) ──
    pre = [ankle(fn) for fn in range(contact-4, contact+1)]
    pre = [p for p in pre if p]
    foot_dir, foot_mag = vec_from(pre)

    # ── BALL INITIAL DIRECTION (first 3-6 frames after contact,
    #    while the ball is freshly struck — robust to later
    #    dropout) ──
    post = [ball(fn) for fn in range(contact, contact+7)]
    post = [p for p in post if p]
    ball_dir, ball_mag = vec_from(post)

    # ── HEADLINE: FOOT-vs-BALL DEVIATION ──
    # signed angle between ball launch direction and foot swing
    # direction. ~0 = ball goes ALONG the foot push (laces/toe);
    # large |dev| = ball leaves OFF the foot line (curl/trivela).
    # SIGN: + vs - separates inside-curl from trivela (opposite).
    if foot_dir is not None and ball_dir is not None and foot_mag > 3 and ball_mag > 3:
        deviation = signed_diff(ball_dir, foot_dir)
        print(f"DEVIATION (ball vs foot): {deviation:+6.0f}deg   "
              f"[foot {foot_dir:+.0f}/{foot_mag:.0f}px, ball {ball_dir:+.0f}/{ball_mag:.0f}px]")
    else:
        deviation = None
        print(f"DEVIATION: n/a (foot_mag {foot_mag:.0f}, ball_mag {ball_mag:.0f})")

    # ── SWING-PATH CURVATURE (foot trajectory bend, contact±6) ──
    arc = [ankle(fn) for fn in range(contact-6, contact+7)]
    arc = [p for p in arc if p]
    bend = None
    if len(arc) >= 6:
        m = len(arc)//2
        d1 = ang(arc[m][0]-arc[0][0], arc[m][1]-arc[0][1])
        d2 = ang(arc[-1][0]-arc[m][0], arc[-1][1]-arc[m][1])
        bend = signed_diff(d2, d1)
        print(f"SWING CURVATURE:          {bend:+6.0f}deg")

    # ── LATERAL FOLLOW-THROUGH RATIO (cross-body vs straight) ──
    # ratio of lateral (x) to total follow-through travel.
    # curl/trivela wrap across body -> high lateral ratio.
    ft = [ankle(fn) for fn in range(contact, contact+18)]
    ft = [p for p in ft if p]
    ft_len = sum(((ft[i][0]-ft[i-1][0])**2+(ft[i][1]-ft[i-1][1])**2)**0.5
                 for i in range(1,len(ft))) if len(ft)>=2 else 0
    lat_ratio = None
    if len(ft) >= 2 and ft_len > 1:
        lat = abs(ft[-1][0]-ft[0][0])
        lat_ratio = lat / ft_len
        print(f"FOLLOW-THROUGH:           {ft_len:.0f}px  lateral_ratio {lat_ratio:.2f}")

    # ── BACKSWING vs FOLLOW-THROUGH RATIO (toe-poke = tiny both;
    #    full strikes = long follow) ──
    bs = [ankle(fn) for fn in range(contact-10, contact)]
    bs = [p for p in bs if p]
    bs_len = sum(((bs[i][0]-bs[i-1][0])**2+(bs[i][1]-bs[i-1][1])**2)**0.5
                 for i in range(1,len(bs))) if len(bs)>=2 else 0
    fb_ratio = (ft_len/bs_len) if bs_len > 1 else None
    print(f"BACKSWING:                {bs_len:.0f}px  follow/back ratio "
          f"{fb_ratio:.2f}" if fb_ratio else f"BACKSWING: {bs_len:.0f}px")

    # ── FOOT SPEED (peak ankle speed near contact) ──
    sp = []
    for fn in range(contact-5, contact+5):
        a,b = ankle(fn), ankle(fn+1)
        if a and b: sp.append(((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5)
    peak = max(sp) if sp else 0
    print(f"FOOT SPEED:               peak {peak:.0f}px/f")

    ROWS.append({"label":label, "deviation":deviation, "bend":bend,
                 "lat_ratio":lat_ratio, "follow":ft_len, "fb_ratio":fb_ratio,
                 "footspeed":peak})

if __name__ == "__main__":
    for label, video, kr in CLIPS:
        try: analyse(label, video, kr)
        except Exception as e: print(f"\n{label}: ERROR — {e}\n")

    print("\n\n" + "="*104)
    print("STABLE 2D-VECTOR FEATURE TABLE")
    print("="*104)
    print(f"{'clip':<26}{'DEVIATN':>9}{'bend':>8}{'lat_rat':>9}"
          f"{'follow':>8}{'fb_rat':>8}{'footsp':>8}")
    print("-"*104)
    def f(v,w,d=0):
        return f"{v:>{w}.{d}f}" if isinstance(v,(int,float)) else f"{'n/a':>{w}}"
    for r in ROWS:
        print(f"{r['label']:<26}{f(r['deviation'],9)}{f(r['bend'],8)}"
              f"{f(r['lat_ratio'],9,2)}{f(r['follow'],8)}"
              f"{f(r['fb_ratio'],8,2)}{f(r['footspeed'],8)}")
    print("="*104)
    print("HEADLINE = DEVIATN (ball-vs-foot). Hypothesis: laces/toe")
    print("near 0 (push-through); finesse/trivela large |dev| (off")
    print("the foot line), opposite SIGNS for inside-curl vs trivela.")
