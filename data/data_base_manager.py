import pymysql
import json
from datetime import datetime
import pytz
from typing import Optional, Dict, Any, List

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
        # 定义可用的任务表
        self.task_tables = ["video_tasks", "video_tasks_lixiang"]
        self.default_table = "video_tasks"

    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.db_config)

    def validate_table_name(self, table_name: str) -> str:
        """验证表名并返回有效的表名"""
        if table_name in self.task_tables:
            return table_name
        return self.default_table

    def get_ready_tasks(self, table_name: str = None):
        """获取所有待处理的任务及其配置"""
        conn = self.get_connection()
        if table_name is None:
            # 如果不指定表，从所有表中获取任务
            all_tasks = []
            for table in self.task_tables:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(f"""
                            SELECT t.*, c.*, '{table}' as source_table
                            FROM {table} t
                            JOIN video_task_configs c ON t.config_id = c.id
                            WHERE t.status = 'ready'
                            ORDER BY t.created_at ASC
                        """)
                        tasks = cursor.fetchall()
                        all_tasks.extend(tasks)
                except Exception as e:
                    print(f"从表 {table} 获取任务时出错: {str(e)}")
            return all_tasks
        else:
            # 使用指定的表
            table = self.validate_table_name(table_name)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT t.*, c.*, '{table}' as source_table
                        FROM {table} t
                        JOIN video_task_configs c ON t.config_id = c.id
                        WHERE t.status = 'ready'
                        ORDER BY t.created_at ASC
                    """)
                    return cursor.fetchall()
            finally:
                conn.close()

    def update_task_status(self, task_id: str, status: str, table_name: str = None, progress: Optional[int] = None,
                      error_message: Optional[str] = None, result_path: Optional[str] = None, minio_path: Optional[str] = None) -> None:
        """更新任务状态"""
        conn = self.get_connection()
        try:
            # 如果未指定表名，尝试确定任务所在的表
            if table_name is None:
                table_name = self.detect_task_table(task_id)
            
            table = self.validate_table_name(table_name)
            
            with conn.cursor() as cursor:
                update_fields = ["status = %s", "updated_at = %s"]  # 添加 updated_at 字段
                china_tz = pytz.timezone('Asia/Shanghai')
                params = [status, datetime.now(china_tz)]
                
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
                
                params.append(task_id)
                
                query = f"""
                    UPDATE {table} 
                    SET {', '.join(update_fields)} 
                    WHERE task_id = %s
                """
                cursor.execute(query, params)
                conn.commit()
        finally:
            conn.close()

    def get_all_tasks(self, table_name: str = None):
        """获取所有任务的列表"""
        conn = self.get_connection()
        try:
            if table_name is None:
                # 如果不指定表，从所有表中获取任务
                all_tasks = []
                for table in self.task_tables:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(f"""
                                SELECT t.*, c.*, '{table}' as source_table
                                FROM {table} t
                                JOIN video_task_configs c ON t.config_id = c.id
                                ORDER BY t.created_at DESC
                            """)
                            tasks = cursor.fetchall()
                            all_tasks.extend(tasks)
                    except Exception as e:
                        print(f"从表 {table} 获取任务时出错: {str(e)}")
                return all_tasks
            else:
                # 使用指定的表
                table = self.validate_table_name(table_name)
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT t.*, c.*, '{table}' as source_table
                        FROM {table} t
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

    def get_task_by_id(self, task_id: str, table_name: str = None) -> Optional[Dict[str, Any]]:
        """根据task_id获取任务"""
        conn = self.get_connection()
        try:
            # 如果未指定表名，尝试确定任务所在的表
            if table_name is None:
                table_name = self.detect_task_table(task_id)
            
            table = self.validate_table_name(table_name)
            
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT t.*, c.*, '{table}' as source_table,
                           COALESCE(v1.audio_voice, v2.audio_voice) as audio_voice,
                           COALESCE(v1.audio_style, v2.audio_style) as audio_style,
                           COALESCE(v1.background_music, v2.background_music) as background_music,
                           COALESCE(v1.enable_background_music, v2.enable_background_music) as enable_background_music,
                           COALESCE(v1.background_music_volume, v2.background_music_volume) as background_music_volume,
                           COALESCE(v1.video_segment_min_length, v2.video_segment_min_length) as video_segment_min_length,
                           COALESCE(v1.video_segment_max_length, v2.video_segment_max_length) as video_segment_max_length,
                           COALESCE(v1.reference_id, v2.reference_id) as reference_id
                    FROM {table} t
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
                
                # 如果在指定表中没找到，且用户没有明确指定表名，尝试在其他表中查找
                if table_name is None:
                    for other_table in [t for t in self.task_tables if t != table]:
                        cursor.execute(f"""
                            SELECT t.*, c.*, '{other_table}' as source_table,
                                   COALESCE(v1.audio_voice, v2.audio_voice) as audio_voice,
                                   COALESCE(v1.audio_style, v2.audio_style) as audio_style,
                                   COALESCE(v1.background_music, v2.background_music) as background_music,
                                   COALESCE(v1.enable_background_music, v2.enable_background_music) as enable_background_music,
                                   COALESCE(v1.background_music_volume, v2.background_music_volume) as background_music_volume,
                                   COALESCE(v1.video_segment_min_length, v2.video_segment_min_length) as video_segment_min_length,
                                   COALESCE(v1.video_segment_max_length, v2.video_segment_max_length) as video_segment_max_length,
                                   COALESCE(v1.reference_id, v2.reference_id) as reference_id
                            FROM {other_table} t
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

    def get_failed_tasks(self, max_retry_count=3, table_name: str = None):
        """获取状态为失败且重试次数小于指定值的任务"""
        conn = self.get_connection()
        try:
            if table_name is None:
                # 如果不指定表，从所有表中获取任务
                all_tasks = []
                for table in self.task_tables:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(f"""
                                SELECT t.*, c.*, '{table}' as source_table
                                FROM {table} t
                                JOIN video_task_configs c ON t.config_id = c.id
                                WHERE t.status = 'FAILURE' AND (t.retry_count IS NULL OR t.retry_count < %s)
                                ORDER BY t.updated_at ASC
                            """, (max_retry_count,))
                            tasks = cursor.fetchall()
                            all_tasks.extend(tasks)
                    except Exception as e:
                        print(f"从表 {table} 获取失败任务时出错: {str(e)}")
                return all_tasks
            else:
                # 使用指定的表
                table = self.validate_table_name(table_name)
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT t.*, c.*, '{table}' as source_table
                        FROM {table} t
                        JOIN video_task_configs c ON t.config_id = c.id
                        WHERE t.status = 'FAILURE' AND (t.retry_count IS NULL OR t.retry_count < %s)
                        ORDER BY t.updated_at ASC
                    """, (max_retry_count,))
                    return cursor.fetchall()
        finally:
            conn.close()

    def increment_retry_count(self, task_id, table_name: str = None):
        """增加任务的重试计数"""
        conn = self.get_connection()
        try:
            # 如果未指定表名，尝试确定任务所在的表
            if table_name is None:
                table_name = self.detect_task_table(task_id)
            
            table = self.validate_table_name(table_name)
            
            with conn.cursor() as cursor:
                # 先检查是否存在retry_count字段
                cursor.execute(f"""
                    UPDATE {table} 
                    SET retry_count = IFNULL(retry_count, 0) + 1,
                        updated_at = %s
                    WHERE task_id = %s
                """, (datetime.now(), task_id))
                conn.commit()
        finally:
            conn.close()

    def get_filtered_tasks(self, page=1, page_size=20, table_name: str = None, config_name=None, batch_id=None, start_date=None, end_date=None):
        """获取筛选后的任务列表，支持分页"""
        conn = self.get_connection()
        try:
            # 如果指定了表名，只查询该表
            if table_name:
                table = self.validate_table_name(table_name)
                return self._get_filtered_tasks_from_table(
                    conn, table, page, page_size, config_name, batch_id, start_date, end_date
                )
            
            # 否则，从所有表中获取并合并结果
            all_tasks = []
            total_count = 0
            
            for table in self.task_tables:
                try:
                    result = self._get_filtered_tasks_from_table(
                        conn, table, 1, 10000, config_name, batch_id, start_date, end_date
                    )
                    all_tasks.extend(result['tasks'])
                    total_count += result['total']
                except Exception as e:
                    print(f"从表 {table} 获取筛选任务时出错: {str(e)}")
            
            # 在内存中进行排序和分页
            all_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 计算分页
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_tasks = all_tasks[start_idx:end_idx] if start_idx < len(all_tasks) else []
            
            return {
                'tasks': paginated_tasks,
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        finally:
            conn.close()

    def _get_filtered_tasks_from_table(self, conn, table, page, page_size, config_name, batch_id, start_date, end_date):
        """从特定表中获取筛选后的任务"""
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
                FROM {table} t
                JOIN video_task_configs c ON t.config_id = c.id
                WHERE {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # 获取分页数据
            offset = (page - 1) * page_size
            query = f"""
                SELECT t.*, c.*, '{table}' as source_table
                FROM {table} t
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

    def get_config_names(self):
        """获取所有配置名称列表"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT config_name FROM video_task_configs ORDER BY config_name")
                return [row['config_name'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_batch_ids(self, table_name: str = None):
        """获取所有批次ID列表"""
        conn = self.get_connection()
        try:
            if table_name is None:
                # 如果不指定表，从所有表中获取批次ID
                all_batch_ids = set()
                for table in self.task_tables:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(f"SELECT DISTINCT batch_id FROM {table} WHERE batch_id IS NOT NULL ORDER BY batch_id")
                            batch_ids = [row['batch_id'] for row in cursor.fetchall()]
                            all_batch_ids.update(batch_ids)
                    except Exception as e:
                        print(f"从表 {table} 获取批次ID时出错: {str(e)}")
                return sorted(list(all_batch_ids))
            else:
                # 使用指定的表
                table = self.validate_table_name(table_name)
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT DISTINCT batch_id FROM {table} WHERE batch_id IS NOT NULL ORDER BY batch_id")
                    return [row['batch_id'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_filtered_success_tasks(self, table_name: str = None, config_name=None, batch_id=None, start_date=None, end_date=None):
        """获取所有符合筛选条件的成功任务"""
        conn = self.get_connection()
        try:
            if table_name is None:
                # 如果不指定表，从所有表中获取任务
                all_tasks = []
                for table in self.task_tables:
                    try:
                        tasks = self._get_filtered_success_tasks_from_table(
                            conn, table, config_name, batch_id, start_date, end_date
                        )
                        all_tasks.extend(tasks)
                    except Exception as e:
                        print(f"从表 {table} 获取成功任务时出错: {str(e)}")
                return all_tasks
            else:
                # 使用指定的表
                table = self.validate_table_name(table_name)
                return self._get_filtered_success_tasks_from_table(
                    conn, table, config_name, batch_id, start_date, end_date
                )
        finally:
            conn.close()
    
    def _get_filtered_success_tasks_from_table(self, conn, table, config_name, batch_id, start_date, end_date):
        """从特定表中获取符合筛选条件的成功任务"""
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
                SELECT t.task_id, '{table}' as source_table
                FROM {table} t
                JOIN video_task_configs c ON t.config_id = c.id
                WHERE {where_clause}
                ORDER BY t.created_at DESC
            """
            cursor.execute(query, params)
            return cursor.fetchall()

    def update_task_tags(self, task_id: str, tags: str, tag_name: str, table_name: str = None) -> None:
        """
        更新任务标签
        Args:
            task_id: 任务ID
            tags: 标签名称（现在直接使用tag_name）
            tag_name: 标签名称
            table_name: 表名
        """
        conn = self.get_connection()
        try:
            # 如果未指定表名，尝试确定任务所在的表
            if table_name is None:
                table_name = self.detect_task_table(task_id)
            
            table = self.validate_table_name(table_name)
            
            with conn.cursor() as cursor:
                update_fields = ["tags = %s", "updated_at = %s"]
                china_tz = pytz.timezone('Asia/Shanghai')
                params = [tags, datetime.now(china_tz), task_id]
                
                query = f"""
                    UPDATE {table} 
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

    def detect_task_table(self, task_id: str) -> str:
        """
        根据任务ID检测任务所在的表
        Args:
            task_id: 任务ID
        Returns:
            表名
        """
        conn = self.get_connection()
        try:
            # 依次在各个任务表中查找
            for table in self.task_tables:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table} WHERE task_id = %s", (task_id,))
                    result = cursor.fetchone()
                    if result and result['count'] > 0:
                        return table
            # 默认返回第一个表
            return self.default_table
        finally:
            conn.close()