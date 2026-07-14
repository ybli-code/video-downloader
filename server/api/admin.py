"""
管理员 API: 用户管理 / 统计 / 系统状态
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from database import get_db
from core.deps import get_admin_user
from models.user import User, UserRole
from models.task import DownloadTask, QuotaUsage
from services.task_queue import get_queue_size, redis_client

router = APIRouter(prefix="/api/admin", tags=["管理"])


@router.get("/stats")
async def stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """系统统计"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    premium_users = db.query(User).filter(User.role == UserRole.PREMIUM).count()

    total_tasks = db.query(DownloadTask).count()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_tasks = db.query(DownloadTask).filter(
        DownloadTask.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    completed_tasks = db.query(DownloadTask).filter(DownloadTask.status == "completed").count()
    failed_tasks = db.query(DownloadTask).filter(DownloadTask.status == "failed").count()

    today_downloads = db.query(QuotaUsage).filter(QuotaUsage.date == today).all()
    today_count = sum(u.download_count for u in today_downloads)
    today_size = sum(u.total_size_mb for u in today_downloads)

    return {
        "users": {"total": total_users, "active": active_users, "premium": premium_users},
        "tasks": {
            "total": total_tasks, "today": today_tasks,
            "completed": completed_tasks, "failed": failed_tasks,
        },
        "today": {"downloads": today_count, "total_size_mb": round(today_size, 2)},
        "queue_size": get_queue_size(),
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """用户列表"""
    query = db.query(User)
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"users": [u.to_dict() for u in users], "total": total, "page": page, "size": size}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """修改用户角色"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if role not in ("free", "premium", "admin"):
        raise HTTPException(400, "无效角色")
    user.role = UserRole(role)
    db.commit()
    return {"success": True, "user": user.to_dict()}


@router.put("/users/{user_id}/quota")
async def update_user_quota(
    user_id: str,
    quota: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """修改用户配额"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.daily_quota = quota
    db.commit()
    return {"success": True, "user": user.to_dict()}


@router.delete("/users/{user_id}")
async def disable_user(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """禁用用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.is_active = not user.is_active
    db.commit()
    return {"success": True, "is_active": user.is_active}
