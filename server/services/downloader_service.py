"""
视频下载服务
封装核心下载逻辑，适配新架构 (DB + OSS + Redis)
复用已有的平台解析器 (抖音/B站/小红书/yt-dlp)
"""
import os
import re
import sys
import time
import uuid
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import yt_dlp
import httpx
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.user import User
from models.task import DownloadTask, TaskStatus
from services.oss_storage import oss_storage
from services.task_queue import update_task_progress, acquire_download_slot, release_download_slot


# ────────────────── 平台检测 ──────────────────

class Platform:
    YOUTUBE = "YouTube"
    TIKTOK = "TikTok"
    DOUYIN = "抖音"
    BILIBILI = "B站"
    TWITTER = "Twitter/X"
    INSTAGRAM = "Instagram"
    FACEBOOK = "Facebook"
    REDDIT = "Reddit"
    VIMEO = "Vimeo"
    DAILYMOTION = "Dailymotion"
    IXIGUA = "西瓜视频"
    WEIBO = "微博"
    XIAOHONGSHU = "小红书"
    UNKNOWN = "未知平台"


PLATFORM_PATTERNS = [
    (Platform.YOUTUBE,      r'(?:youtube\.com|youtu\.be|youtube-nocookie\.com)'),
    (Platform.TIKTOK,       r'(?:tiktok\.com|vm\.tiktok\.com)'),
    (Platform.DOUYIN,       r'(?:douyin\.com|v\.douyin\.com|iesdouyin\.com)'),
    (Platform.BILIBILI,     r'(?:bilibili\.com|b23\.tv|b29\.tv)'),
    (Platform.TWITTER,      r'(?:twitter\.com|x\.com|t\.co)'),
    (Platform.INSTAGRAM,    r'(?:instagram\.com|instagr\.am)'),
    (Platform.FACEBOOK,     r'(?:facebook\.com|fb\.watch|fb\.com)'),
    (Platform.REDDIT,       r'(?:reddit\.com|redd\.it)'),
    (Platform.VIMEO,        r'vimeo\.com'),
    (Platform.DAILYMOTION,  r'(?:dailymotion\.com|dai\.ly)'),
    (Platform.IXIGUA,       r'ixigua\.com'),
    (Platform.WEIBO,        r'(?:weibo\.com|weibo\.cn|t\.cn)'),
    (Platform.XIAOHONGSHU,  r'(?:xiaohongshu\.com|xhslink\.com)'),
]


def detect_platform(url: str) -> str:
    url_lower = url.lower().strip()
    for platform, pattern in PLATFORM_PATTERNS:
        if re.search(pattern, url_lower):
            return platform
    return Platform.UNKNOWN


SUPPORTED_PLATFORMS = [
    {"name": "YouTube", "icon": "YT", "color": "#FF0000"},
    {"name": "TikTok", "icon": "TT", "color": "#000000"},
    {"name": "抖音", "icon": "DY", "color": "#161823"},
    {"name": "B站", "icon": "B", "color": "#00A1D6"},
    {"name": "Twitter/X", "icon": "X", "color": "#000000"},
    {"name": "Instagram", "icon": "IG", "color": "#E4405F"},
    {"name": "Facebook", "icon": "FB", "color": "#1877F2"},
    {"name": "Reddit", "icon": "R", "color": "#FF4500"},
    {"name": "Vimeo", "icon": "V", "color": "#1AB7EA"},
    {"name": "Dailymotion", "icon": "DM", "color": "#0066DC"},
    {"name": "西瓜视频", "icon": "XG", "color": "#FF4256"},
    {"name": "微博", "icon": "WB", "color": "#E6162D"},
    {"name": "小红书", "icon": "XHS", "color": "#FF2442"},
]


# ────────────────── 下载器 ──────────────────

