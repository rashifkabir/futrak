"""
A/B capture-framing validation harness.

Answers the one question that gates the whole "wide landscape, goal-in-frame"
capture redesign: does the WIDE framing (player near-side, netted goal at the
far end) produce body-mechanics outputs close enough to the current CLOSE-UP
framing that the fault-gates and kinetic-chain timing still agree -- while the
ball stays trackable all the way to the goal?

This is an AGREEMENT test, not a calibration test: it needs PAIRED clips of the
SAME shot filmed both ways, NOT coach bands. Fill CLIPS with those pairs (two
phones filming simultaneously is ideal; one phone back-to-back works but adds
shot-to-shot noise) and run:

    python diagnostics/diag_ab_validation.py

Maps to the validation-spec metrics:
  1 fault-gate agreement ....... chain_order_ok (+ lean veto) close vs wide
  2 kinetic-chain timing delta .. hip/knee/foot_peak_at + gaps, in frames & ms
  3 coordination values ......... technique score + breakdown deltas
  4 landmark noise floor ........ plant_foot / pelvis / trunk / head jitter ratio
  5 detection completeness ...... pose+ball frames (via the analysers' own run)
  7 ball trackability at goal ... detections AFTER contact (the flight to goal)

Metric 6 (goal/miss CALL accuracy) is intentionally NOT computed here -- the
stop-event goal/miss detector doesn't exist yet (that's what this test decides
whether to build). Record the KNOWN outcome per wide clip in CLIPS (`goal_truth`)
so it's ready to plug in once that detector exists; for now the harness just
echoes it alongside the ball-trackability proxy.

NOTE: this is an offline diagnostic, not latency-critical -- it re-runs ball
tracking once for the trackability proxy on top of each analyser's own internal
run, and each analyser re-loads the detector model. Slow but correct; fine for a
one-off validation pass over a handful of clips.
"""
import sys
import statistics
sys.path.append(".")

from backend.cv_engine.laces_technique import analyse_laces_technique
from backend.cv_engine.finesse_technique import analyse_finesse_technique
from backend.cv_engine.ball_detector import BallDetector

ANALYSERS = {
    "laces": analyse_laces_technique,
    "finesse": analyse_finesse_technique,
}

# (label, shot_type, close_up_clip, wide_clip, goal_truth)
#   close_up_clip -> current close side-on portrait (the mechanics REFERENCE)
#   wide_clip     -> new wide landscape, player near-side, netted goal far end
#   goal_truth    -> known outcome of the wide clip: "goal" | "miss" | "?"
#                    (you were there / can eyeball it -- ground truth for later)
# Ideal: 15-25 pairs spanning clean goals, wide misses, over-bar misses, and
# both good AND deliberately-faulty technique. Capture the wide clip at each
# res/fps combo the phone supports (e.g. suffix labels _1080p120 / _720p240 /
# _4k60) to find the sweet spot.
CLIPS: list[tuple[str, str, str, str, str]] = [
    # ("laces_good_01", "laces",
    #  "data/ab/laces_good_01_close.mp4",
    #  "data/ab/laces_good_01_wide_1080p120.mp4", "goal"),
]

# measured fields pulled for the comparison (defensive .get -- finesse's measure
# reuses the shared _kinetic_chain so the timing/gate fields are present, but not
# every jitter field is guaranteed across shot types).
FAULT_GATES = ["chain_order_ok"]              # bool gates compared for agreement
TIMING_FIELDS = ["hip_peak_at", "knee_peak_at", "foot_peak_at",
                 "hip_to_knee_gap", "knee_to_foot_gap"]   # frame offsets
JITTER_FIELDS = ["plant_foot_jit", "pelvis_jit", "trunk_sway",
                 "head_jit", "support_knee_jit"]          # noise-floor proxies


