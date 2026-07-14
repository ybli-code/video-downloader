"""
任务 API: 提交下载 / 任务列表 / 任务详情 / 下载文件 / 去水印 / 删除
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from core.deps import get_current_user, check_quota, increment_quota, rate_limiter
from models.user import User, UserRole
from models.task import DownloadTask, TaskStatus, QuotaUsage
from services.downloader_service import downloader_service, detect_platform, SUPPORTED_PLATFORMS
from services.task_queue import get_cached_task
from services.oss_storage import oss_storage
from config import settings

router = APIRouter(prefix="/api", tags=["任务"])


# ── 请求模型 ──

class DownloadRequest(BaseModel):
    url: str


class WatermarkRequest(BaseModel):
    x: int
    y: int
    w: int
    h: int


# ── 端点 ──

@router.get("/platforms")
async def platforms():
    """获取支持的平台列表 (无需认证)"""
    return {"platforms": SUPPORTED_PLATFORMS}


@router.post("/detect")
async def detect(req: dict):
    """检测 URL 平台 (无需认证)"""
    url = req.get("url", "").strip()
    if not url:
        raise HTTPException(400, "请提供视频链接")
    platform = detect_platform(url)
    return {"url": url, "platform": platform, "supported": platform != "未知平台"}


@router.post("/download")
async def submit_download(
    req: DownloadRequest,
    user: User = Depends(rate_limiter),
    db: Session = Depends(get_db),
):
    """提交下载任务"""
    url = req.url.strip()
    if not url:
        raise HTTPException(400, "请提供视频链接")

    # 检查配额
    if not check_quota(db, user):
        raise HTTPException(429, "今日下载配额已用完，明天再试")

    task = downloader_service.submit_download(db, user, url)
    return {"success": True, "task": task.to_dict()}


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户任务列表"""
    query = db.query(DownloadTask).filter(DownloadTask.user_id == user.id)
    total = query.count()
    tasks = query.order_by(DownloadTask.created_at.desc()).offset((page - 1) * size).limit(size).all()

    # 合并 Redis 缓存的实时进度
    result = []
    for t in tasks:
        d = t.to_dict()
        cached = get_cached_task(t.task_id)
        if cached and t.status in ("pending", "analyzing", "downloading", "processing", "uploading"):
            d["progress"] = cached.get("progress", t.progress)
            d["speed"] = cached.get("speed", t.speed)
            d["eta"] = cached.get("eta", t.eta)
        result.append(d)

    return {"tasks": result, "total": total, "page": page, "size": size}


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取任务详情"""
    task = db.query(DownloadTask).filter(
        DownloadTask.task_id == task_id,
        DownloadTask.user_id == user.id,
    ).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    d = task.to_dict()
    # 合并 Redis 缓存
    cached = get_cached_task(task_id)
    if cached and task.status in ("pending", "analyzing", "downloading", "processing", "uploading"):
        d["progress"] = cached.get("progress", task.progress)
        d["speed"] = cached.get("speed", task.speed)
        d["eta"] = cached.get("eta", task.eta)
    return d


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除任务及文件"""
    task = db.query(DownloadTask).filter(
        DownloadTask.task_id == task_id,
        DownloadTask.user_id == user.id,
    ).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # 删除 OSS 文件
    if task.oss_key:
        oss_storage.delete_file(task.oss_key)

    db.delete(task)
    db.commit()
    return {"success": True}


@router.get("/download/{task_id}")
async def download_file(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取视频下载 URL"""
    task = db.query(DownloadTask).filter(
        DownloadTask.task_id == task_id,
        DownloadTask.user_id == user.id,
    ).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != "completed":
        raise HTTPException(400, "视频尚未下载完成")

    # 生成新的签名 URL
    url = oss_storage.generate_signed_url(task.oss_key) if task.oss_key else task.oss_url
    return {"url": url, "filename": f"{task.title or 'video'}.mp4", "size": task.file_size_str}


@router.post("/tasks/{task_id}/watermark")
async def remove_watermark(
    task_id: str,
    req: WatermarkRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """去除视频水印"""
    task = db.query(DownloadTask).filter(
        DownloadTask.task_id == task_id,
        DownloadTask.user_id == user.id,
    ).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != "completed":
        raise HTTPException(400, "视频尚未下载完成")

    if req.w <= 0 or req.h <= 0:
        raise HTTPException(400, "水印区域宽高必须大于 0")

    try:
        url = downloader_service.remove_watermark(db, task, req.x, req.y, req.w, req.h)
        return {"success": True, "task": task.to_dict()}
    except Exception as e:
        raise HTTPException(500, f"去水印失败: {str(e)}")


@router.get("/quota")
async def get_quota(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户配额使用情况"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = db.query(QuotaUsage).filter(
        QuotaUsage.user_id == user.id,
        QuotaUsage.date == today,
    ).first()

    used = usage.download_count if usage else 0
    limit = settings.PREMIUM_DAILY_LIMIT if user.role == UserRole.PREMIUM else user.daily_quota

    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "total_size_mb": round(usage.total_size_mb, 2) if usage else 0,
        "reset_at": (datetime.utcnow() + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat(),
    }
