"""Hang doi ben vung cho phan tich CV.

- Neu co REDIS_URL: day payload vao Redis list, worker tieu thu qua BLPOP.
- Neu khong: giu BackgroundTasks hien tai + worker poll DB dinh ky (15s)
  de nhat CV uploaded con sot (vi du sau khi backend restart).
- Khoa theo file_hash co ban Redis (SET NX) khi chay nhieu worker,
  fallback ve Lock bo nho tien trinh.
"""
import json
import logging
import threading
import time
from contextlib import contextmanager
from threading import Lock

logger = logging.getLogger(__name__)

QUEUE_KEY = "cv_analysis_queue"
HASH_LOCK_PREFIX = "cv_analysis_hash_lock:"
HASH_LOCK_TTL = 600

_memory_locks: dict[str, Lock] = {}
_memory_locks_guard = Lock()


def _settings():
    from app.core.config import settings
    return settings


def _redis_client():
    try:
        url = (_settings().REDIS_URL or "").strip()
        if not url:
            return None
        import redis
        return redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=5)
    except Exception:
        return None


def queue_cv_analysis(background_tasks, cv_id: int, file_path: str, run_id: str | None) -> str:
    """Day viec phan tich vao hang doi; tra ve 'redis' hoac 'local'."""
    try:
        client = _redis_client()
        if client is not None:
            payload = json.dumps({"cv_id": cv_id, "file_path": file_path, "run_id": run_id})
            client.rpush(QUEUE_KEY, payload)
            return "redis"
    except Exception as exc:
        logger.warning("Day viec CV %s vao Redis that bai, dung local: %s", cv_id, exc)
    from app.api.cv import process_cv_analysis
    background_tasks.add_task(process_cv_analysis, cv_id, file_path, run_id)
    return "local"


def _get_analysis_lock(file_hash: str) -> Lock:
    """Tra ve lock bo nho dung chung theo hash (tuong thich test cu)."""
    with _memory_locks_guard:
        return _memory_locks.setdefault(file_hash, Lock())


@contextmanager
def hash_lock(file_hash: str | None):
    """Khoa theo hash file; Redis SET NX khi co the, fallback Lock bo nho."""
    if not file_hash:
        yield
        return
    client = _redis_client()
    if client is None:
        lock = _get_analysis_lock(file_hash)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
        return
    key = HASH_LOCK_PREFIX + file_hash
    try:
        acquired = client.set(key, "1", nx=True, ex=HASH_LOCK_TTL)
    except Exception:
        acquired = False
    if not acquired:
        # Co worker khac dang xu ly cung noi dung; bo qua lan nay.
        yield
        return
    try:
        yield
    finally:
        try:
            client.delete(key)
        except Exception:
            pass


def _process_payload(cv_id: int, file_path: str, run_id: str | None) -> None:
    from app.api.cv import process_cv_analysis
    process_cv_analysis(cv_id, file_path, run_id)


def _poll_db_once(limit: int = 5) -> int:
    from app.core.database import SessionLocal
    from app.models.cv import CV
    db = SessionLocal()
    try:
        rows = (
            db.query(CV.id, CV.file_path, CV.analysis_run_id)
            .filter(CV.status == "uploaded")
            .order_by(CV.updated_at.asc(), CV.id.asc())
            .limit(limit)
            .all()
        )
        ids = [(r[0], r[1], r[2]) for r in rows]
    finally:
        db.close()
    for cv_id, file_path, run_id in ids:
        try:
            _process_payload(cv_id, file_path, run_id)
        except Exception as exc:
            logger.exception("Worker xu ly CV %s loi: %s", cv_id, exc)
    return len(ids)


def _redis_worker_loop(poll_interval: int = 15) -> None:
    client = _redis_client()
    if client is None:
        return
    while True:
        try:
            item = client.blpop(QUEUE_KEY, timeout=poll_interval)
        except Exception as exc:
            # BLPOP het han (socket_timeout < poll_interval) la binh thuong:
            # coi nhu khong co viec, poll DB roi cho tiep.
            if "timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower():
                _poll_db_once()
                continue
            logger.exception("Redis worker loi: %s", exc)
            time.sleep(poll_interval)
            continue
        try:
            if not item:
                _poll_db_once()
                continue
            payload = json.loads(item[1])
            _process_payload(payload["cv_id"], payload.get("file_path", ""), payload.get("run_id"))
        except Exception as exc:
            logger.exception("Redis worker loi: %s", exc)
            time.sleep(poll_interval)


def _db_worker_loop(poll_interval: int = 15) -> None:
    while True:
        try:
            _poll_db_once()
        except Exception as exc:
            logger.exception("DB worker loi: %s", exc)
        time.sleep(poll_interval)


_worker_started = False
_worker_guard = Lock()


def start_analysis_worker() -> bool:
    """Khoi dong worker nen (idempotent); chi goi mot lan khi startup."""
    global _worker_started
    with _worker_guard:
        if _worker_started:
            return False
        _worker_started = True
    use_redis = bool((_settings().REDIS_URL or "").strip())
    target = _redis_worker_loop if use_redis else _db_worker_loop
    thread = threading.Thread(target=target, name="cv-analysis-worker", daemon=True)
    thread.start()
    logger.info("Da khoi dong CV analysis worker (backend=%s)", "redis" if use_redis else "db-poll")
    return True
