import os
import uuid
import aiofiles
from fastapi          import APIRouter, UploadFile, File, Form, HTTPException
from backend.models.schemas          import ShootingAnalysisResponse
from backend.services.shooting_service import run_shooting_analysis
from backend.shot_types              import ALL_SHOT_TYPES
# Finishing is WIP and deferred per v1 scope (see project design notes) — route disabled
# below until backend.cv_engine.finishing_analyser.FinishingAnalyser exists.
# from backend.services.finishing_service import run_finishing_analysis

router = APIRouter()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
MAX_FILE_SIZE_MB   = 100
# Deliberately ALL registered shot types, not just ranked ones — this raw
# scoring endpoint is shared infrastructure for both the main ranked flow
# and the side-competition path, so it stays permissive. See
# backend/shot_types.py for where ranked-flow eligibility is actually gated.
SHOT_TYPES         = ALL_SHOT_TYPES
CONDITIONS         = {"static", "runup"}


@router.post(
    "/analyse/shooting",
    response_model = ShootingAnalysisResponse,
    summary        = "Analyse a shooting technique video",
    description    = "Upload a video of a football shot. "
                     "Returns technique grade, power grade, "
                     "shot type classification, and AI coaching feedback."
)
async def analyse_shooting(
    file: UploadFile = File(
        ...,
        description="Video file of the shot (MP4, MOV, AVI)"
    ),
    shot_type: str = Form(
        ...,
        description="Declared shot type: laces, finesse, or trivela"
    ),
    condition: str = Form(
        "static",
        description="static or runup"
    )
):
    # ── Validate file extension ──────────────────
    filename  = file.filename or "upload.mp4"
    ext       = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code = 400,
            detail      = f"File type {ext} not supported. "
                          f"Please upload MP4, MOV, or AVI."
        )

    if shot_type not in SHOT_TYPES:
        raise HTTPException(
            status_code = 400,
            detail      = f"shot_type must be one of {sorted(SHOT_TYPES)}"
        )

    if condition not in CONDITIONS:
        raise HTTPException(
            status_code = 400,
            detail      = f"condition must be one of {sorted(CONDITIONS)}"
        )

    # ── Save uploaded file temporarily ──────────
    unique_name = f"{uuid.uuid4()}{ext}"
    save_path   = os.path.join(UPLOAD_DIR, unique_name)

    try:
        async with aiofiles.open(save_path, "wb") as f:
            content = await file.read()

            # Check file size
            size_mb = len(content) / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                raise HTTPException(
                    status_code = 413,
                    detail      = f"File too large ({size_mb:.1f}MB). "
                                  f"Maximum size is {MAX_FILE_SIZE_MB}MB."
                )

            await f.write(content)

        # ── Run full analysis pipeline ───────────
        result = run_shooting_analysis(save_path, shot_type, condition)

        return ShootingAnalysisResponse(**result)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Analysis failed: {str(e)}"
        )

    finally:
        # Always clean up temp file
        if os.path.exists(save_path):
            os.remove(save_path)


@router.get(
    "/health",
    summary = "Health check"
)
async def health_check():
    return {
        "status":  "running",
        "service": "ProPath FC API"
    } 
    
# /analyse/finishing route disabled — see import note above.
