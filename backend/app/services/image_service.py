"""
图片服务：从 HTML 中提取 base64 data URI 图片，存到磁盘，替换为服务器 URL。
"""
import base64
import hashlib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_DATA_URI_RE = re.compile(
    r'(<img\b[^>]*\bsrc\s*=\s*")data:image/([^;]+);base64,([^"]+)(")',
    re.IGNORECASE,
)

MIME_TO_EXT = {
    "png": "png",
    "jpeg": "jpg",
    "jpg": "jpg",
    "gif": "gif",
    "webp": "webp",
    "svg+xml": "svg",
    "bmp": "bmp",
    "tiff": "tiff",
}


def _save_image(data_b64: str, mime_sub: str, doc_id: str) -> str:
    """将 base64 图片数据保存到磁盘，返回文件名。"""
    raw = base64.b64decode(data_b64)
    digest = hashlib.sha256(raw).hexdigest()[:16]
    ext = MIME_TO_EXT.get(mime_sub.lower(), "png")
    filename = f"{doc_id}_{digest}.{ext}"

    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        filepath.write_bytes(raw)
        logger.info("image.saved %s (%d bytes)", filename, len(raw))

    return filename


def extract_and_store_images(html: str, doc_id: str, base_url: str = "/api/images") -> str:
    """
    扫描 HTML 中所有 <img src="data:image/...;base64,..."> 标签，
    将图片数据存到磁盘，替换 src 为服务器 URL。
    """
    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        prefix = m.group(1)    # '<img ... src="'
        mime_sub = m.group(2)  # 'png' / 'jpeg' etc.
        b64data = m.group(3)   # base64 payload
        suffix = m.group(4)    # '"'
        try:
            filename = _save_image(b64data, mime_sub, doc_id)
            count += 1
            return f'{prefix}{base_url}/{filename}{suffix}'
        except Exception:
            logger.exception("image.save_failed doc_id=%s", doc_id)
            return m.group(0)

    result = _DATA_URI_RE.sub(_replace, html)
    if count:
        logger.info("image.extract doc_id=%s replaced=%d", doc_id, count)
    return result


def get_image_path(filename: str) -> Path | None:
    """返回磁盘上的图片路径，不存在返回 None。"""
    path = UPLOAD_DIR / filename
    if path.exists() and path.is_file():
        return path
    return None
