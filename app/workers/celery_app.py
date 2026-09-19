from celery import Celery
from app.core.config import settings

# When running in eager mode (no real worker), use in-memory transport
# to avoid Redis connection errors on startup
_broker = "memory://" if settings.CELERY_TASK_ALWAYS_EAGER else settings.REDIS_URL
_backend = "cache+memory://" if settings.CELERY_TASK_ALWAYS_EAGER else settings.REDIS_URL

celery_app = Celery(
    "document_intelligence_worker",
    broker=_broker,
    backend=_backend,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=0,
)

