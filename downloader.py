#!/usr/bin/env python3
"""
视频下载智能体 - 核心下载模块
支持多平台无水印视频下载，基于 yt-dlp 引擎
"""

import os
import re
import json
import time
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

import yt_dlp


# ──────────────────────────── 平台检测 ────────────────────────────

class Platform(Enum):
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


# 平台 URL 匹配规则（按优先级排序）
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


def detect_platform(url: str) -> Platform:
    """从 URL 自动检测视频平台"""
    url_lower = url.lower().strip()
    for platform, pattern in PLATFORM_PATTERNS:
        if re.search(pattern, url_lower):
            return platform
    return Platform.UNKNOWN


# ──────────────────────────── 下载状态 ────────────────────────────

class DownloadStatus(Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"      # 正在解析视频信息
    DOWNLOADING = "downloading"  # 正在下载
    PROCESSING = "processing"    # 正在合并/后处理
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    """单个下载任务"""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    url: str = ""
    platform: str = ""
    status: str = DownloadStatus.PENDING.value
    title: str = ""
    author: str = ""
    duration: str = ""
    thumbnail: str = ""
    file_path: str = ""
    file_size: int = 0
    file_size_str: str = ""
    progress: float = 0.0       # 0-100
    speed: str = ""
    eta: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    completed_at: str = ""
    watermark_free: bool = True  # 标记是否为无水印版本

    def to_dict(self) -> dict:
        return asdict(self)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)


# ──────────────────────────── 核心下载器 ────────────────────────────

