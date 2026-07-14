"""
Redis 任务队列
基于 Redis List 实现简单的 FIFO 队列，支持优先级
"""
import json
import redis
from config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

TASK_QUEUE_KEY = "vd:task_queue"
TASK_STATUS_KEY = "vd:task_status"  # Hash: task_id -> json
TASK_TTL = 86400 * 2  # 2天


def enqueue_task(task_id: str, task_data: dict, priority: int = 0):
    """将任务推入队列"""
    task_json = json.dumps({"task_id": task_id, "data": task_data, "priority": priority})
    # 高优先级任务放前面 (LPUSH)，普通任务放后面 (RPUSH)
    if priority > 0:
        redis_client.lpush(TASK_QUEUE_KEY, task_json)
    else:
        redis_client.rpush(TASK_QUEUE_KEY, task_json)

    # 缓存任务状态
    redis_client.hset(TASK_STATUS_KEY, task_id, json.dumps(task_data))
    redis_client.expire(TASK_STATUS_KEY, TASK_TTL)


def dequeue_task(timeout: int = 5) -> dict | None:
    """从队列取出任务 (阻塞)"""
    result = redis_client.blpop(TASK_QUEUE_KEY, timeout=timeout)
    if result:
        _, task_json = result
        return json.loads(task_json)
    return None


def update_task_progress(task_id: str, progress: float, **extra):
    """更新任务进度 (Redis 缓存，用于实时轮询)"""
    data = {"progress": progress, **extra}
    redis_client.hset(TASK_STATUS_KEY, task_id, json.dumps(data))
    redis_client.expire(TASK_STATUS_KEY, TASK_TTL)


def get_cached_task(task_id: str) -> dict | None:
    """获取缓存的任务状态"""
    data = redis_client.hget(TASK_STATUS_KEY, task_id)
    if data:
        return json.loads(data)
    return None


def remove_cached_task(task_id: str):
    """删除缓存的任务"""
    redis_client.hdel(TASK_STATUS_KEY, task_id)


def get_queue_size() -> int:
    """获取队列长度"""
    return redis_client.llen(TASK_QUEUE_KEY)


def acquire_download_slot(user_id: str) -> bool:
    """检查并发下载数限制 (同一用户最多1个并发任务)"""
    key = f"vd:downloading:{user_id}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 600)  # 10分钟超时
        return True
    redis_client.decr(key)
    return False


def release_download_slot(user_id: str):
    """释放下载槽位"""
    redis_client.delete(f"vd:downloading:{user_id}")