class DownloaderService:

    def __init__(self):
        self.download_dir = Path(settings.DOWNLOAD_DIR)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def submit_download(self, db: Session, user: User, url: str) -> DownloadTask:
        """创建下载任务并入队"""
        platform = detect_platform(url)
        task_id = uuid.uuid4().hex[:12]

        task = DownloadTask(
            task_id=task_id,
            user_id=user.id,
            url=url,
            platform=platform,
            status=TaskStatus.PENDING.value,
            expires_at=datetime.utcnow() + timedelta(hours=settings.TASK_EXPIRE_HOURS),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 推入 Redis 队列
        from services.task_queue import enqueue_task
        enqueue_task(task_id, {
            "url": url,
            "platform": platform,
            "user_id": str(user.id),
        })

        return task

    def process_task(self, task_id: str, task_data: dict):
        """Worker 调用: 执行实际下载"""
        db = SessionLocal()
        try:
            task = db.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
            if not task:
                return

            user_id = task_data.get("user_id", "")
            url = task_data.get("url", "")
            platform = task_data.get("platform", "")

            # 并发控制
            if not acquire_download_slot(user_id):
                task.status = TaskStatus.FAILED.value
                task.error = "已有下载任务进行中，请等待完成"
                db.commit()
                return

            try:
                task.status = TaskStatus.ANALYZING.value
                db.commit()
                update_task_progress(task_id, 0, status="analyzing")

                # 路由到平台专用下载器
                if platform == Platform.XIAOHONGSHU:
                    local_file = self._download_xiaohongshu(task, db)
                elif platform == Platform.DOUYIN:
                    local_file = self._download_douyin(task, db)
                elif platform == Platform.BILIBILI:
                    local_file = self._download_bilibili(task, db)
                else:
                    local_file = self._download_ytdlp(task, db)

                if not local_file or not os.path.exists(local_file):
                    task.status = TaskStatus.FAILED.value
                    task.error = "下载完成但未找到文件"
                    db.commit()
                    return

                # 上传到 OSS
                task.status = TaskStatus.UPLOADING.value
                task.progress = 95.0
                db.commit()
                update_task_progress(task_id, 95, status="uploading")

                oss_key, oss_url = oss_storage.upload_file(local_file, user_id, platform)

                file_size = os.path.getsize(local_file)
                task.status = TaskStatus.COMPLETED.value
                task.progress = 100.0
                task.file_size = file_size
                task.file_size_str = self._format_size(file_size)
                task.oss_key = oss_key
                task.oss_url = oss_url
                task.completed_at = datetime.utcnow()
                db.commit()
                update_task_progress(task_id, 100, status="completed")

                # 删除本地临时文件
                if oss_storage.available and os.path.exists(local_file):
                    os.remove(local_file)

                # 增加配额
                from core.deps import increment_quota
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    increment_quota(db, user, file_size / (1024 * 1024))

            finally:
                release_download_slot(user_id)

        except Exception as e:
            task = db.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED.value
                task.error = str(e)[:500]
                task.completed_at = datetime.utcnow()
                db.commit()
            update_task_progress(task_id, 0, status="failed", error=str(e)[:200])
        finally:
            db.close()

    # ──── yt-dlp 通用下载 ────

    def _download_ytdlp(self, task: DownloadTask, db: Session) -> Optional[str]:
        ydl_opts = {
            "format": "best",
            "format_sort": ["res", "fps", "br", "size"],
            "outtmpl": str(self.download_dir / f"{task.task_id}_%(title).80s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }

        # 提取信息
        with yt_dlp.YoutubeDL({**ydl_opts, "skip_download": True}) as ydl:
            info = ydl.extract_info(task.url, download=False)

        if info:
            task.title = (info.get("title", "未知标题") or "未知标题")[:200]
            task.author = info.get("uploader", info.get("channel", info.get("author", "")))[:200]
            task.duration = self._format_duration(info.get("duration", 0))
            task.thumbnail = info.get("thumbnail", "")
            task.status = TaskStatus.DOWNLOADING.value
            db.commit()

        def progress_hook(d):
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    pct = float(pct)
                except ValueError:
                    pct = 0
                task.progress = min(pct, 99)
                task.speed = d.get("_speed_str", "").strip()
                task.eta = d.get("_eta_str", "").strip()
                db.commit()
                update_task_progress(task.task_id, task.progress, status="downloading",
                                     speed=task.speed, eta=task.eta)

        ydl_opts["progress_hooks"] = [progress_hook]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([task.url])

        return self._find_file(task.task_id)

    # ──── 抖音专用下载 ────

    def _download_douyin(self, task: DownloadTask, db: Session) -> Optional[str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/90.0.4430.91",
        }
        # 解析短链接
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            resp = client.get(task.url, headers=headers)
            final_url = str(resp.url)

        # 从 iesdouyin 获取视频信息
        aweme_id = re.search(r'/video/(\d+)', final_url)
        if not aweme_id:
            # 尝试从分享文本提取
            aweme_id = re.search(r'/(\d+)', final_url)
        if not aweme_id:
            raise RuntimeError("无法提取抖音视频ID")

        api_url = f"https://www.iesdouyin.com/share/video/{aweme_id.group(1)}"
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            resp = client.get(api_url, headers=headers)
            html = resp.text

        # 提取 _ROUTER_DATA
        match = re.search(r'_ROUTER_DATA\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
        if not match:
            raise RuntimeError("无法解析抖音页面数据")

        import json
        data = json.loads(match.group(1))
        loader = data.get("loaderData", {})
        video_info = loader.get("video_(id)/page", {})

        if not video_info:
            # 尝试其他路径
            for v in loader.values():
                if isinstance(v, dict) and "videoInfoRes" in v:
                    video_info = v
                    break

        video_data = video_info.get("videoInfoRes", {}).get("item_list", [{}])[0] if video_info else {}
        if not video_data:
            raise RuntimeError("未找到视频数据")

        task.title = (video_data.get("desc", "抖音视频") or "抖音视频")[:200]
        task.author = video_data.get("author", {}).get("nickname", "")[:200]
        task.duration = self._format_duration(video_data.get("duration", 0) // 1000)
        task.thumbnail = video_data.get("video", {}).get("cover", {}).get("url_list", [""])[0]
        task.status = TaskStatus.DOWNLOADING.value
        db.commit()
        update_task_progress(task.task_id, 10, status="downloading")

        # 获取无水印视频 URL
        play_addr = video_data.get("video", {}).get("play_addr", {})
        url_list = play_addr.get("url_list", [])
        if not url_list:
            raise RuntimeError("未找到视频下载地址")

        video_url = url_list[0].replace("playwm", "play")

        # 下载
        task.progress = 50
        db.commit()
        filename = f"{task.task_id}_douyin.mp4"
        filepath = str(self.download_dir / filename)

        with httpx.Client(follow_redirects=True, timeout=120) as client:
            with client.stream("GET", video_url, headers=headers) as resp:
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)

        task.progress = 90
        db.commit()

        return filepath

    # ──── B站专用下载 ────

    def _download_bilibili(self, task: DownloadTask, db: Session) -> Optional[str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
        }

        # 解析短链接
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            resp = client.get(task.url, headers=headers)
            final_url = str(resp.url)

        # 提取 BV 号
        bv = re.search(r'(BV\w+)', final_url)
        if not bv:
            raise RuntimeError("无法提取B站视频ID")
        bvid = bv.group(1)

        # 获取视频信息
        info_api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        with httpx.Client(timeout=15) as client:
            resp = client.get(info_api, headers=headers)
            info_data = resp.json()

        if info_data.get("code") != 0:
            raise RuntimeError(f"B站API错误: {info_data.get('message')}")

        vdata = info_data["data"]
        aid = vdata["aid"]
        cid = vdata["cid"]
        task.title = vdata.get("title", "B站视频")[:200]
        task.author = vdata.get("owner", {}).get("name", "")[:200]
        task.duration = self._format_duration(vdata.get("duration", 0))
        task.thumbnail = vdata.get("pic", "")
        task.status = TaskStatus.DOWNLOADING.value
        db.commit()
        update_task_progress(task.task_id, 10, status="downloading")

        # 请求 DASH 格式 (最高清)
        play_api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=127&fnval=4048"
        with httpx.Client(timeout=15) as client:
            resp = client.get(play_api, headers=headers)
            play_data = resp.json()

        video_url = None
        audio_url = None

        if play_data.get("data", {}).get("dash"):
            dash = play_data["data"]["dash"]
            videos = sorted(dash.get("video", []), key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
            if videos:
                video_url = videos[0]["baseUrl"] or videos[0]["base_url"]
            audios = sorted(dash.get("audio", []), key=lambda x: x.get("bandwidth", 0), reverse=True)
            if audios:
                audio_url = audios[0]["baseUrl"] or audios[0]["base_url"]

        if not video_url:
            # 回退到 durl
            durl_api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=127&fnval=1"
            with httpx.Client(timeout=15) as client:
                resp = client.get(durl_api, headers=headers)
                durl_data = resp.json()
            durls = durl_data.get("data", {}).get("durl", [])
            if durls:
                video_url = durls[0]["url"]

        if not video_url:
            raise RuntimeError("未找到B站视频下载地址")

        task.progress = 30
        db.commit()

        # 下载视频流
        filename = f"{task.task_id}_bilibili.mp4"
        filepath = str(self.download_dir / filename)
        v_temp = filepath + ".v"
        a_temp = filepath + ".a"

        dl_headers = {**headers, "Referer": "https://www.bilibili.com/"}

        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", video_url, headers=dl_headers) as resp:
                with open(v_temp, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)

            task.progress = 70
            db.commit()

            if audio_url:
                with client.stream("GET", audio_url, headers=dl_headers) as resp:
                    with open(a_temp, "wb") as f:
                        for chunk in resp.iter_bytes():
                            f.write(chunk)

        task.status = TaskStatus.PROCESSING.value
        task.progress = 85
        db.commit()
        update_task_progress(task.task_id, 85, status="processing")

        # 合并音视频
        if audio_url and os.path.exists(a_temp):
            cmd = ["ffmpeg", "-y", "-i", v_temp, "-i", a_temp, "-c", "copy", filepath]
            subprocess.run(cmd, capture_output=True, timeout=120)
            os.remove(v_temp)
            os.remove(a_temp)
        else:
            os.rename(v_temp, filepath)

        return filepath

    # ──── 小红书专用下载 ────

    def _download_xiaohongshu(self, task: DownloadTask, db: Session) -> Optional[str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        with httpx.Client(follow_redirects=True, timeout=15) as client:
            resp = client.get(task.url, headers=headers)
            html = resp.text

        # 提取视频 URL
        import json
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
        if match:
            state = json.loads(match.group(1))
            note = state.get("note", {}).get("noteDetailMap", {})
            for v in note.values():
                note_data = v.get("note", {})
                task.title = (note_data.get("title", "小红书视频") or "小红书视频")[:200]
                task.author = note_data.get("user", {}).get("nickname", "")[:200]
                video = note_data.get("video", {})
                media = video.get("media", {}).get("stream", {})
                codecs = list(media.values())
                if codecs and codecs[0].get("urls"):
                    video_url = list(codecs[0]["urls"].values())[0]
                    task.thumbnail = note_data.get("imageList", [{}])[0].get("urlDefault", "")
                    task.status = TaskStatus.DOWNLOADING.value
                    db.commit()
                    update_task_progress(task.task_id, 20, status="downloading")

                    filename = f"{task.task_id}_xhs.mp4"
                    filepath = str(self.download_dir / filename)
                    with httpx.Client(timeout=120, follow_redirects=True) as client:
                        with client.stream("GET", video_url, headers=headers) as resp:
                            with open(filepath, "wb") as f:
                                for chunk in resp.iter_bytes():
                                    f.write(chunk)

                    task.progress = 90
                    db.commit()
                    return filepath

        raise RuntimeError("无法解析小红书视频")

    # ──── 水印去除 ────

    def remove_watermark(self, db: Session, task: DownloadTask, x: int, y: int, w: int, h: int) -> str:
        """下载视频到本地，去除水印，重新上传 OSS"""
        import tempfile

        # 从 OSS 下载到临时文件
        temp_dir = Path(tempfile.mkdtemp())
        input_path = str(temp_dir / f"input_{task.task_id}.mp4")
        output_path = str(temp_dir / f"output_{task.task_id}.mp4")

        if task.oss_url and not task.oss_url.startswith("local://"):
            with httpx.Client(timeout=120, follow_redirects=True) as client:
                with client.stream("GET", task.oss_url) as resp:
                    with open(input_path, "wb") as f:
                        for chunk in resp.iter_bytes():
                            f.write(chunk)
        elif task.oss_key:
            # 本地文件
            local_path = task.oss_key.replace("local://", "")
            if os.path.exists(local_path):
                input_path = local_path

        if not os.path.exists(input_path):
            raise FileNotFoundError("视频文件不存在")

        # ffprobe 获取分辨率
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", input_path],
            capture_output=True, text=True, timeout=15
        )
        parts = probe.stdout.strip().split(",")
        video_w, video_h = int(parts[0]), int(parts[1])

        pad = 4
        x_c = max(0, x - pad)
        y_c = max(0, y - pad)
        w_c = min(w + pad * 2, video_w - x_c)
        h_c = min(h + pad * 2, video_h - y_c)

        delogo = f"delogo=x={x_c}:y={y_c}:w={w_c}:h={h_c}"
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", delogo,
               "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-crf", "18", output_path]
        result = subprocess.run(cmd, capture_output=True, timeout=300)

        if result.returncode != 0 or not os.path.exists(output_path):
            # 回退高斯模糊
            blur = (f"crop={w_c}:{h_c}:{x_c}:{y_c},gblur=sigma=20[blurred];"
                    f"[0:v][blurred]overlay={x_c}:{y_c}")
            cmd2 = ["ffmpeg", "-y", "-i", input_path, "-filter_complex", blur,
                    "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-crf", "18", output_path]
            subprocess.run(cmd2, capture_output=True, timeout=300)

        # 上传处理后的视频
        oss_key, oss_url = oss_storage.upload_file(output_path, str(task.user_id), task.platform + "_nowm")

        # 删除旧文件
        if task.oss_key:
            oss_storage.delete_file(task.oss_key)

        # 更新任务
        task.oss_key = oss_key
        task.oss_url = oss_url
        task.watermark_processed = True
        task.watermark_x = x
        task.watermark_y = y
        task.watermark_w = w
        task.watermark_h = h
        file_size = os.path.getsize(output_path)
        task.file_size = file_size
        task.file_size_str = self._format_size(file_size)
        db.commit()

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        return oss_url

    # ──── 工具方法 ────

    def _find_file(self, task_id: str) -> Optional[str]:
        files = list(self.download_dir.glob(f"{task_id}_*"))
        if files:
            return str(files[0])
        return None

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _format_duration(self, seconds: int) -> str:
        if not seconds:
            return ""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


downloader_service = DownloaderService()