class VideoDownloader:
    """视频下载器 - 基于 yt-dlp，自动无水印"""

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: dict[str, DownloadTask] = {}
        self._lock = threading.Lock()
        # 启动时恢复已有的下载文件
        self._recover_existing_files()

    def _recover_existing_files(self):
        """扫描下载目录，将已有的视频文件恢复为已完成任务"""
        extensions = ['*.mp4', '*.webm', '*.mkv']
        files = []
        for ext in extensions:
            files.extend(self.download_dir.glob(ext))

        for f in files:
            # 跳过临时文件
            if '_temp_' in f.name:
                continue

            # 从文件名推断平台
            platform = "未知平台"
            if '_douyin' in f.name:
                platform = "抖音"
            elif '_bilibili' in f.name:
                platform = "B站"
            elif '_xhs' in f.name:
                platform = "小红书"

            # 从文件名提取标题（去掉平台后缀和扩展名）
            title = f.stem
            for suffix in ['_douyin', '_bilibili', '_xhs']:
                if title.endswith(suffix):
                    title = title[:-len(suffix)]
                    break

            file_size = f.stat().st_size
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            task = DownloadTask(
                url="(已恢复)",
                platform=platform,
                status=DownloadStatus.COMPLETED.value,
                title=title,
                file_path=str(f),
                file_size=file_size,
                file_size_str=self._format_size(file_size),
                progress=100.0,
                created_at=mtime,
                completed_at=mtime,
                watermark_free=True,
            )
            self.tasks[task.task_id] = task

    # ──── 公共 API ────

    def submit(self, url: str) -> DownloadTask:
        """提交一个下载任务（异步执行）"""
        url = url.strip()
        if not url:
            raise ValueError("URL 不能为空")

        platform = detect_platform(url)
        task = DownloadTask(
            url=url,
            platform=platform.value,
            watermark_free=True,
        )

        with self._lock:
            self.tasks[task.task_id] = task

        # 启动后台线程执行下载
        thread = threading.Thread(target=self._run_download, args=(task,), daemon=True)
        thread.start()

        return task

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[DownloadTask]:
        return sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)

    def delete_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        # 如果文件存在，删除文件
        if task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except OSError:
                pass
        del self.tasks[task_id]
        return True

    def get_file_path(self, task_id: str) -> Optional[str]:
        task = self.tasks.get(task_id)
        if task and task.file_path and os.path.exists(task.file_path):
            return task.file_path
        return None

    def remove_watermark(self, task_id: str, x: int, y: int, w: int, h: int) -> str:
        """对已完成任务的视频去除指定区域的水印（ffmpeg delogo 滤镜）
        
        Args:
            task_id: 任务 ID
            x, y: 水印区域左上角坐标
            w, h: 水印区域宽高
        
        Returns:
            输出文件路径
        """
        import subprocess

        task = self.tasks.get(task_id)
        if not task or not task.file_path or not os.path.exists(task.file_path):
            raise FileNotFoundError("视频文件不存在")

        input_path = task.file_path

        # 先用 ffprobe 获取视频分辨率
        probe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0", input_path,
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
        if probe_result.returncode != 0:
            raise RuntimeError(f"无法获取视频分辨率: {probe_result.stderr}")

        parts = probe_result.stdout.strip().split(',')
        video_w, video_h = int(parts[0]), int(parts[1])

        # 约束水印区域在视频范围内，并加 padding 防止 delogo 边界报错
        pad = 4
        x_clamped = max(0, x - pad)
        y_clamped = max(0, y - pad)
        w_clamped = min(w + pad * 2, video_w - x_clamped)
        h_clamped = min(h + pad * 2, video_h - y_clamped)

        # 生成输出文件名
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_nowm{ext}"

        # 使用 ffmpeg delogo 滤镜去除水印
        # delogo=x:y:w:h 会对指定区域进行插值修复
        delogo_filter = f"delogo=x={x_clamped}:y={y_clamped}:w={w_clamped}:h={h_clamped}"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", delogo_filter,
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)

        if result.returncode != 0 or not os.path.exists(output_path):
            # 如果 delogo 失败，回退到高斯模糊方案
            blur_filter = (
                f"crop={w_clamped}:{h_clamped}:{x_clamped}:{y_clamped},"
                f"gblur=sigma=20[blurred];"
                f"[0:v][blurred]overlay={x_clamped}:{y_clamped}"
            )
            cmd2 = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-filter_complex", blur_filter,
                "-c:a", "copy",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                output_path,
            ]
            result2 = subprocess.run(cmd2, capture_output=True, timeout=300)
            if result2.returncode != 0 or not os.path.exists(output_path):
                raise RuntimeError(f"去水印处理失败: {result2.stderr.decode()[:300]}")

        # 更新任务信息
        file_size = os.path.getsize(output_path)
        task.update(
            file_path=output_path,
            file_size=file_size,
            file_size_str=self._format_size(file_size),
        )

        # 删除原始文件
        if os.path.exists(input_path) and input_path != output_path:
            os.remove(input_path)

        return output_path

    # ──── 内部下载逻辑 ────

    def _run_download(self, task: DownloadTask):
        """在后台线程中执行下载"""
        try:
            task.update(status=DownloadStatus.ANALYZING.value)

            # 小红书使用专用下载器（yt-dlp 不支持）
            if task.platform == Platform.XIAOHONGSHU.value:
                self._download_xiaohongshu(task)
                return

            # 抖音使用专用下载器（yt-dlp 需要 cookie）
            if task.platform == Platform.DOUYIN.value:
                self._download_douyin(task)
                return

            # B站：先解析 b23.tv 短链接
            if task.platform == Platform.BILIBILI.value:
                self._download_bilibili(task)
                return

            # 构建 yt-dlp 选项
            ydl_opts = self._build_ydl_opts(task)

            # 先提取视频信息
            with yt_dlp.YoutubeDL({**ydl_opts, 'skip_download': True}) as ydl:
                info = ydl.extract_info(task.url, download=False)

            if info:
                task.update(
                    title=info.get('title', '未知标题')[:200],
                    author=info.get('uploader', info.get('channel', info.get('author', '未知'))),
                    duration=self._format_duration(info.get('duration', 0)),
                    thumbnail=info.get('thumbnail', ''),
                )

            # 执行下载
            task.update(status=DownloadStatus.DOWNLOADING.value)

            def progress_hook(d):
                self._handle_progress(d, task)

            ydl_opts['progress_hooks'] = [progress_hook]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([task.url])

            # 查找下载的文件
            downloaded_file = self._find_downloaded_file(task)
            if downloaded_file:
                file_size = os.path.getsize(downloaded_file)
                task.update(
                    status=DownloadStatus.COMPLETED.value,
                    file_path=str(downloaded_file),
                    file_size=file_size,
                    file_size_str=self._format_size(file_size),
                    progress=100.0,
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    speed="",
                    eta="",
                )
            else:
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="下载完成但未找到输出文件",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            # 友好化常见错误
            if "HTTP Error 403" in error_msg:
                error_msg = "访问被拒绝(403)，可能需要登录或提供 Cookie"
            elif "HTTP Error 429" in error_msg:
                error_msg = "请求过于频繁(429)，请稍后重试"
            elif "Unsupported URL" in error_msg:
                error_msg = "不支持的视频链接，请检查 URL 是否正确"
            elif "Video unavailable" in error_msg:
                error_msg = "视频不可用，可能已被删除或设为私密"

            task.update(
                status=DownloadStatus.FAILED.value,
                error=error_msg,
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            task.update(
                status=DownloadStatus.FAILED.value,
                error=f"未知错误: {str(e)}",
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

    def _download_xiaohongshu(self, task: DownloadTask):
        """小红书专用下载器 - 解析页面提取无水印视频直链"""
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.xiaohongshu.com/",
        }

        try:
            # Step 1: 解析短链接，获取实际页面 URL
            with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
                resp = client.get(task.url)
                page_url = str(resp.url)
                html = resp.text

            # Step 2: 提取视频直链（小红书页面中嵌入的 mp4 URL）
            video_urls = re.findall(r'(https?://sns-video[^"\'\s]+\.mp4[^"\'\s]*)', html)

            if not video_urls:
                # 尝试从 __INITIAL_STATE__ 中提取
                state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', html, re.DOTALL)
                if state_match:
                    state_raw = state_match.group(1)
                    # 替换 undefined 为 null 以便 JSON 解析
                    state_raw = state_raw.replace('undefined', 'null')
                    try:
                        state = json.loads(state_raw)
                        # 深度搜索视频 URL
                        def find_video_url(obj):
                            if isinstance(obj, str) and 'sns-video' in obj and '.mp4' in obj:
                                return obj
                            if isinstance(obj, dict):
                                for v in obj.values():
                                    result = find_video_url(v)
                                    if result:
                                        return result
                            if isinstance(obj, list):
                                for item in obj:
                                    result = find_video_url(item)
                                    if result:
                                        return result
                            return None
                        found = find_video_url(state)
                        if found:
                            video_urls = [found]
                    except json.JSONDecodeError:
                        pass

            if not video_urls:
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="未能从小红书页面提取视频地址，可能该笔记不含视频或需要登录",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return

            # 去重并选择最高清的视频地址
            # 小红书视频 URL 中可能包含不同清晰度版本
            # 优先选择 URL 中含有更高分辨率标识的地址
            unique_urls = list(dict.fromkeys(video_urls))  # 去重保持顺序

            def video_quality_score(url):
                """根据 URL 特征估算视频质量分数"""
                score = 0
                url_lower = url.lower()
                # 小红书视频 URL 中的质量标识
                if 'fmv2' in url_lower or 'fv2' in url_lower:
                    score += 100  # 高清
                if 'hd' in url_lower:
                    score += 50
                # URL 更长通常包含更多参数，可能是更高清版本
                score += len(url) // 100
                # 偏好 mp4 格式
                if url_lower.endswith('.mp4') or '.mp4?' in url_lower:
                    score += 10
                return score

            unique_urls.sort(key=video_quality_score, reverse=True)
            video_url = unique_urls[0]

            # Step 3: 提取元数据
            title = "小红书视频"
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html)
            if title_match:
                title = title_match.group(1).replace(' - 小红书', '').strip()[:200]

            # 提取作者
            author = ""
            author_match = re.search(r'"nickName"\s*:\s*"([^"]+)"', html)
            if author_match:
                author = author_match.group(1)

            # 提取缩略图
            thumbnail = ""
            thumb_match = re.findall(r'"urlDefault"\s*:\s*"(https?://[^"]+)"', html)
            if thumb_match:
                thumbnail = thumb_match[0]

            task.update(
                title=title,
                author=author or "小红书用户",
                thumbnail=thumbnail,
            )

            # Step 4: 下载视频文件
            task.update(status=DownloadStatus.DOWNLOADING.value, progress=0.0)

            # 清理文件名
            safe_title = re.sub(r'[\\/:*?"<>|\n\r]', '_', title)[:80]
            filename = f"{safe_title}_xhs.mp4"
            filepath = self.download_dir / filename

            with httpx.Client(timeout=60, headers=headers) as client:
                with client.stream("GET", video_url) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    start_time = time.time()

                    with open(filepath, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                progress = (downloaded / total) * 100
                                elapsed = time.time() - start_time
                                speed_val = downloaded / elapsed if elapsed > 0 else 0
                                task.update(
                                    progress=round(progress, 1),
                                    file_size_str=self._format_size(downloaded),
                                    speed=self._format_speed(speed_val),
                                )

            # 完成
            file_size = os.path.getsize(filepath)
            task.update(
                status=DownloadStatus.COMPLETED.value,
                file_path=str(filepath),
                file_size=file_size,
                file_size_str=self._format_size(file_size),
                progress=100.0,
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                speed="",
                eta="",
            )

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                error_msg = "小红书笔记不存在或已被删除"
            elif "403" in error_msg:
                error_msg = "访问被拒绝，可能需要登录"
            task.update(
                status=DownloadStatus.FAILED.value,
                error=f"小红书下载失败: {error_msg}",
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

    def _resolve_short_url(self, url: str) -> str:
        """解析短链接，返回最终 URL"""
        import httpx
        try:
            with httpx.Client(follow_redirects=True, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }) as client:
                resp = client.get(url)
                return str(resp.url)
        except Exception:
            return url

    def _download_douyin(self, task: DownloadTask):
        """抖音专用下载器 - 通过 iesdouyin.com 分享页提取无水印视频"""
        import httpx

        mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"

        try:
            # Step 1: 解析短链接获取 video_id
            with httpx.Client(follow_redirects=True, timeout=20, headers={"User-Agent": mobile_ua}) as client:
                resp = client.get(task.url)
                final_url = str(resp.url)

            # 提取 video_id
            vid_match = re.search(r'/video/(\d+)', final_url)
            if not vid_match:
                # 尝试从原始 URL 提取
                vid_match = re.search(r'/(\d{15,})', final_url)

            if not vid_match:
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="无法从抖音链接中提取视频 ID",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return

            video_id = vid_match.group(1)

            # Step 2: 访问 iesdouyin.com 分享页获取 _ROUTER_DATA
            with httpx.Client(follow_redirects=True, timeout=20, headers={"User-Agent": mobile_ua}) as client:
                resp = client.get(f"https://www.iesdouyin.com/share/video/{video_id}/")
                html = resp.text

            # 提取 _ROUTER_DATA
            router_match = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>', html, re.DOTALL)
            if not router_match:
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="无法从抖音分享页提取视频数据",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return

            try:
                router_data = json.loads(router_match.group(1))
            except json.JSONDecodeError:
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="抖音视频数据解析失败",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return

            # Step 3: 深度搜索 play_addr 和元数据
            def find_field(obj, field, depth=0):
                if depth > 25:
                    return None
                if isinstance(obj, dict) and field in obj:
                    return obj[field]
                if isinstance(obj, dict):
                    for v in obj.values():
                        r = find_field(v, field, depth + 1)
                        if r is not None:
                            return r
                if isinstance(obj, list):
                    for item in obj:
                        r = find_field(item, field, depth + 1)
                        if r is not None:
                            return r
                return None

            play_addr = find_field(router_data, 'play_addr')
            play_addr_h264 = find_field(router_data, 'play_addr_h264')
            desc = find_field(router_data, 'desc') or "抖音视频"
            nickname = find_field(router_data, 'nickname') or "抖音用户"
            duration = find_field(router_data, 'duration') or 0
            cover = find_field(router_data, 'cover')
            thumbnail = ""
            if isinstance(cover, dict):
                thumbnail = cover.get('url_list', [''])[0] if cover.get('url_list') else ""

            if not play_addr or not isinstance(play_addr, dict):
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="未找到抖音视频播放地址",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return

            url_list = play_addr.get('url_list', [])
            if not url_list:
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="抖音视频播放地址为空",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return

            # Step 4: 选择最高清的视频流并去除水印
            # play_addr 通常是最高清的（可能包含 265 编码的高清流）
            # 收集所有可用的视频流地址，按宽度和码率排序选最高清
            candidate_streams = []

            def collect_video_streams(obj, depth=0):
                """递归收集所有 play_addr 类的视频流"""
                if depth > 25:
                    return
                if isinstance(obj, dict):
                    # 检查是否是视频流地址对象
                    if 'url_list' in obj and isinstance(obj['url_list'], list):
                        width = obj.get('width', 0)
                        height = obj.get('height', 0)
                        data_size = obj.get('data_size', 0)
                        url = obj['url_list'][0] if obj['url_list'] else ""
                        if url and ('.mp4' in url or 'douyin' in url or 'bytecdn' in url or 'aweme' in url):
                            candidate_streams.append({
                                'url': url,
                                'width': width,
                                'height': height,
                                'resolution': width * height,
                                'data_size': data_size,
                            })
                    for v in obj.values():
                        collect_video_streams(v, depth + 1)
                if isinstance(obj, list):
                    for item in obj:
                        collect_video_streams(item, depth + 1)

            collect_video_streams(router_data)

            # 按 resolution 降序排序，选最高清的
            if candidate_streams:
                candidate_streams.sort(key=lambda s: s['resolution'], reverse=True)
                best_stream = candidate_streams[0]
                video_url = best_stream['url']
            elif url_list:
                video_url = url_list[0]
            else:
                task.update(
                    status=DownloadStatus.FAILED.value,
                    error="抖音视频播放地址为空",
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return

            # 将 playwm 替换为 play 获取无水印地址
            video_url = video_url.replace('playwm', 'play')

            task.update(
                title=desc[:200],
                author=nickname,
                duration=self._format_duration(duration / 1000 if duration > 1000 else duration),
                thumbnail=thumbnail,
            )

            # Step 5: 下载视频
            task.update(status=DownloadStatus.DOWNLOADING.value, progress=0.0)

            safe_title = re.sub(r'[\\/:*?"<>|\n\r#]', '_', desc)[:80]
            filename = f"{safe_title}_douyin.mp4"
            filepath = self.download_dir / filename

            download_headers = {
                "User-Agent": mobile_ua,
                "Referer": "https://www.iesdouyin.com/",
            }

            with httpx.Client(timeout=120, headers=download_headers, follow_redirects=True) as client:
                with client.stream("GET", video_url) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    start_time = time.time()

                    with open(filepath, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                progress = (downloaded / total) * 100
                                elapsed = time.time() - start_time
                                speed_val = downloaded / elapsed if elapsed > 0 else 0
                                task.update(
                                    progress=round(progress, 1),
                                    file_size_str=self._format_size(downloaded),
                                    speed=self._format_speed(speed_val),
                                )

            file_size = os.path.getsize(filepath)
            task.update(
                status=DownloadStatus.COMPLETED.value,
                file_path=str(filepath),
                file_size=file_size,
                file_size_str=self._format_size(file_size),
                progress=100.0,
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                speed="",
                eta="",
            )

        except Exception as e:
            error_msg = str(e)
            task.update(
                status=DownloadStatus.FAILED.value,
                error=f"抖音下载失败: {error_msg}",
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

    def _download_bilibili(self, task: DownloadTask):
        """B站专用下载器 - 通过 Bilibili API 获取无水印视频"""
        import httpx
        import subprocess

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        }

        try:
            with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
                # Step 1: 解析短链接获取 BV ID
                resp = client.get(task.url)
                final_url = str(resp.url)

                bv_match = re.search(r'(BV[a-zA-Z0-9]+)', final_url)
                if not bv_match:
                    task.update(
                        status=DownloadStatus.FAILED.value,
                        error="无法从B站链接中提取视频 ID",
                        completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    return

                bvid = bv_match.group(1)

                # Step 2: 获取视频信息
                info_resp = client.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
                if info_resp.status_code != 200:
                    task.update(
                        status=DownloadStatus.FAILED.value,
                        error=f"B站 API 返回错误: {info_resp.status_code}",
                        completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    return

                info_data = info_resp.json()
                if info_data.get('code') != 0:
                    task.update(
                        status=DownloadStatus.FAILED.value,
                        error=f"B站视频信息获取失败: {info_data.get('message', '未知错误')}",
                        completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    return

                vdata = info_data['data']
                cid = vdata.get('cid')
                title = vdata.get('title', 'B站视频')
                author = vdata.get('owner', {}).get('name', 'B站用户')
                duration = vdata.get('duration', 0)
                thumbnail = vdata.get('pic', '')

                task.update(
                    title=title[:200],
                    author=author,
                    duration=self._format_duration(duration),
                    thumbnail=thumbnail,
                )

                # Step 3: 获取视频流地址 - 同时请求 durl 和 DASH 两种格式，选最高清
                # qn=127: 请求最高画质(4K HDR)，B站会返回实际可用的最高画质
                # fnval=4048: DASH 格式（分离音视频流，画质可能受限）
                # fnval=1: durl 格式（单文件，未登录时画质通常更高）

                # 3a: 请求 DASH 格式
                dash_resp = client.get(
                    f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=127&fnval=4048&fourk=1"
                )
                dash_data = None
                if dash_resp.status_code == 200:
                    dj = dash_resp.json()
                    if dj.get('code') == 0:
                        dash_data = dj['data']

                # 3b: 请求 durl 格式（未登录时通常比 DASH 画质更高）
                durl_resp = client.get(
                    f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=127&fnval=1&fourk=1"
                )
                durl_data = None
                if durl_resp.status_code == 200:
                    dj2 = durl_resp.json()
                    if dj2.get('code') == 0:
                        durl_data = dj2['data']

                if not dash_data and not durl_data:
                    task.update(
                        status=DownloadStatus.FAILED.value,
                        error="B站视频流地址获取失败",
                        completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    return

                # B站画质等级: 127=4K HDR, 120=4K, 116=1080P60, 112=1080P+, 80=1080P, 64=720P, 32=480P, 16=360P
                QN_RESOLUTIONS = {127: 2160, 120: 2160, 116: 1080, 112: 1080, 80: 1080, 64: 720, 32: 480, 16: 360}

                dash_quality = dash_data.get('quality', 0) if dash_data else 0
                durl_quality = durl_data.get('quality', 0) if durl_data else 0

                # 计算 DASH 最佳视频流分辨率
                dash_best_height = 0
                if dash_data and 'dash' in dash_data:
                    for v in dash_data['dash'].get('video', []):
                        h = v.get('height', 0)
                        if h > dash_best_height:
                            dash_best_height = h

                durl_height = QN_RESOLUTIONS.get(durl_quality, 0)
                dash_height = max(dash_best_height, QN_RESOLUTIONS.get(dash_quality, 0))

                # 选择更高画质的格式
                use_durl = durl_height >= dash_height

                # Step 4: 下载视频
                task.update(status=DownloadStatus.DOWNLOADING.value, progress=0.0)

                safe_title = re.sub(r'[\\/:*?"<>|\n\r]', '_', title)[:80]
                output_file = self.download_dir / f"{safe_title}_bilibili.mp4"

                # 方式 A: 使用 durl 单文件格式（画质更高时优先）
                if use_durl and durl_data and durl_data.get('durl'):
                    durl_entry = durl_data['durl'][0]
                    video_url = durl_entry.get('url', '')
                    total_size = durl_entry.get('size', 0)

                    if not video_url:
                        task.update(
                            status=DownloadStatus.FAILED.value,
                            error="B站视频地址为空",
                            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        )
                        return

                    # 下载单文件
                    download_headers = {**headers, "Referer": "https://www.bilibili.com/"}
                    with httpx.Client(timeout=120, headers=download_headers) as dl_client:
                        with dl_client.stream("GET", video_url) as stream_resp:
                            stream_resp.raise_for_status()
                            total = int(stream_resp.headers.get("content-length", total_size))
                            downloaded = 0
                            start_time = time.time()

                            with open(output_file, "wb") as f:
                                for chunk in stream_resp.iter_bytes(chunk_size=65536):
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if total > 0:
                                        progress = (downloaded / total) * 100
                                        elapsed = time.time() - start_time
                                        speed_val = downloaded / elapsed if elapsed > 0 else 0
                                        task.update(
                                            progress=round(progress, 1),
                                            file_size_str=self._format_size(downloaded),
                                            speed=self._format_speed(speed_val),
                                        )

                # 方式 B: 使用 DASH 格式（分离音视频流，需 ffmpeg 合并）
                elif dash_data and 'dash' in dash_data:
                    dash = dash_data['dash']
                    videos = dash.get('video', [])
                    audios = dash.get('audio', [])

                    if not videos:
                        task.update(
                            status=DownloadStatus.FAILED.value,
                            error="B站视频流为空",
                            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        )
                        return

                    # 选择最高清视频流：优先按分辨率（width*height），其次按 id 和码率
                    def video_sort_key(v):
                        w = v.get('width', 0)
                        h = v.get('height', 0)
                        vid = v.get('id', 0)
                        bandwidth = v.get('bandwidth', 0)
                        return (w * h, vid, bandwidth)

                    best_video = max(videos, key=video_sort_key)
                    video_url = best_video.get('baseUrl') or best_video.get('base_url', '')

                    # 选择最高质量音频流：按 id 和码率排序
                    audio_url = ""
                    if audios:
                        best_audio = max(audios, key=lambda a: (a.get('id', 0), a.get('bandwidth', 0)))
                        audio_url = best_audio.get('baseUrl') or best_audio.get('base_url', '')

                    if not video_url:
                        task.update(
                            status=DownloadStatus.FAILED.value,
                            error="B站视频流地址为空",
                            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        )
                        return

                    # 下载视频流和音频流
                    temp_video = self.download_dir / f"{safe_title}_temp_video.m4s"
                    temp_audio = self.download_dir / f"{safe_title}_temp_audio.m4s"
                    download_headers = {**headers, "Referer": "https://www.bilibili.com/"}

                    # 下载视频流
                    total_download_size = 0
                    start_time = time.time()

                    with httpx.Client(timeout=180, headers=download_headers) as dl_client:
                        # 下载视频
                        with dl_client.stream("GET", video_url) as v_resp:
                            v_resp.raise_for_status()
                            v_total = int(v_resp.headers.get("content-length", 0))
                            v_downloaded = 0
                            with open(temp_video, "wb") as f:
                                for chunk in v_resp.iter_bytes(chunk_size=65536):
                                    f.write(chunk)
                                    v_downloaded += len(chunk)
                                    total_download_size = v_downloaded
                                    if v_total > 0:
                                        progress = (v_downloaded / v_total) * 50  # 视频占 50%
                                        task.update(
                                            progress=round(progress, 1),
                                            file_size_str=self._format_size(v_downloaded),
                                        )

                        # 下载音频
                        if audio_url:
                            with dl_client.stream("GET", audio_url) as a_resp:
                                a_resp.raise_for_status()
                                a_total = int(a_resp.headers.get("content-length", 0))
                                a_downloaded = 0
                                with open(temp_audio, "wb") as f:
                                    for chunk in a_resp.iter_bytes(chunk_size=65536):
                                        f.write(chunk)
                                        a_downloaded += len(chunk)
                                        total_download_size += a_downloaded
                                        if a_total > 0:
                                            progress = 50 + (a_downloaded / a_total) * 40  # 音频占 40%
                                            elapsed = time.time() - start_time
                                            speed_val = total_download_size / elapsed if elapsed > 0 else 0
                                            task.update(
                                                progress=round(progress, 1),
                                                file_size_str=self._format_size(total_download_size),
                                                speed=self._format_speed(speed_val),
                                            )

                    # Step 5: 用 ffmpeg 合并音视频
                    task.update(status=DownloadStatus.PROCESSING.value, progress=95.0)

                    if audio_url and os.path.exists(temp_audio):
                        cmd = [
                            "ffmpeg", "-y",
                            "-i", str(temp_video),
                            "-i", str(temp_audio),
                            "-c", "copy",
                            "-bsf:a", "aac_adtstoasc",
                            str(output_file),
                        ]
                    else:
                        cmd = [
                            "ffmpeg", "-y",
                            "-i", str(temp_video),
                            "-c", "copy",
                            str(output_file),
                        ]

                    result = subprocess.run(cmd, capture_output=True, timeout=120)

                    # 清理临时文件
                    for temp_file in [temp_video, temp_audio]:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)

                    if result.returncode != 0:
                        # 如果 ffmpeg 合并失败，直接使用视频流
                        if os.path.exists(temp_video):
                            os.rename(temp_video, output_file)
                        else:
                            task.update(
                                status=DownloadStatus.FAILED.value,
                                error=f"ffmpeg 合并失败: {result.stderr.decode()[:200]}",
                                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            )
                            return
                else:
                    task.update(
                        status=DownloadStatus.FAILED.value,
                        error="B站返回了未知的视频格式",
                        completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    return

                # 完成
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    task.update(
                        status=DownloadStatus.COMPLETED.value,
                        file_path=str(output_file),
                        file_size=file_size,
                        file_size_str=self._format_size(file_size),
                        progress=100.0,
                        completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        speed="",
                        eta="",
                    )
                else:
                    task.update(
                        status=DownloadStatus.FAILED.value,
                        error="下载完成但未找到输出文件",
                        completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )

        except Exception as e:
            error_msg = str(e)
            task.update(
                status=DownloadStatus.FAILED.value,
                error=f"B站下载失败: {error_msg}",
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

    def _build_ydl_opts(self, task: DownloadTask) -> dict:
        """根据平台构建 yt-dlp 选项"""
        platform_str = task.platform

        # 通用选项
        opts = {
            # 选择最高清视频+最高质量音频，回退到最佳单流
            # bv*: 按分辨率降序选最佳视频流; ba: 最佳音频
            'format': 'bestvideo*+bestaudio/best',
            # 格式排序偏好：优先分辨率，其次帧率，再码率
            'format_sort': ['res', 'fps', 'br', 'size'],
            'merge_output_format': 'mp4',                # 合并为 mp4
            'outtmpl': str(self.download_dir / f'%(title)s_%(id)s.%(ext)s'),
            'restrictfilenames': False,
            'noplaylist': True,                          # 不下载播放列表
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_warnings': True,
            'quiet': True,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            # 文件名清理
            'windowsfilenames': False,
        }

        # ──── 平台特定优化 ────

        if platform_str == Platform.DOUYIN.value:
            # 抖音：使用 aweme app 身份获取无水印 play_addr
            opts['extractor_args'] = {
                'tiktok': {
                    'app_info': ['aweme/1128/35.1.3/2023501030'],
                }
            }
            # 抖音通常单流，选最高质量
            opts['format'] = 'bestvideo*+bestaudio/best'

        elif platform_str == Platform.TIKTOK.value:
            # TikTok：默认即无水印（yt-dlp 取 play_addr），选最高质量
            opts['format'] = 'bestvideo*+bestaudio/best'

        elif platform_str == Platform.BILIBILI.value:
            # B站：选择最佳质量（B站专用下载器已处理，这里用于 yt-dlp 回退）
            opts['format'] = 'bestvideo*+bestaudio/best'

        elif platform_str == Platform.INSTAGRAM.value:
            # Instagram：选最高质量
            opts['format'] = 'bestvideo*+bestaudio/best'

        elif platform_str == Platform.TWITTER.value:
            # Twitter/X：选最高质量
            opts['format'] = 'bestvideo*+bestaudio/best'

        elif platform_str == Platform.YOUTUBE.value:
            # YouTube：确保请求最高清，包括 4K/8K
            opts['format'] = 'bestvideo*+bestaudio/best'
            # 允许下载高分辨率格式
            opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            }

        return opts

    def _handle_progress(self, d: dict, task: DownloadTask):
        """处理 yt-dlp 下载进度回调"""
        status = d.get('status', '')

        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            if total > 0:
                progress = (downloaded / total) * 100
            else:
                progress = 0

            task.update(
                status=DownloadStatus.DOWNLOADING.value,
                progress=round(progress, 1),
                speed=self._format_speed(speed),
                eta=self._format_eta(eta),
                file_size_str=self._format_size(downloaded),
            )

        elif status == 'finished':
            task.update(
                status=DownloadStatus.PROCESSING.value,
                progress=99.0,
                speed="",
                eta="",
            )

    def _find_downloaded_file(self, task: DownloadTask) -> Optional[Path]:
        """在下载目录中查找刚下载的文件"""
        # 查找最近修改的 mp4/webm/mkv 文件
        extensions = ['*.mp4', '*.webm', '*.mkv', '*.m4a', '*.mp3']
        candidates = []
        for ext in extensions:
            candidates.extend(self.download_dir.glob(ext))

        if not candidates:
            return None

        # 按修改时间排序，取最新的
        candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # 如果有文件名信息，优先匹配
        if task.title:
            for f in candidates:
                # 清理标题中的特殊字符用于匹配
                clean_title = re.sub(r'[\\/:*?"<>|]', '', task.title)[:50]
                if clean_title and clean_title in f.name:
                    return f

        return candidates[0] if candidates else None

    # ──── 工具方法 ────

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def _format_speed(speed: float) -> str:
        if speed == 0:
            return ""
        return f"{VideoDownloader._format_size(int(speed))}/s"

    @staticmethod
    def _format_eta(eta: int) -> str:
        if eta == 0:
            return ""
        if eta < 60:
            return f"{eta}s"
        minutes, seconds = divmod(eta, 60)
        if minutes < 60:
            return f"{minutes}m{seconds}s"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h{minutes}m"

    @staticmethod
    def _format_duration(duration: float) -> str:
        if not duration:
            return ""
        duration = int(duration)
        if duration < 3600:
            return f"{duration // 60}:{duration % 60:02d}"
        return f"{duration // 3600}:{(duration % 3600) // 60:02d}:{duration % 60:02d}"


# ──── 全局单例 ────

downloader = VideoDownloader(download_dir=str(Path(__file__).parent / "downloads"))
