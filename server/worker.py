"""
后台 Worker 进程
从 Redis 队列消费任务，执行视频下载
可多进程运行提升吞吐量
"""
import os
import sys
import signal
import time
import multiprocessing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.task_queue import dequeue_task
from services.downloader_service import downloader_service
from config import settings


class TaskWorker:
    """任务消费 Worker"""

    def __init__(self, worker_id: int = 0):
        self.worker_id = worker_id
        self.running = True
        self.current_task = None

    def stop(self, *args):
        print(f"[Worker-{self.worker_id}] 正在停止...")
        self.running = False

    def run(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)

        print(f"[Worker-{self.worker_id}] 启动，等待任务...")

        while self.running:
            try:
                # 阻塞等待任务 (5秒超时)
                task = dequeue_task(timeout=5)
                if not task:
                    continue

                task_id = task.get("task_id")
                task_data = task.get("data", {})

                print(f"[Worker-{self.worker_id}] 处理任务: {task_id} ({task_data.get('platform', '?')})")
                self.current_task = task_id

                # 执行下载
                downloader_service.process_task(task_id, task_data)

                print(f"[Worker-{self.worker_id}] 任务完成: {task_id}")
                self.current_task = None

            except Exception as e:
                print(f"[Worker-{self.worker_id}] 任务异常: {e}")
                self.current_task = None
                time.sleep(1)

        print(f"[Worker-{self.worker_id}] 已停止")


def run_worker(worker_id: int):
    w = TaskWorker(worker_id)
    w.run()


if __name__ == "__main__":
    num_workers = int(os.getenv("WORKER_CONCURRENCY", str(settings.MAX_CONCURRENT_DOWNLOADS)))
    print(f"启动 {num_workers} 个 Worker 进程...")

    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=run_worker, args=(i,))
        p.start()
        processes.append(p)

    # 等待所有 worker
    for p in processes:
        p.join()
