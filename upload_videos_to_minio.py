#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一次性脚本：将batch_id为2.28、3.1和3.2的任务中的视频上传到MinIO并更新数据库中的公网链接
"""

import os
import logging
import json
from types import SimpleNamespace
from typing import List, Dict, Any, Optional
from data.data_base_manager import DatabaseManager
from data.minio_handler import MinIOHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MinIO配置
MINIO_CONFIG = {
    "minio_config": {
        "endpoint": "objectstorageapi.bja.sealos.run",
        "access_key": "1wpzyo2e",
        "secret_key": "2djs6znwsdmrwqbv",
        "bucket": "1wpzyo2e-ai-mcn",
        "prefix": "final_output_taibao"
    }
}

# 要处理的batch_id列表
TARGET_BATCH_IDS = ["2.28", "3.1", "3.2"]


def get_tasks_by_batch_ids(db_manager: DatabaseManager, batch_ids: List[str]) -> List[Dict[str, Any]]:
    """
    获取指定batch_id的任务列表
    
    Args:
        db_manager: 数据库管理器实例
        batch_ids: 批次ID列表
        
    Returns:
        符合条件的任务列表
    """
    all_tasks = []
    
    for batch_id in batch_ids:
        logger.info(f"获取batch_id为 {batch_id} 的任务...")
        
        # 使用get_filtered_tasks方法获取指定batch_id的任务
        result = db_manager.get_filtered_tasks(
            page=1,
            page_size=1000,  # 设置较大的页面大小以获取所有任务
            batch_id=batch_id
        )
        
        if result and 'tasks' in result:
            tasks = result['tasks']
            logger.info(f"找到 {len(tasks)} 个任务，batch_id={batch_id}")
            all_tasks.extend(tasks)
        else:
            logger.warning(f"未找到batch_id为 {batch_id} 的任务")
    
    return all_tasks


def process_tasks(tasks: List[Dict[str, Any]], db_manager: DatabaseManager, minio_handler: MinIOHandler) -> None:
    """
    处理任务列表：上传视频到MinIO并更新数据库
    
    Args:
        tasks: 任务列表
        db_manager: 数据库管理器实例
        minio_handler: MinIO处理器实例
    """
    total_tasks = len(tasks)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    logger.info(f"开始处理 {total_tasks} 个任务...")
    
    for i, task in enumerate(tasks, 1):
        task_id = task.get('task_id')
        result_path = task.get('result_path')
        minio_path = task.get('minio_path')
        
        logger.info(f"[{i}/{total_tasks}] 处理任务 {task_id}")
        
        # 如果已经有MinIO路径，则跳过
        if minio_path:
            logger.info(f"任务 {task_id} 已有MinIO路径，跳过")
            skipped_count += 1
            continue
        
        # 如果没有结果路径，则跳过
        if not result_path:
            logger.warning(f"任务 {task_id} 没有结果路径，跳过")
            skipped_count += 1
            continue
        
        # 检查文件是否存在
        if not os.path.exists(result_path):
            logger.error(f"任务 {task_id} 的结果文件不存在: {result_path}")
            failed_count += 1
            continue
        
        try:
            # 上传视频到MinIO
            object_path = f"{task_id}/{os.path.basename(result_path)}"
            success, result = minio_handler.upload_file(result_path, object_path)
            
            if not success:
                logger.error(f"上传失败: {result}")
                failed_count += 1
                continue
            
            # 获取公网URL
            success, url = minio_handler.get_public_url(object_path)
            
            if not success:
                logger.error(f"获取公网URL失败: {url}")
                failed_count += 1
                continue
            
            # 更新数据库
            db_manager.update_task_status(
                task_id=task_id,
                status=task.get('status', 'SUCCESS'),  # 保持原状态
                minio_path=url
            )
            
            logger.info(f"成功处理任务 {task_id}, MinIO URL: {url}")
            success_count += 1
            
        except Exception as e:
            logger.exception(f"处理任务 {task_id} 时发生错误: {str(e)}")
            failed_count += 1
    
    logger.info(f"任务处理完成: 总计 {total_tasks}, 成功 {success_count}, 失败 {failed_count}, 跳过 {skipped_count}")


def main():
    """主函数"""
    logger.info("开始执行视频上传脚本...")
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager()
        logger.info("数据库管理器初始化成功")
        
        # 初始化MinIO处理器
        config = json.loads(json.dumps(MINIO_CONFIG), object_hook=lambda d: SimpleNamespace(**d))
        minio_handler = MinIOHandler(config)
        logger.info("MinIO处理器初始化成功")
        
        # 获取指定batch_id的任务
        tasks = get_tasks_by_batch_ids(db_manager, TARGET_BATCH_IDS)
        
        if not tasks:
            logger.warning("未找到符合条件的任务，脚本结束")
            return
        
        # 处理任务
        process_tasks(tasks, db_manager, minio_handler)
        
    except Exception as e:
        logger.exception(f"脚本执行过程中发生错误: {str(e)}")
    
    logger.info("脚本执行完成")


if __name__ == "__main__":
    main() 