import cv2
import sys
import numpy as np
sys.path.append(".")

from backend.cv_engine.pose_extractor import extract_landmarks_from_video
from backend.cv_engine.angle_calculator import (
    extract_shooting_angles,
    extract_ankle_angle,
    measure_follow_through,
    classify_shot_type,
    get_coords
)
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index,
    filter_foot_glued_optical_flow,
)

def overlay_ball_on_annotated(video_path, detections):
    """
    Second pass: draws the ball detection ring onto the
    already-skeleton-annotated video so body mechanics
    and ball tracking appear together.
    Yellow ring  = YOLO detection
    Orange ring  = optical flow detection
    """
    import cv2 as _cv2

    annotated_in = video_path.replace(".mp4", "_annotated.mp4")
    combined_out = video_path.replace(".mp4", "_annotated_full.mp4")

    cap = _cv2.VideoCapture(annotated_in)
    if not cap.isOpened():
        print(f"[overlay] Could not open {annotated_in}")
        return None

    fps_v = cap.get(_cv2.CAP_PROP_FPS)
    w     = int(cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
    h     = int(cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))

    out = _cv2.VideoWriter(
        combined_out,
        _cv2.VideoWriter_fourcc(*"mp4v"),
        fps_v, (w, h)
    )

    # Build a frame -> ball lookup
    ball_map = {
        d["frame"]: d["ball"]
        for d in detections
        if d.get("ball") is not None
    }

    fnum = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if fnum in ball_map:
            b      = ball_map[fnum]
            cx, cy = int(b["cx"]), int(b["cy"])
            method = b.get("method", "yolo")
            colour = (0, 255, 255) if method == "yolo" \
                     else (0, 165, 255)

            _cv2.circle(frame, (cx, cy), 14, colour, 3)
            _cv2.putText(frame, f"ball f{fnum}",
                         (cx + 16, cy),
                         _cv2.FONT_HERSHEY_SIMPLEX,
                         0.4, colour, 1)

        out.write(frame)
        fnum += 1

    cap.release()
    out.release()
    print(f"[overlay] Combined video saved: {combined_out}")
    return combined_out


from backend.cv_engine.technique_scorer import (
    score_technique,
    calculate_shooting_score
)
from backend.cv_engine.ai_feedback import generate_ai_feedback

import sys as _sys
VIDEO_PATH = _sys.argv[1] if len(_sys.argv) > 1 else "data/new_videos/f10s4.mp4"


# ─────────────────────────────────────────
# CONTACT FRAME DETECTOR
# ─────────────────────────────────────────





# ─────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────

print("=" * 55)
print("PROPATH FC — SHOOTING ANALYSIS")
print("=" * 55 + "\n")

# ── Step 1: Pose extraction ──────────────
print("Step 1: Extracting pose landmarks...")
frames = extract_landmarks_from_video(
    VIDEO_PATH, draw_skeleton=True
)

if not frames:
    print("No frames extracted — check video path")
    exit()

valid_frames = [
    f for f in frames if f["landmarks"] is not None
]
print(f"Pose detected in {len(valid_frames)} frames\n")

# ── Step 2: Ball detection ───────────────
print("Step 2: Detecting ball...")
detector        = BallDetector()
detections, fps = detector.track_shot_only(VIDEO_PATH)

# Remove phantom optical-flow balls glued to a foot (e.g.
# post-shot retrieval drift) before contact/power use them.
_cap_fg = cv2.VideoCapture(VIDEO_PATH)
_fw_fg  = int(_cap_fg.get(cv2.CAP_PROP_FRAME_WIDTH))
_fh_fg  = int(_cap_fg.get(cv2.CAP_PROP_FRAME_HEIGHT))
_cap_fg.release()
detections = filter_foot_glued_optical_flow(
    valid_frames, detections, _fw_fg, _fh_fg
)

# ── Step 2b: Contact frame (needed for power) ──
print("Locating contact frame...")
_contact_result = find_contact_frame_index(valid_frames, detections, VIDEO_PATH)

# Hard-stop if the camera angle is unreliable (kicking-foot
# methods disagree → e.g. right-foot shot filmed from the left)
if isinstance(_contact_result, dict) and _contact_result.get("rejected"):
    _foot = "right" if _contact_result["likely_kicking_is_right"] else "left"
    print("\n" + "=" * 55)
    print("ANALYSIS STOPPED — CAMERA ANGLE ISSUE")
    print("=" * 55)
    print(f"\nThis looks like a {_foot}-foot shot, but the camera")
    print("angle makes it unreliable to analyse.\n")
    print(f"For best results, film from your {_foot}-foot side")
    print("with the ball clearly visible throughout the shot.\n")
    exit()

if _contact_result is not None:
    _contact_idx, _ = _contact_result
    _contact_frame_no = valid_frames[_contact_idx]["frame"]
else:
    _contact_frame_no = None

# ── Step 2c: Power (anchored to contact) ──
print("Estimating power...")
power_result    = detector.estimate_power_score(
                    detections, fps, _contact_frame_no
                  )

if power_result["power_grade"] is not None:
    print(f"Power grade:  {power_result['power_grade']}/100 "
          f"({power_result['speed_kmh']} km/h)\n")
