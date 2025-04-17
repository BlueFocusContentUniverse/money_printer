import os
from kombu import Exchange, Queue
from celery.schedules import crontab

# Redis连接配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6381))
REDIS_PASSWORD = "Bfg@usr" 
REDIS_DB_BROKER = 0
REDIS_DB_BACKEND = 1

# Broker设置
broker_url = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BROKER}'
result_backend = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BACKEND}'

# 序列化设置
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
result_accept_content = ['json']
# 时区设置
timezone = 'Asia/Shanghai'
enable_utc = True

# 任务设置
task_track_started = True
task_time_limit = 3600  # 1小时超时
task_soft_time_limit = 3300  # 55分钟软超时
task_acks_late = True  # 任务执行完成后再确认

# Worker设置
worker_max_tasks_per_child = 50  # 处理50个任务后重启worker
worker_prefetch_multiplier = 2  # 限制worker预取任务数
worker_concurrency = int(os.getenv('CELERY_WORKERS', 3))  # worker进程数

# 定义Exchange
default_exchange = Exchange('default', type='direct')
high_priority_exchange = Exchange('high_priority', type='direct')
low_priority_exchange = Exchange('low_priority', type='direct')

# 任务队列设置
task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('high_priority', high_priority_exchange, routing_key='high_priority'),
    Queue('low_priority', low_priority_exchange, routing_key='low_priority'),
)

# 任务路由设置
task_routes = {
    'worker.celery.generate_video_task': {'queue': 'high_priority'},
    'worker.celery.cleanup_task': {'queue': 'low_priority'},
    'worker.celery.update_task_record': {'queue': 'high_priority'}
}

# 结果配置
result_expires = 36000  # 结果过期时间(秒)

# 确保结果能够正确序列化
task_reject_on_worker_lost = True
task_acks_late = True

# 日志设置
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'
CELERY_LOGGING = {
    'filename': '/home/jinpeng/MoneyPrinterPlus/moneyprinter3/worker/celery.log',  # 指定日志文件路径
    'level': 'DEBUG'
}
# 错误处理
task_annotations = {
    'worker.celery.update_task_record': {
        'rate_limit': '100/m',  # 状态更新任务可以更频繁
        'max_retries': 3,
        'retry_backoff': True
    },
    '*': {
        'rate_limit': '10/m',  # 全局任务速率限制
        'max_retries': 3,      # 最大重试次数
        'retry_backoff': True  # 重试时间递增
    }
}

# 心跳监控
worker_send_task_events = True

# 添加定时任务配置
beat_schedule = {
    'scan-ready-tasks': {
        'task': 'worker.celery.scan_and_process_ready_tasks',
        'schedule': 30.0,  # 每30秒执行一次
        'options': {
            'queue': 'high_priority'
        }
    },
    'retry-failed-tasks': {
        'task': 'worker.celery.retry_failed_tasks',
        'schedule': 600.0,  # 每10分钟执行一次
        'args': (3,),  # 最大重试3次
        'options': {
            'queue': 'low_priority'  # 使用低优先级队列
        }
    }
}