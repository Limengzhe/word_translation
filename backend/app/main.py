"""
FastAPI 应用入口。
"""
from contextlib import asynccontextmanager
import logging
import logging.handlers

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.documents import router as doc_router
from app.api.images import router as img_router
from app.core.config import settings
from app.api.revisions import router as rev_router
from app.api.segments import router as seg_router
from app.api.skills import router as skill_router
from app.core.errors import AppError
from app.db.session import create_db_and_tables

from pathlib import Path as _Path

_LOG_DIR = _Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            _LOG_DIR / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),
    ],
)

_llm_logger = logging.getLogger("llm_requests")
_llm_handler = logging.handlers.RotatingFileHandler(
    _LOG_DIR / "llm_requests.log",
    maxBytes=20 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_llm_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
_llm_logger.addHandler(_llm_handler)
_llm_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    key_suffix = settings.openai_api_key[-6:] if settings.openai_api_key else "<empty>"
    logger.info(
        "app.startup base_url=%s model=%s api_key_suffix=%s",
        settings.openai_base_url,
        settings.default_model,
        key_suffix,
    )
    yield


app = FastAPI(
    title="AI 翻译智能体",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(doc_router)
app.include_router(img_router)
app.include_router(seg_router)
app.include_router(rev_router)
app.include_router(skill_router)


@app.exception_handler(AppError)
async def app_error_handler(_req: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.get("/health")
def health():
    return {"status": "ok"}
