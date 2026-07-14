"""
高性能视频下载服务 - 全局配置
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 服务 ──
    APP_NAME: str = "视频下载服务"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "vd-secret-key-change-in-production-2024")

    # ── 数据库 ──
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://vd:vd123@localhost:5432/videodownloader")

    # ── Redis ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── JWT ──
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── 阿里云 OSS ──
    OSS_ACCESS_KEY_ID: str = os.getenv("OSS_ACCESS_KEY_ID", "")
    OSS_ACCESS_KEY_SECRET: str = os.getenv("OSS_ACCESS_KEY_SECRET", "")
    OSS_ENDPOINT: str = os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
    OSS_BUCKET_NAME: str = os.getenv("OSS_BUCKET_NAME", "")
    OSS_CDN_DOMAIN: str = os.getenv("OSS_CDN_DOMAIN", "")  # 如果配了CDN，填CDN域名

    # ── 用户配额 ──
    DAILY_DOWNLOAD_LIMIT: int = 10       # 免费用户每日下载次数
    PREMIUM_DAILY_LIMIT: int = 100       # 付费用户每日下载次数
    MAX_FILE_SIZE_MB: int = 500          # 单个视频最大大小
    TASK_EXPIRE_HOURS: int = 24          # 任务/文件保留时间

    # ── 限流 ──
    RATE_LIMIT_PER_MINUTE: int = 20      # 每分钟API请求限制
    RATE_LIMIT_DOWNLOAD_PER_MINUTE: int = 5  # 每分钟下载请求限制

    # ── 下载 ──
    DOWNLOAD_DIR: str = "/tmp/vd-downloads"  # 临时下载目录(上传OSS后删除)
    MAX_CONCURRENT_DOWNLOADS: int = 5        # 最大并发下载数

    class Config:
        env_file = ".env"


settings = Settings()
