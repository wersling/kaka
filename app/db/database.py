"""
Database Connection and Session Management
数据库连接和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path
from typing import Generator
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 数据库目录
DB_DIR = Path("data")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "tasks.db"

# 创建数据库引擎
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # SQLite 需要
    echo=False,  # 生产环境设为 False
)

# 创建 Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    from app.db.models import Base
    logger.info(f"初始化数据库: {DB_PATH}")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ 数据库表创建完成")


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）

    用法:
        @app.get("/tasks")
        def get_tasks(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    获取数据库会话（手动管理）

    用法:
        db = get_db_session()
        try:
            # 数据库操作
            db.commit()
        finally:
            db.close()
    """
    return SessionLocal()
