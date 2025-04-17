import os
from celery.signals import celeryd_after_setup
from celery.bin import worker
from celery import Celery
from celery.apps.multi import MultiTool

def start_celery():
    """启动Celery Worker"""
    # 设置环境变量
    os.environ.setdefault('CELERY_CONFIG_MODULE', 'worker.celeryconfig')
    
    # 创建Celery实例
    app = Celery('moneyprinter3')
    
    # 从配置文件加载配置
    app.config_from_object('worker.celeryconfig')
    
    # 自动发现任务
    app.autodiscover_tasks(['worker'])
    
    # 启动Worker
    worker = app.Worker(
        concurrency=3,  # worker进程数
        loglevel='INFO',
        pool='prefork',  # 进程池类型
        optimization='fair'  # 任务分配策略
    )
    
    worker.start()

if __name__ == '__main__':
    start_celery()