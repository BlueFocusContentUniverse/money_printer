#!/bin/bash

# 停止Celery Worker
if [ -f celery.pid ]; then
    kill $(cat celery.pid)
    rm celery.pid
fi

# 停止Redis
redis-cli -p 6381 shutdown