import subprocess

from app.api.routes.advisor import router as advisor_router
from fastapi import FastAPI

from app.api.routes.booking import router as booking_router
from app.api.routes.plan import router as plan_router
from app.core.config import get_settings
from app.utils.logger import configure_logging

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def install_playwright() -> None:
    try:
        subprocess.run(["playwright", "install", "--with-deps", "chromium"], check=True)
        print("Playwright Chromium installed")
    except Exception as exc:
        print(f"Playwright install failed: {exc}")

app.include_router(plan_router, prefix="/api/v1", tags=["planner"])
app.include_router(booking_router, prefix="/api/v1", tags=["booking"])
app.include_router(booking_router, prefix="/api", tags=["booking"])
app.include_router(advisor_router, prefix="/api/v1", tags=["advisor"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
