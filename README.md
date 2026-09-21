# Futrak

Scores football shooting technique from a phone video.

You film a shot side-on, pick the shot type, and the app returns a technique score,
a power estimate and a per-feature breakdown. Technique and power are kept as
separate numbers rather than combined into one.

Built with AI coding assistance. Work in progress.

## How it works

1. **Capture** — Expo app records at 240fps (120fps fallback). Android needed a small
   custom Camera2 module, since the usual React Native camera libraries are built on
   CameraX, which doesn't support high-speed capture.
2. **Pose** — MediaPipe Pose Landmarker gives 33 body landmarks per frame.
3. **Ball** — a YOLOv8n model trained on this project's frames, exported to ONNX and
   run locally with `onnxruntime`. Tracking links detections frame to frame.
4. **Contact frame** — found as the last time the foot meets the ball before it flies
   away, so earlier dribble touches aren't mistaken for the shot.
5. **Power** — the ball's known diameter (0.22m) converts pixels to metres, and its
   movement per frame plus the video's real frame rate gives speed. Frame rate is read
   with `ffprobe`, because phones save 240fps slow-mo as a 30fps file.
6. **Technique** — joint angles, balance and the timing of peak hip, knee and ankle
   speed around contact, scored against per-shot-type thresholds.

Scoring only penalises clear faults rather than measuring distance from one "ideal"
technique, since good players strike the ball in visibly different ways.

## Stack

Python (FastAPI, MediaPipe, OpenCV, onnxruntime) · React + TypeScript + Vite ·
Expo / React Native with a Kotlin native module · Postgres (Supabase) schema for the
pitch-leaderboard side of the app.

## Running it

Needs Python 3.10, Node 18+ and `ffmpeg` on your PATH.

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload     # API docs at http://localhost:8000/docs

# Web
cd frontend && npm install && npm run dev

# Mobile
cd mobile && npm install && npx expo start
```

For testing on a real phone, put your computer's LAN address in `mobile/.env`:

```
EXPO_PUBLIC_API_BASE_URL=http://<your-lan-ip>:8000
```

Copy `.env.example` to `.env` if you want the optional LLM feedback or the Supabase
scripts. The CV pipeline itself runs without any keys.

### Model weights

Not in the repo. The pose model downloads from Google:

```bash
curl -o models/pose_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
```

The ball detector (`models/weights/propathfc_v4.onnx`) was trained on footage of real
people, so it isn't published here. Any two-class (`ball`, `goalpost`) YOLOv8 ONNX
export at 640×640 works in its place.

### Test footage

No video or images are committed. All the clips and training frames are of real,
identifiable players, so `data/` and the training set stay out of the repo. The
scripts in `diagnostics/` expect your own side-on clips in `data/new_videos/`.

## Status

Working: capture, pose and ball tracking, contact detection, power estimation, and
technique scoring for laces and finesse shots. Trivela is built too, on a separate
path.

Next up: moving inference onto the phone, tuning the score thresholds against
coach-rated clips, automatic goal/miss detection, and deploying the Supabase backend.

Some things a single side-on camera can't see — ball spin, exact contact surface,
left-right placement — are left out of the score on purpose rather than guessed at.
