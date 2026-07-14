"""
视频下载服务 - FastAPI 主应用
高性能异步 API + JWT 鉴权 + 用户管理
"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# 确保能 import 项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import engine, Base, SessionLocal
from models.user import User, UserRole
from core.security import hash_password
from api.auth import router as auth_router
from api.tasks import router as task_router
from api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时执行: 建表 + 创建管理员"""
    Base.metadata.create_all(bind=engine)

    # 创建默认管理员
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@aibuddy.top",
                hashed_password=hash_password("admin123456"),
                role=UserRole.ADMIN,
                daily_quota=9999,
            )
            db.add(admin)
            db.commit()
            print("[启动] 已创建默认管理员: admin / admin123456")
    finally:
        db.close()

    print(f"[启动] {settings.APP_NAME} 运行中")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(auth_router)
app.include_router(task_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "version": "2.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        workers=int(os.getenv("WORKERS", "4")),
        log_level="info",
    )
