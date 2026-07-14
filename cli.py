#!/usr/bin/env python3
"""
视频下载智能体 - 命令行工具
用法: python cli.py <视频链接>
"""

import sys
import time
from downloader import downloader, detect_platform


def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main():
    if len(sys.argv) < 2:
        print("用法: python cli.py <视频链接>")
        print("示例: python cli.py https://www.youtube.com/watch?v=...")
        print("      python cli.py https://www.tiktok.com/@user/video/...")
        print("      python cli.py https://www.douyin.com/video/...")
        sys.exit(1)

    url = sys.argv[1].strip()
    platform = detect_platform(url)

    print("=" * 50)
    print(f"  平台: {platform.value}")
    print(f"  链接: {url}")
    print(f"  无水印: 是")
    print("=" * 50)
    print()

    # 提交下载任务
    task = downloader.submit(url)
    print(f"[任务ID] {task.task_id}")
    print(f"[状态] 正在解析视频信息...")

    # 轮询等待完成
    while True:
        t = downloader.get_task(task.task_id)

        if t.status == 'analyzing':
            if t.title:
                print(f"\n[标题] {t.title}")
                print(f"[作者] {t.author}")
                print(f"[时长] {t.duration}")
                print(f"\n[状态] 开始下载...")
            time.sleep(0.5)

        elif t.status == 'downloading':
            # 进度条
            bar_length = 30
            filled = int(bar_length * t.progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            sys.stdout.write(f"\r[下载] |{bar}| {t.progress:.1f}%  {t.speed}  {t.eta}  {t.file_size_str}")
            sys.stdout.flush()
            time.sleep(0.3)

        elif t.status == 'processing':
            sys.stdout.write(f"\r[处理] 正在合并音视频流...                    ")
            sys.stdout.flush()
            time.sleep(0.5)

        elif t.status == 'completed':
            print(f"\n\n[完成] 下载成功!")
            print(f"[文件] {t.file_path}")
            print(f"[大小] {t.file_size_str}")
            break

        elif t.status == 'failed':
            print(f"\n\n[失败] {t.error}")
            sys.exit(1)

        time.sleep(0.1)


if __name__ == '__main__':
    main()
