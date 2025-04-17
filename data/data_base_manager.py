import pymysql
import json
from datetime import datetime
import pytz
from typing import Optional, Dict, Any

class DatabaseManager:
    def __init__(self):
        self.db_config = {
            "host": "dbconn.sealosbja.site",
            "port": 41065,
            "user": "root",
            "password": "rkstc95t",
            "database": "ai-mcn",
            "charset": 'utf8mb4',
            "cursorclass": pymysql.cursors.DictCursor  # 使用字典游标
        }

    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.db_config)

    def get_ready_tasks(self):
        """获取所有待处理的任务及其配置"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT t.*, c.*
                    FROM video_tasks t
                    JOIN video_task_configs c ON t.config_id = c.id
                    WHERE t.status = 'ready'
                    ORDER BY t.created_at ASC
                """)
                return cursor.fetchall()
        finally:
            conn.close()

    def update_task_status(self, task_id: str, status: str, progress: Optional[int] = None,
                      error_message: Optional[str] = None, result_path: Optional[str] = None, minio_path: Optional[str] = None) -> None:
        """更新任务状态"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                update_fields = ["status = %s", "updated_at = %s"]  # 添加 updated_at 字段
                china_tz = pytz.timezone('Asia/Shanghai')
                params = [status,datetime.now(china_tz)]
                
                if progress is not None:
                    update_fields.append("progress = %s")
                    params.append(progress)
                
                if error_message is not None:
                    update_fields.append("error_message = %s")
                    params.append(error_message)
                    
                if result_path is not None:
                    update_fields.append("result_path = %s")
                    params.append(result_path)
                if minio_path is not None:      
                    update_fields.append("minio_path = %s")
                    params.append(minio_path)
                    
                
                # china_tz = pytz.timezone('Asia/Shanghai')
                # params.append(datetime.now(china_tz))  # 添加 updated_at 的值
                params.append(task_id)
                
                query = f"""
                    UPDATE video_tasks 
                    SET {', '.join(update_fields)} 
                    WHERE task_id = %s
                """
                cursor.execute(query, params)
                conn.commit()
        finally:
            conn.close()

    def get_all_tasks(self):
        """获取所有任务的列表"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT t.*, c.*
                    FROM video_tasks t
                    JOIN video_task_configs c ON t.config_id = c.id
                    ORDER BY t.created_at DESC
                """)
                return cursor.fetchall()
        finally:
            conn.close()

    def get_task_config(self, config_id):
        """获取任务配置"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM video_task_configs WHERE id = %s", (config_id,))
                return cursor.fetchone()
        finally:
            conn.close()

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据task_id获取任务"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT t.*, c.*, 
                           COALESCE(v1.audio_voice, v2.audio_voice) as audio_voice,
                           COALESCE(v1.audio_style, v2.audio_style) as audio_style,
                           COALESCE(v1.background_music, v2.background_music) as background_music,
                           COALESCE(v1.enable_background_music, v2.enable_background_music) as enable_background_music,
                           COALESCE(v1.background_music_volume, v2.background_music_volume) as background_music_volume,
                           COALESCE(v1.video_segment_min_length, v2.video_segment_min_length) as video_segment_min_length,
                           COALESCE(v1.video_segment_max_length, v2.video_segment_max_length) as video_segment_max_length,
                           COALESCE(v1.reference_id, v2.reference_id) as reference_id
                    FROM video_tasks t
                    LEFT JOIN video_task_configs c ON t.config_id = c.id
                    LEFT JOIN voice_configs v1 ON t.koc_name = v1.koc_name
                    LEFT JOIN voice_configs v2 ON v2.koc_name = 'default' AND v1.koc_name IS NULL
                    WHERE t.task_id = %s
                """, (task_id,))
                task = cursor.fetchone()
                
                if task:
                    # 清理字段名，移除表前缀
                    cleaned_task = {}
                    for key, value in task.items():
                        clean_key = key.split('.')[-1]
                        cleaned_task[clean_key] = value
                    
                    return cleaned_task
                return None
        finally:
            conn.close()

    def get_failed_tasks(self, max_retry_count=3):
        """获取状态为失败且重试次数小于指定值的任务"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT t.*, c.*
                    FROM video_tasks t
                    JOIN video_task_configs c ON t.config_id = c.id
                    WHERE t.status = 'FAILURE' AND (t.retry_count IS NULL OR t.retry_count < %s)
                    ORDER BY t.updated_at ASC
                """, (max_retry_count,))
                return cursor.fetchall()
        finally:
            conn.close()

    def increment_retry_count(self, task_id):
        """增加任务的重试计数"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 先检查是否存在retry_count字段
                cursor.execute("""
                    UPDATE video_tasks 
                    SET retry_count = IFNULL(retry_count, 0) + 1,
                        updated_at = %s
                    WHERE task_id = %s
                """, (datetime.now(), task_id))
                conn.commit()
        finally:
            conn.close()

    def get_filtered_tasks(self, page=1, page_size=20, config_name=None, batch_id=None, start_date=None, end_date=None):
        """获取筛选后的任务列表，支持分页"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 构建WHERE子句
                where_clauses = []
                params = []
                
                if config_name:
                    where_clauses.append("c.config_name LIKE %s")
                    params.append(f"%{config_name}%")
                
                if batch_id:
                    where_clauses.append("t.batch_id = %s")
                    params.append(batch_id)
                
                if start_date:
                    where_clauses.append("t.created_at >= %s")
                    params.append(start_date)
                
                if end_date:
                    where_clauses.append("t.created_at <= %s")
                    params.append(end_date)
                
                # 构建完整的WHERE子句
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # 获取总记录数
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM video_tasks t
                    JOIN video_task_configs c ON t.config_id = c.id
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                offset = (page - 1) * page_size
                query = f"""
                    SELECT t.*, c.*
                    FROM video_tasks t
                    JOIN video_task_configs c ON t.config_id = c.id
                    WHERE {where_clause}
                    ORDER BY t.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, params + [page_size, offset])
                tasks = cursor.fetchall()
                
                return {
                    'tasks': tasks,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size
                }
        finally:
            conn.close()

    def get_config_names(self):
        """获取所有配置名称列表"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT config_name FROM video_task_configs ORDER BY config_name")
                return [row['config_name'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_batch_ids(self):
        """获取所有批次ID列表"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT batch_id FROM video_tasks WHERE batch_id IS NOT NULL ORDER BY batch_id")
                return [row['batch_id'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_filtered_success_tasks(self, config_name=None, batch_id=None, start_date=None, end_date=None):
        """获取所有符合筛选条件的成功任务"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 构建WHERE子句
                where_clauses = ["t.status = 'SUCCESS'"]  # 只获取成功的任务
                params = []
                
                if config_name:
                    where_clauses.append("c.config_name LIKE %s")
                    params.append(f"%{config_name}%")
                
                if batch_id:
                    where_clauses.append("t.batch_id = %s")
                    params.append(batch_id)
                
                if start_date:
                    where_clauses.append("t.created_at >= %s")
                    params.append(start_date)
                
                if end_date:
                    where_clauses.append("t.created_at <= %s")
                    params.append(end_date)
                
                # 构建完整的WHERE子句
                where_clause = " AND ".join(where_clauses)
                
                # 获取所有符合条件的任务
                query = f"""
                    SELECT t.task_id
                    FROM video_tasks t
                    JOIN video_task_configs c ON t.config_id = c.id
                    WHERE {where_clause}
                    ORDER BY t.created_at DESC
                """
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            conn.close()

    def update_task_tags(self, task_id: str, tags: str, tag_name: str) -> None:
        """
        更新任务标签
        Args:
            task_id: 任务ID
            tags: 标签名称（现在直接使用tag_name）
            tag_name: 标签名称
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                update_fields = ["tags = %s", "updated_at = %s"]
                china_tz = pytz.timezone('Asia/Shanghai')
                params = [tags, datetime.now(china_tz), task_id]
                
                query = f"""
                    UPDATE video_tasks 
                    SET {', '.join(update_fields)} 
                    WHERE task_id = %s
                """
                cursor.execute(query, params)
                conn.commit()
                print(f"已更新任务 {task_id} 的标签: {tag_name}")
        except Exception as e:
            print(f"更新标签失败: {str(e)}")
        finally:
            conn.close()