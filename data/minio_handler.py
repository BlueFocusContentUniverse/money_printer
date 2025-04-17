# handlers/minio_handler.py
from minio import Minio
from minio.error import S3Error
import os
import logging
from typing import Optional, Tuple, BinaryIO
from datetime import timedelta

class MinIOHandler:
    """处理与 MinIO 的交互"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.prefix = config.minio_config.prefix
        self.bucket = config.minio_config.bucket

        
        # 初始化 MinIO 客户端
        self.client = Minio(
            endpoint=config.minio_config.endpoint,
            access_key=config.minio_config.access_key,
            secret_key=config.minio_config.secret_key,
            secure=True
        )
        
        # 确保 bucket 存在
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """确保存储桶存在"""
        try:
            # 修复：使用点表示法
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"创建存储桶: {self.bucket}")
        except S3Error as e:
            self.logger.error(f"存储桶操作失败: {str(e)}")
            raise

    def _get_full_path(self, object_path: str) -> str:
        """
        获取完整的对象路径
        
        Args:
            object_path: 相对路径
            
        Returns:
            完整的对象路径
        """
        # 清理路径中的多余斜杠和开头的斜杠
        clean_path = object_path.strip('/')
        if self.prefix:
            return f"{self.prefix}/{clean_path}"
        return clean_path
    
    def upload_file(self, file_path: str, object_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        上传文件到 MinIO
        
        Args:
            file_path: 本地文件路径
            object_path: MinIO 中的对象路径（可选，相对于 prefix）
            
        Returns:
            (success, message)
        """
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在"
                
            # 如果没有指定对象路径，使用文件名
            if object_path is None:
                object_path = os.path.basename(file_path)
                
            # 获取完整路径
            full_path = self._get_full_path(object_path)
            
            # 上传文件
            result = self.client.fput_object(
                bucket_name=self.bucket,
                object_name=full_path,
                file_path=file_path,
                content_type='video/mp4'
            )
            
            return True, str(result.object_name)
            
        except S3Error as e:
            error_msg = f"上传失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def download_file(self, object_path: str, file_path: str) -> Tuple[bool, str]:
        """
        从 MinIO 下载文件
        
        Args:
            object_name: MinIO 中的对象名称
            file_path: 本地保存路径
            
        Returns:
            (success, message)
        """
        try:
            full_path = self._get_full_path(object_path)

            self.client.fget_object(
                bucket_name=self.bucket,
                object_name=full_path,
                file_path=file_path
            )
            return True, file_path
            
        except S3Error as e:
            error_msg = f"下载失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_public_url(self, object_path: str) -> Tuple[bool, str]:
        """
        获取对象的公网访问 URL
        """
        try:
            full_path = self._get_full_path(object_path)
            # 直接拼接公网访问地址
            url = f"https://{self.config.minio_config.endpoint}/{self.bucket}/{full_path}"
            return True, url
        except Exception as e:
            error_msg = f"获取公网访问 URL 失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg


    def delete_file(self, object_path: str) -> Tuple[bool, str]:
        """
        删除 MinIO 中的文件
        
        Args:
            object_path: 要删除的对象路径（相对于 prefix）
            
        Returns:
            (success, message)
        """
        try:
            full_path = self._get_full_path(object_path)
            
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=full_path
            )
            return True, f"成功删除 {full_path}"
            
        except S3Error as e:
            error_msg = f"删除失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg


    def list_files(self, prefix: str = "") -> Tuple[bool, list]:
        """
        列出 MinIO 中的文件
        
        Args:
            prefix: 额外的路径前缀（可选，相对于基础 prefix）
            
        Returns:
            (success, file_list/error_message)
        """
        try:
            full_prefix = self._get_full_path(prefix)
            
            objects = self.client.list_objects(
                bucket_name=self.bucket,
                prefix=full_prefix
            )
            
            # 移除基础前缀，返回相对路径
            file_list = [obj.object_name for obj in objects]
            return True, file_list
            
        except S3Error as e:
            error_msg = f"列举文件失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def upload_video_and_get_url(
        self, 
        video_path: str, 
        object_path: Optional[str] = None, 
        expires: timedelta = timedelta(hours=1)
    ) -> Tuple[bool, dict]:
        """
        上传视频并获取临时访问链接
        
        Args:
            video_path: 本地视频文件路径
            object_path: MinIO 中的存储路径（可选）
            expires: 链接有效期（默认 1小时）
            
        Returns:
            Tuple[bool, dict]: (成功状态, 结果字典)
            结果字典包含：
            - success 时: {"url": "访问链接", "object_path": "存储路径"}
            - failure 时: {"error": "错误信息"}
        """
        try:
            # 1. 上传视频
            upload_result = self.upload_file(video_path, object_path)
            if not upload_result:
                return False, {"error": "视频上传失败"}
                
            # 获取实际的存储路径
            actual_object_path = object_path if object_path else os.path.basename(video_path)
            
            # 2. 获取访问链接
            success, url_result = self.get_public_url(actual_object_path)
            if not success:
                return False, {"error": f"获取访问链接失败: {url_result}"}
                
            return True, {
                "url": url_result,
                "object_path": actual_object_path
            }
            
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            self.logger.error(error_msg)
            return False, {"error": error_msg}
        