else:
    print("Power grade:  could not estimate — "
          "ball not tracked clearly enough\n")

# ── Overlay ball onto skeleton video ─────
overlay_ball_on_annotated(VIDEO_PATH, detections)

# ── Step 3: Contact frame detection ──────
print("Step 3: Using contact frame from Step 2b...")
result = _contact_result  # reuse Step 2b result (no re-detect)

if result is None:
    print("Could not isolate contact frame")
    exit()

contact_idx, kicking_is_right = result
kicking_foot = "right" if kicking_is_right else "left"

if contact_idx == 0 or contact_idx >= len(valid_frames) - 1:
    print("Contact frame too close to start or end of video")
    exit()

pre_contact  = valid_frames[contact_idx - 1]
contact      = valid_frames[contact_idx]
post_contact = valid_frames[contact_idx + 1]

print(f"Contact at frame {contact['frame']} | "
      f"Kicking foot: {kicking_foot}\n")

# ── Step 4: Extract measurements ─────────
print("Step 4: Extracting biomechanical measurements...")
contact_angles = extract_shooting_angles(contact["landmarks"])

ankle_ang = extract_ankle_angle(
    contact["landmarks"], kicking_foot
)

follow = measure_follow_through(
    pre_contact["landmarks"],
    post_contact["landmarks"],
    kicking_foot,
    all_frames  = valid_frames,
    contact_idx = contact_idx
) 

# ── Step 5: Classify shot type ───────────
print("Step 5: Classifying shot type...")
classification = classify_shot_type(
    contact_angles, ankle_ang, follow
)

# ── Step 6: Score technique ───────────────
print("Step 6: Scoring technique...\n")
technique_result = score_technique(
    shot_type      = classification["type"],
    contact_angles = contact_angles,
    ankle_angle    = ankle_ang,
    follow_through = follow,
    kicking_foot   = kicking_foot
)

shooting_result = calculate_shooting_score(
    technique_score = technique_result["technique_score"],
    power_grade     = power_result["power_grade"]
)

# ── Step 7: Generate AI feedback ─────────
print("Step 7: Generating AI coaching feedback...\n")
ai_feedback = generate_ai_feedback(
    shot_type      = classification["type"],
    contact_angles = contact_angles,
    ankle_angle    = ankle_ang,
    follow_through = follow,
    power_grade    = power_result["power_grade"]
)


# ─────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────

print("=" * 55)
print("RESULTS")
print("=" * 55)

# ── Raw measurements ──────────────────────
print("\n" + "─" * 55)
print("RAW MEASUREMENTS")
print("─" * 55)

key_frames = [
    ("Before contact", pre_contact),
    ("At contact",     contact),
    ("After contact",  post_contact)
]

for label, f in key_frames:
    angles = extract_shooting_angles(f["landmarks"])
    print(f"\n[{label}] — Frame {f['frame']}:")
    for name, value in angles.items():
        val_str = (
            f"{value}°" if value is not None
            else "not visible"
        )
        print(f"  {name.replace('_',' ').title():<28} {val_str}")

print(
    f"\n  {'Ankle angle at contact:':<28} "
    f"{ankle_ang}°" if ankle_ang is not None
    else f"\n  {'Ankle angle:':<28} not visible"
)
print(
    f"  {'Follow-through distance:':<28} {follow}"
    if follow is not None
    else f"  {'Follow-through:':<28} not visible"
)

# ── Shot classification ───────────────────
print("\n" + "─" * 55)
print("SHOT CLASSIFICATION")
print("─" * 55)
print(f"\n  Shot type:   {classification['type']}")
print(f"  Confidence:  {int(classification['confidence'] * 100)}%")
print(f"\n  Signals detected:")
for signal, reading in classification["signals"].items():
    print(f"    {signal.replace('_',' ').title():<28} {reading}")

# ── Technique breakdown ───────────────────
print("\n" + "─" * 55)
print("TECHNIQUE BREAKDOWN")
print("─" * 55)
print(f"\n  Technique score: "
      f"{technique_result['technique_score']}/100 — "
      f"{technique_result['grade_label']}")
print(f"\n  Deductions from 100:")

for attr, deduction in technique_result["deductions"].items():
    label = attr.replace("_", " ").title()
    if deduction > 0:
        print(f"    {label:<28} -{deduction} pts")
    else:
        print(f"    {label:<28} ✅ optimal")

if technique_result["missing"]:
    print(f"\n  Not measured: "
          f"{', '.join(technique_result['missing'])}")

# ── Overall shooting score ────────────────
print("\n" + "─" * 55)
print("SHOOTING SCORE")
print("─" * 55)

tech  = shooting_result["components"]["technique"]
power = shooting_result["components"]["power"]

print(f"\n  ⚽ Shooting score:  "
      f"{shooting_result['shooting_score']}/100 — "
      f"{shooting_result['grade_label']}")
print(f"\n  Technique:  {tech}/100")
print(
    f"  Power:      {power}/100"
    if power is not None
    else "  Power:      not measured"
)

# ── AI coaching feedback ──────────────────
print("\n" + "─" * 55)
print("AI COACH FEEDBACK")
print("─" * 55 + "\n")
#print(ai_feedback)

print("\n" + "=" * 55)
print("Analysis complete.")
print("=" * 55) 