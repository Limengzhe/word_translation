"""
数据库会话工厂（SQLModel + SQLite）。
"""
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

engine = create_engine(settings.database_url, echo=False)


def create_db_and_tables() -> None:
    """在应用启动时创建所有表（开发用；生产建议 Alembic）。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 依赖注入：提供数据库会话。"""
    with Session(engine) as session:
        yield session