if __name__ == "__main__":
    import argparse
    import tempfile
    import json
    from types import SimpleNamespace
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='测试MinIO处理器功能')
    parser.add_argument('--config', type=str, help='MinIO配置文件路径')
    args = parser.parse_args()
    
    # 配置信息
    if args.config:
        # 从配置文件加载
        with open(args.config, 'r') as f:
            config_dict = json.load(f)
    else:
        # 使用默认配置（需要修改为有效的配置）
        config_dict = {
            "minio_config": {
                "endpoint": "objectstorageapi.bja.sealos.run",
                "access_key": "1wpzyo2e",
                "secret_key": "2djs6znwsdmrwqbv",
                "bucket": "1wpzyo2e-ai-mcn",
                "prefix": "final_output_taibao"
            }
        }
    
    # 将字典转换为对象，以便通过点表示法访问
    config = json.loads(json.dumps(config_dict), object_hook=lambda d: SimpleNamespace(**d))
    
    # 初始化MinIO处理器
    try:
        minio_handler = MinIOHandler(config)
        print("MinIO处理器初始化成功")
        
        # 创建测试文件
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp:
            temp.write(b"111")
            test_file_path = temp.name
        
        print(f"创建测试文件: {test_file_path}")
        
        # 测试上传文件
        print("\n测试上传文件...")
        upload_result = minio_handler.upload_file(test_file_path, "test-file.txt")
        if upload_result:
            print(f"文件上传成功: {upload_result}")
        else:
            print("文件上传失败")
            exit(1)
        
        # 测试获取公网URL
        print("\n测试获取公网URL...")
        success, url = minio_handler.get_public_url("test-file.txt")
        if success:
            print(f"获取URL成功: {url}")
        else:
            print(f"获取URL失败: {url}")
        
        # 测试列出文件
        print("\n测试列出文件...")
        success, files = minio_handler.list_files()
        if success:
            print(f"文件列表: {files}")
        else:
            print(f"列出文件失败: {files}")
        
        # 测试下载文件
        print("\n测试下载文件...")
        download_path = os.path.join(tempfile.gettempdir(), "downloaded-test-file.txt")
        success, message = minio_handler.download_file("test-file.txt", download_path)
        if success:
            print(f"文件下载成功: {download_path}")
            with open(download_path, 'r') as f:
                print(f"下载文件内容: {f.read()}")
        else:
            print(f"文件下载失败: {message}")
        
        # 测试删除文件
        # print("\n测试删除文件...")
        # success, message = minio_handler.delete_file("test-file.txt")
        # if success:
        #     print(message)
        # else:
        #     print(f"删除文件失败: {message}")
        
        # 清理测试文件
        os.unlink(test_file_path)
        if os.path.exists(download_path):
            os.unlink(download_path)
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")