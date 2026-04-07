"""
路由：Images
GET /api/images/{filename} — 返回已存储的图片文件
"""
import mimetypes

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import AppError, ErrorCode
from app.services.image_service import get_image_path

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{filename}")
async def serve_image(filename: str):
    path = get_image_path(filename)
    if not path:
        raise AppError(ErrorCode.NOT_FOUND, "Image not found", 404)
    media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
