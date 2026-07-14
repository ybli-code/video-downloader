"""
下载任务模型 + 配额使用记录
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    UPLOADING = "uploading"    # 上传到OSS
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"        # 文件已过期清理


class DownloadTask(Base):
    __tablename__ = "download_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(32), unique=True, index=True, nullable=False)

    # 用户
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # 视频信息
    url = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False)
    title = Column(String(500), default="")
    author = Column(String(200), default="")
    duration = Column(String(20), default="")
    thumbnail = Column(Text, default="")

    # 状态
    status = Column(String(20), default=TaskStatus.PENDING.value, nullable=False, index=True)
    progress = Column(Float, default=0.0)
    speed = Column(String(30), default="")
    eta = Column(String(20), default="")
    error = Column(Text, default="")

    # 文件信息
    file_size = Column(Integer, default=0)
    file_size_str = Column(String(30), default="")
    oss_key = Column(String(500), default="")        # OSS存储路径
    oss_url = Column(Text, default="")                # OSS访问URL
    watermark_free = Column(Boolean, default=True)

    # 水印处理
    watermark_processed = Column(Boolean, default=False)
    watermark_x = Column(Integer, default=0)
    watermark_y = Column(Integer, default=0)
    watermark_w = Column(Integer, default=0)
    watermark_h = Column(Integer, default=0)

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # 文件过期时间

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "url": self.url,
            "platform": self.platform,
            "title": self.title,
            "author": self.author,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "status": self.status,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "error": self.error,
            "file_size": self.file_size,
            "file_size_str": self.file_size_str,
            "oss_url": self.oss_url,
            "watermark_free": self.watermark_free,
            "watermark_processed": self.watermark_processed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class QuotaUsage(Base):
    """用户每日配额使用记录"""
    __tablename__ = "quota_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    download_count = Column(Integer, default=0)
    total_size_mb = Column(Float, default=0.0)

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "date": self.date,
            "download_count": self.download_count,
            "total_size_mb": round(self.total_size_mb, 2),
        }
