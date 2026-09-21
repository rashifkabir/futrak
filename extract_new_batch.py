import cv2, os, glob

SOURCE_DIR   = "data/new_videos"
OUTPUT_DIR   = "data/new_frames"
MAX_PER_VIDEO = 14    # cap frames from each video
MIN_INTERVAL  = 5     # never sample closer than this

os.makedirs(SOURCE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

videos = (glob.glob(f"{SOURCE_DIR}/*.mp4") +
          glob.glob(f"{SOURCE_DIR}/*.MP4") +
          glob.glob(f"{SOURCE_DIR}/*.mov") +
          glob.glob(f"{SOURCE_DIR}/*.MOV"))

if not videos:
    print(f"No videos found in {SOURCE_DIR}")
    raise SystemExit

print(f"Found {len(videos)} videos\n")
print(f"Capping at {MAX_PER_VIDEO} frames per video\n")

total = 0
for vp in videos:
    name  = os.path.splitext(os.path.basename(vp))[0]
    cap   = cv2.VideoCapture(vp)
    if not cap.isOpened():
        print(f"  SKIP: {name}")
        continue

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Work out interval so we get ~MAX_PER_VIDEO frames
    # spread evenly across the whole clip
    interval = max(MIN_INTERVAL,
                   frame_count // MAX_PER_VIDEO)

    fnum, saved = 0, 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if fnum % interval == 0 and saved < MAX_PER_VIDEO:
            cv2.imwrite(
                f"{OUTPUT_DIR}/{name}_f{fnum:04d}.jpg", frame
            )
            saved += 1
        fnum += 1
    cap.release()
    print(f"  {name}: {saved} frames "
          f"(clip {frame_count}f, interval {interval})")
    total += saved

print(f"\nTotal frames: {total}")
print(f"Saved to: {OUTPUT_DIR}")
print("\nThen prune to ~250-300 best frames,")
print("favouring in-flight balls + fence hard negatives.")
