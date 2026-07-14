"""
FastAPI 依赖注入: 鉴权 + 限流
"""
import redis
import json
from datetime import datetime
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from config import settings
from database import get_db
from core.security import decode_token
from models.user import User, UserRole
from models.task import QuotaUsage

security_scheme = HTTPBearer(auto_error=False)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT 获取当前用户"""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """要求管理员权限"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


async def rate_limiter(request: Request, user: User = Depends(get_current_user)):
    """Redis 滑动窗口限流"""
    key = f"rate:{user.id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 60)
    if count > settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")
    return user


def check_quota(db: Session, user: User) -> bool:
    """检查用户今日下载配额"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = db.query(QuotaUsage).filter(
        QuotaUsage.user_id == user.id,
        QuotaUsage.date == today,
    ).first()

    used = usage.download_count if usage else 0
    limit = user.daily_quota if user.role != UserRole.PREMIUM else settings.PREMIUM_DAILY_LIMIT
    return used < limit


def increment_quota(db: Session, user: User, file_size_mb: float = 0):
    """增加用户配额使用"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = db.query(QuotaUsage).filter(
        QuotaUsage.user_id == user.id,
        QuotaUsage.date == today,
    ).first()

    if not usage:
        usage = QuotaUsage(user_id=user.id, date=today, download_count=0, total_size_mb=0)
        db.add(usage)

    usage.download_count += 1
    usage.total_size_mb += file_size_mb
    db.commit()
