#!/bin/bash

# 启动Redis(如果没有运行)
redis-server --port 6381 &

# 启动Celery Worker
celery -A worker.celery worker --loglevel=INFO --pool=prefork --concurrency=4 -Q high_priority,default,low_priority &

# 启动Flower监控(可选)
celery -A worker.celery flower --port=5555 &

# 保存进程ID
echo $! > celery.pid