import os
import re
import base64
import requests
from typing import List, Optional,Dict,Any
from datetime import datetime
import logging

class ScreenshotHandler:
    def __init__(self, car_keywords=None, params_keywords=None, 
                 screenshot_url="http://172.22.93.27:8187/screenshot",
                 car_params_url="http://172.22.93.27:8187/car_params_pic", 
                 save_dir="screenshots"):
        """
        初始化处理器
        :param car_keywords: 场景关键词列表
        :param params_keywords: 参数关键词列表
        :param screenshot_url: 截图服务的 URL
        :param save_dir: 图片保存目录
        """
        self.screenshot_url = screenshot_url
        self.save_dir = save_dir
        self.car_keywords = car_keywords or []
        self.params_keywords = params_keywords or []

        # API endpoints
        self.screenshot_url = screenshot_url
        self.car_params_url = car_params_url
        
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_car_params_pics(self, car: str, tags: str) -> List[str]:
        """
        
        获取车型参数图片,最多重试 3 次
        Args:
            car: 车型参数
            tags: 标签参数
        Returns:
            图片 URL 列表
        """
        for i in range(3):
            try:
                tags_list = [tags]
                request_params = {
                    'car': car,
                    'tags': tags_list
                }
                
                # 打印请求结构体
                print(f"Request Params: {request_params}")
                
                # 直接调用 API
                response = requests.post(
                    self.car_params_url,
                    json=request_params
                )
                print(f"Received response: {response}")
                data = response.json()
                # 解析嵌套结构：car_param{tags['url1','url2',...]}
                if car in data:
                    car_data = data[car]
                    if tags in car_data:
                        return car_data[tags]  # 返回 URL 列表
            except Exception as e:    
                self.logger.error(f"Error getting car params pics: {e}")
            else:
                break
        else:
            self.logger.error("Failed to get car params pics after 3 retries")
            return []

    def download_image(self, url: str, filename: str) -> Optional[str]:
        """
        下载图片并保存
        Args:
            url: 图片 URL
            filename: 保存的文件名
        Returns:
            保存的文件路径
        """
        try:
        # 简单校验 URL
            if not url.startswith(('http://', 'https://')):
                self.logger.error(f"Invalid URL: {url}")
                return None
                
            # 设置超时，避免请求卡死
            response = requests.get(url, timeout=10)
            
            # 检查状态码但不抛出异常
            if response.status_code != 200:
                self.logger.error(f"Failed to download image, status code: {response.status_code}")
                return None
                
            # 检查响应类型
            if not response.headers.get('content-type', '').startswith('image/'):
                self.logger.error(f"Not an image response from {url}")
                return None
                
            # 构建保存路径并确保目录存在
            os.makedirs(self.save_dir, exist_ok=True)
            save_path = os.path.join(self.save_dir, f"{filename}.jpg")
            
            # 保存图片
            with open(save_path, 'wb') as f:
                f.write(response.content)
                
            return save_path
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error while downloading {url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        
        return None
        

    def get_screenshot(self, keyword):
        """
        获取指定关键词的截图
        :param keyword: 搜索关键词
        :return: base64 编码的图片数据或 None
        """
        try:
            params = {
                'keyword': keyword
            }
            response = requests.get(
                self.screenshot_url, 
                params=params
            )
            
            if response.status_code == 200:
                # 记录响应内容类型
                self.logger.info(f"Response content type: {response.headers.get('content-type', 'unknown')}")
                return response.text
            else:
                self.logger.error(f"Screenshot request failed with status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting screenshot: {e}")
            return None

    def save_image(self, base64_data, keyword):
        """
        将 base64 数据保存为图片
        :param base64_data: base64 编码的图片数据
        :param keyword: 用于生成文件名的关键词
        :return: 保存的文件路径或 None
        """
        try:
            # 生成安全的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_keyword = re.sub(r'[^a-zA-Z0-9]', '_', keyword)
            filename = f"{safe_keyword}_{timestamp}.png"
            filepath = os.path.join(self.save_dir, filename)
            # 确保文件路径的目录存在
            directory = os.path.dirname(filepath)
            if not os.path.exists(directory):
                os.makedirs(directory)
            
            # 解码并保存图片
            image_data = base64.b64decode(base64_data)
            with open(filepath, 'wb') as f:
                f.write(image_data)
                
            self.logger.info(f"Image saved successfully: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return None

    def process_text(self, car_param, keyword_param):
        """
        处理文本并获取相关截图
        Args:
            car_param: 车型参数
            keyword_param: 关键词参数
        Returns:
            str: 图片文件路径
        Raises:
            Exception: 处理失败时抛出异常
        """
        if keyword_param == '价格':
            # 获取截图,最多重试 3 次
            for i in range(3):
                base64_data = self.get_screenshot(car_param)
                if base64_data:
                    break
            else:
                self.logger.error("Failed to get screenshot after 3 retries")
                return None
                
            # 处理 base64 数据
            if '<img' in base64_data:
                match = re.search(r'base64,([^"]*)', base64_data)
                if not match:
                    raise ValueError("Invalid base64 data format")
                base64_data = match.group(1)
            
            # 保存图片
            filepath = self.save_image(base64_data, car_param)
            if not filepath:
                raise Exception("Failed to save image")
            
            return filepath
                
        else:
            # 获取参数图片
            image_urls = self.get_car_params_pics(car_param, keyword_param)
            if not image_urls:
                print(f"No images found for {car_param} with param {keyword_param}")
                return None  # 正常情况下没有图片，返回 None
            
            # 下载第一个图片,最多重试 3 次
            for i in range(3):
                filepath = self.download_image(image_urls[0], f"{car_param}_{keyword_param}")
                if filepath:
                    break
            else:
                self.logger.error("Failed to download image after 3 retries")
                return None
                    
            return filepath
            