def analyse(shot_type, path):
    """Run the canonical measure+score for the shot type. Returns the analyser
    dict (score/measured/breakdown) or None if contact/pose couldn't be found."""
    fn = ANALYSERS.get(shot_type)
    if fn is None:
        print(f"  [skip] unknown shot_type '{shot_type}'")
        return None
    try:
        return fn(path)
    except Exception as e:  # a bad/misframed clip shouldn't kill the whole run
        print(f"  [error] {shot_type} analyse failed on {path}: {e}")
        return None


def ms_before(peak_at_frames, fps):
    """peak_at is frames-before-contact (negative). Convert to ms-before so the
    close/wide delta is comparable even if the two clips ran at different fps."""
    if peak_at_frames is None or fps in (None, 0):
        return None
    return peak_at_frames * 1000.0 / fps


def ball_trackability_after_contact(detector, path, contact_frame):
    """Metric 7 proxy: of the ball's flight AFTER contact (toward the goal),
    how many frames is it actually detected? This is the feasibility signal for
    the stop-event goal/miss call -- if the ball vanishes on the way to the
    goal, goal/miss isn't decidable from this framing/res/fps."""
    try:
        dets, _ = detector.track_shot_only(path)
    except Exception as e:
        print(f"  [error] ball tracking failed on {path}: {e}")
        return None, None
    after = [d for d in dets if d["frame"] > contact_frame]
    if not after:
        return 0, 0
    detected = sum(1 for d in after if d["ball"] is not None)
    return detected, len(after)


def fmt(v, nd=4):
    if v is None:
        return "None"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def compare_pair(label, shot_type, close_path, wide_path, goal_truth, detector):
    print(f"\n{'=' * 64}\n{label}   ({shot_type})\n{'=' * 64}")

    a_close = analyse(shot_type, close_path)
    a_wide = analyse(shot_type, wide_path)
    if a_close is None or a_wide is None:
        print("  one or both clips failed to analyse -- skipping this pair")
        return None

    mc, mw = a_close["measured"], a_wide["measured"]
    fps_close = detector.get_actual_fps(close_path)
    fps_wide = detector.get_actual_fps(wide_path)

    # --- metric 1: fault-gate agreement ---
    gate_agree = {}
    for g in FAULT_GATES:
        cv, wv = mc.get(g), mw.get(g)
        gate_agree[g] = (cv == wv)
    # lean veto is an implicit fault-gate (lean_impact < -16 -> veto in scorer)
    lean_close = (mc.get("lean_impact", 0) < -16)
    lean_wide = (mw.get("lean_impact", 0) < -16)
    gate_agree["lean_veto"] = (lean_close == lean_wide)

    print("  -- metric 1: fault-gate agreement --")
    for g in FAULT_GATES:
        print(f"  {g:<20} close={fmt(mc.get(g))}  wide={fmt(mw.get(g))}  "
              f"{'OK' if gate_agree[g] else 'MISMATCH'}")
    print(f"  {'lean_veto':<20} close={lean_close}  wide={lean_wide}  "
          f"{'OK' if gate_agree['lean_veto'] else 'MISMATCH'}")

    # --- metric 2: kinetic-chain timing delta (frames + ms) ---
    print("  -- metric 2: timing delta (wide - close) --")
    timing_ms_deltas = {}
    for t in TIMING_FIELDS:
        cvf, wvf = mc.get(t), mw.get(t)
        dframes = (wvf - cvf) if (cvf is not None and wvf is not None) else None
        cms, wms = ms_before(cvf, fps_close), ms_before(wvf, fps_wide)
        dms = (wms - cms) if (cms is not None and wms is not None) else None
        if dms is not None:
            timing_ms_deltas[t] = dms
        print(f"  {t:<20} close={fmt(cvf)}  wide={fmt(wvf)}  "
              f"dframes={fmt(dframes)}  dms={fmt(dms, 1)}")

    # --- metric 3: coordination / score delta ---
    dscore = a_wide["score"] - a_close["score"]
    print("  -- metric 3: technique score --")
    print(f"  {'score':<20} close={fmt(a_close['score'],1)}  "
          f"wide={fmt(a_wide['score'],1)}  dscore={fmt(dscore,1)}")

    # --- metric 4: landmark noise floor (wide/close jitter ratio) ---
    print("  -- metric 4: jitter ratio (wide / close; >1 = noisier wide) --")
    jitter_ratios = {}
    for j in JITTER_FIELDS:
        cv, wv = mc.get(j), mw.get(j)
        ratio = (wv / cv) if (cv not in (None, 0) and wv is not None) else None
        if ratio is not None:
            jitter_ratios[j] = ratio
        print(f"  {j:<20} close={fmt(cv)}  wide={fmt(wv)}  ratio={fmt(ratio,2)}")

    # --- metric 7: ball trackability after contact (wide clip) ---
    detected, total = ball_trackability_after_contact(
        detector, wide_path, mw.get("contact_frame"))
    track_frac = (detected / total) if total else None
    print("  -- metric 7: wide-clip ball trackability after contact --")
    print(f"  detected {fmt(detected)}/{fmt(total)} post-contact frames "
          f"(fraction {fmt(track_frac, 2)})")

    # --- metric 6 placeholder: goal/miss ground truth (no detector yet) ---
    print(f"  -- metric 6: goal/miss ground truth = '{goal_truth}' "
          f"(detector not built; recorded for later) --")

    return dict(
        label=label,
        gate_agree=gate_agree,
        timing_ms_deltas=timing_ms_deltas,
        dscore=dscore,
        jitter_ratios=jitter_ratios,
        track_frac=track_frac,
        goal_truth=goal_truth,
    )


