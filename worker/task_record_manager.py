import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from data.data_base_manager import DatabaseManager

class TaskRecordManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def update_task_status(self, task_id: str, data: Dict[str, Any]) -> None:
        """更新任务状态到数据库"""
        # 准备更新数据
        current_time = datetime.now().isoformat()
        result = data.get('result', {})
        
        # 如果result是字符串（例如文件路径），直接使用，不进行JSON序列化
        if isinstance(result, str):
            result_str = result
        else:
            result_str = json.dumps(result)
            
        # 更新数据库
        self.db_manager.update_task_status(
            task_id=task_id,
            status=data.get('status', 'PENDING'),
            progress=data.get('progress', 0),
            error_message=data.get('message', ''),
            result_path=result_str
        )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取任务状态"""
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM video_tasks 
                    WHERE task_id = %s
                """, (task_id,))
                task = cursor.fetchone()
                
                if task:
                    # 处理result字段
                    try:
                        if task['result_path'] and (
                            task['result_path'].startswith('{') or 
                            task['result_path'].startswith('[')
                        ):
                            task['result'] = json.loads(task['result_path'])
                        else:
                            task['result'] = task['result_path']
                    except json.JSONDecodeError:
                        task['result'] = task['result_path']
                    
                    return task
                return None
        finally:
            conn.close()

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务记录"""
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM video_tasks ORDER BY created_at DESC")
                tasks = cursor.fetchall()
                
                # 处理每个任务的result字段
                for task in tasks:
                    try:
                        if task['result_path'] and (
                            task['result_path'].startswith('{') or 
                            task['result_path'].startswith('[')
                        ):
                            task['result'] = json.loads(task['result_path'])
                        else:
                            task['result'] = task['result_path']
                    except json.JSONDecodeError:
                        task['result'] = task['result_path']
                
                return tasks
        finally:
            conn.close()

    def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有任务"""
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM video_tasks 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC
                """, (user_id,))
                tasks = cursor.fetchall()
                
                # 处理每个任务的result字段
                for task in tasks:
                    try:
                        if task['result_path'] and (
                            task['result_path'].startswith('{') or 
                            task['result_path'].startswith('[')
                        ):
                            task['result'] = json.loads(task['result_path'])
                        else:
                            task['result'] = task['result_path']
                    except json.JSONDecodeError:
                        task['result'] = task['result_path']
                
                return tasks
        finally:
            conn.close()

    def get_success_tasks(self) -> List[Dict[str, Any]]:
        """获取所有成功的任务"""
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM video_tasks 
                    WHERE status = 'SUCCESS' 
                    ORDER BY created_at DESC
                """)
                tasks = cursor.fetchall()
                
                # 处理每个任务的result字段
                for task in tasks:
                    try:
                        if task['result_path'] and (
                            task['result_path'].startswith('{') or 
                            task['result_path'].startswith('[')
                        ):
                            task['result'] = json.loads(task['result_path'])
                        else:
                            task['result'] = task['result_path']
                    except json.JSONDecodeError:
                        task['result'] = task['result_path']
                
                return tasks
        finally:
            conn.close()

    def delete_task(self, task_id: str) -> bool:
        """删除指定任务"""
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM video_tasks 
                    WHERE task_id = %s
                """, (task_id,))
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()