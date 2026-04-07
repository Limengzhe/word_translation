"""
应用配置：从环境变量读取，不硬编码 API Key。
自动在当前目录及上级目录寻找 .env 文件。
"""
from pathlib import Path
from pydantic_settings import BaseSettings


def _find_env_file() -> Path:
    """从 config.py 所在目录向上逐级查找 .env，最多查 5 层。"""
    cur = Path(__file__).resolve().parent   # 从目录开始，不是文件
    for _ in range(5):
        candidate = cur / ".env"
        if candidate.exists():
            return candidate
        cur = cur.parent
    return Path(".env")  # fallback


_ENV_FILE = _find_env_file()


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    default_model: str = "qwen-plus"
    default_temperature: float = 0.2
    stream_concurrency: int = 1
    max_segment_chars: int = 1000
    database_url: str = "sqlite:///./translate.db"

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