def aggregate(results):
    results = [r for r in results if r is not None]
    if not results:
        return
    print(f"\n{'#' * 64}\nAGGREGATE over {len(results)} pair(s)\n{'#' * 64}")

    # fault-gate agreement rate (the GREEN/RED floor)
    all_gate_keys = FAULT_GATES + ["lean_veto"]
    for g in all_gate_keys:
        agrees = [r["gate_agree"].get(g) for r in results if g in r["gate_agree"]]
        if agrees:
            rate = 100.0 * sum(agrees) / len(agrees)
            print(f"  fault-gate agreement  {g:<16} {rate:5.1f}%  "
                  f"({sum(agrees)}/{len(agrees)})")

    # median |timing delta| in ms per field
    print("  median |timing delta| (ms):")
    for t in TIMING_FIELDS:
        vals = [abs(r["timing_ms_deltas"][t]) for r in results
                if t in r["timing_ms_deltas"]]
        if vals:
            print(f"    {t:<20} {statistics.median(vals):6.1f} ms")

    # score + jitter + trackability summaries
    dscores = [abs(r["dscore"]) for r in results if r["dscore"] is not None]
    if dscores:
        print(f"  median |score delta|      {statistics.median(dscores):.1f}")
    for j in JITTER_FIELDS:
        vals = [r["jitter_ratios"][j] for r in results if j in r["jitter_ratios"]]
        if vals:
            print(f"  median jitter ratio   {j:<16} {statistics.median(vals):.2f}x")
    tracks = [r["track_frac"] for r in results if r["track_frac"] is not None]
    if tracks:
        print(f"  median ball trackability  {statistics.median(tracks):.2f} "
              f"(fraction of post-contact frames)")

    print("\n  Decision guide:")
    print("   GREEN  fault-gates agree ~>=90%, timing deltas small/stable,")
    print("          ball trackability high        -> single wide clip viable")
    print("   AMBER  gates agree but coordination/jitter drift")
    print("          -> ship wide mode with coordination suppressed + flagged")
    print("   RED    fault-gates FLIP, or ball lost en route to goal")
    print("          -> two-clip (close mechanics + wide goal-cam) fallback")


def main():
    if not CLIPS:
        print(__doc__)
        print(">> CLIPS is empty. Add paired (close, wide) clips to CLIPS and "
              "re-run once you've captured the A/B set.")
        return
    detector = BallDetector()
    results = [compare_pair(*clip, detector) for clip in CLIPS]
    aggregate(results)


if __name__ == "__main__":
    main()
