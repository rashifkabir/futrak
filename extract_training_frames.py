import cv2
import os
import glob

SOURCE_DIR = "data/training_source"
OUTPUT_DIR = "data/training_frames"
FRAME_INTERVAL = 3  # extract every 3rd frame

os.makedirs(OUTPUT_DIR, exist_ok=True)

videos = glob.glob(f"{SOURCE_DIR}/*.mp4") + \
         glob.glob(f"{SOURCE_DIR}/*.mov")

print(f"Found {len(videos)} source videos")

total_extracted = 0

for video_path in videos:
    video_name = os.path.splitext(
        os.path.basename(video_path)
    )[0]

    cap         = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)

    print(f"\n{video_name}:")
    print(f"  {total_frames} frames at {fps:.0f}fps")

    extracted = 0
    frame_num = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num % FRAME_INTERVAL == 0:
            output_path = (
                f"{OUTPUT_DIR}/{video_name}_"
                f"frame_{frame_num:04d}.jpg"
            )
            cv2.imwrite(output_path, frame)
            extracted += 1

        frame_num += 1

    cap.release()
    print(f"  Extracted {extracted} frames")
    total_extracted += extracted

print(f"\nTotal extracted: {total_extracted} frames")
print(f"Saved to: {OUTPUT_DIR}")
