from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router

app = FastAPI(
    title       = "ProPath FC API",
    description = "AI-powered football development analysis",
    version     = "0.1.0"
)

# CORS — allows frontend and mobile app to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],  # restrict in production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"]
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "ProPath FC API is running",
        "docs":    "/docs"
    }