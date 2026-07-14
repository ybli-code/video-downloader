"""
阿里云 OSS 对象存储服务
视频文件上传到 OSS，不占服务器磁盘
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import oss2

from config import settings


class OSSStorage:
    """阿里云 OSS 封装"""

    def __init__(self):
        self.bucket = None
        self._init_oss()

    def _init_oss(self):
        if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_BUCKET_NAME:
            print("[OSS] 未配置 OSS 凭证，视频将存储在本地")
            return

        auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
        self.bucket = oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)

        # 验证连接
        try:
            self.bucket.get_bucket_info()
            print(f"[OSS] 连接成功: {settings.OSS_BUCKET_NAME}")
        except Exception as e:
            print(f"[OSS] 连接失败: {e}")
            self.bucket = None

    @property
    def available(self) -> bool:
        return self.bucket is not None

    def upload_file(self, local_path: str, user_id: str, platform: str) -> tuple[str, str]:
        """
        上传文件到 OSS
        返回: (oss_key, oss_url)
        """
        ext = os.path.splitext(local_path)[1] or ".mp4"
        date_str = datetime.utcnow().strftime("%Y%m%d")
        oss_key = f"videos/{date_str}/{user_id}/{uuid.uuid4().hex[:12]}_{platform}{ext}"

        if not self.available:
            # OSS 不可用时，文件保留在本地
            return local_path, f"local://{local_path}"

        self.bucket.put_object_from_file(oss_key, local_path)

        # 生成签名 URL (有效期 24 小时)
        url = self.bucket.sign_url(
            "GET", oss_key, 24 * 3600,
            slash_safe=True,
            params={"response-content-disposition": f"attachment; filename=video{ext}"}
        )

        # 如果有 CDN 域名，替换 URL
        if settings.OSS_CDN_DOMAIN:
            url = f"https://{settings.OSS_CDN_DOMAIN}/{oss_key}"

        return oss_key, url

    def delete_file(self, oss_key: str):
        """从 OSS 删除文件"""
        if not self.available or oss_key.startswith("local://"):
            local_path = oss_key.replace("local://", "")
            if os.path.exists(local_path):
                os.remove(local_path)
            return

        try:
            self.bucket.delete_object(oss_key)
        except Exception as e:
            print(f"[OSS] 删除失败: {e}")

    def generate_signed_url(self, oss_key: str, expires_hours: int = 24) -> str:
        """生成临时签名下载 URL"""
        if not self.available or oss_key.startswith("local://"):
            return oss_key.replace("local://", "")

        if settings.OSS_CDN_DOMAIN:
            return f"https://{settings.OSS_CDN_DOMAIN}/{oss_key}"

        return self.bucket.sign_url("GET", oss_key, expires_hours * 3600, slash_safe=True)


oss_storage = OSSStorage()
