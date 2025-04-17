from typing import List, Optional,Dict,Any
from dataclasses import dataclass
from services.material_process.screenshot import ScreenshotHandler
from services.captioning.caption_from_text_audio import ChatTTSSegments
from services.video.video_service import VideoService
from services.material_process.overlay_image import overlay_image_on_video
from services.material_process.sound_effect_analyzer import SoundEffectResult
import subprocess
import re
import os
from openai import OpenAI
import httpx
import yaml

proxy_host = "172.22.93.27"
proxy_port = "1081"



# 读取配置文件
with open('common/config/config.yml', 'r') as file:
    config = yaml.safe_load(file)
# 从环境变量中读取 API Key 和 Base URL
os.environ['OPENAI_API_KEY'] = config['llm']['OpenAI']['api_key']
os.environ['OPENAI_API_BASE_URL'] = config['llm']['OpenAI']['base_url']

api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_API_BASE_URL")

@dataclass 
class OverlayAnalysisResult:
    """贴图分析结果"""
    # 时间信息
    # 必需参数（没有默认值的）放前面
    text_position: int     # 在文本中的位置
    begin_time: float
    end_time: float
    duration: float
    search_keyword: str
    text_content: str
    overlay_image: Optional[str]
    # 有默认值的参数放后面
    params: Optional[Dict[str, Any]] = None
    process_type: str = ''


class OverlayAnalyzer:
    """贴图分析器：负责分析和标记"""
    """# 1. 初始化分析器
        analyzer = OverlayAnalyzer()
        analyzer.init_with_full_text(full_text)  # 先处理整体文本

        # 2. 逐行处理
        for line in full_text.splitlines():
            if "[I-" in line:  # 有贴图标记的行才处理
                segment = get_segment_for_line(line)  # 获取对应的时间段
                analysis_result = analyzer.analyze(line, segment)
                # ... 后续处理 ..."""
    
    def __init__(self):
        self.tag_pattern = r'\[I-(.*?)\]'
        self.content_pattern = r'\[I-.*?\](.*?)\[/I\]'
        self.screenshot_handler = ScreenshotHandler()
        self.car_keyword = None

    def init_with_full_text(self, full_text: str):
        """
        初始化时提取 car 关键词
        Args:
            full_text: 完整的多行文本
        """
        try:
            self.car_keyword = self._extract_car_keyword(full_text)
        except Exception as e:
            raise 
    
    def analyze(self, text: str, segment: ChatTTSSegments, sound_effect: Optional[SoundEffectResult] = None) -> OverlayAnalysisResult:
        """
        分析文本并标记 segment
        Args:
            text: 原始文本
            segment: 原始时间段
        Returns:
            标记后的时间段
        """
        """分析并返回完整的处理参数"""
        text = text.strip().strip('"\'')  # 去除首尾空白和引号
        try:
            # 1. 提取文本内容
            print(f"\n 开始处理文本: {text}")
            keyword = self._get_tag_keyword(text)
            print(f"提取的关键词: {keyword}")
            
            if not keyword:
                print("未找到关键词，返回 None")
                return None 
            else:
                # 2. 获取关键词
                content = self._get_content_text(text)
                print(f"提取的内容文本: {content}")
                
                if not content:
                    print("未找到内容文本，返回 None")
                    return None 
                else:
                    search_term = self._map_keyword_to_search_term(keyword)
                    print(f"映射后的搜索词: {search_term}")
                    
                    # 3. 获取截图
                    print(f"开始获取截图，参数: car_keyword={self.car_keyword}, search_term={search_term}")
                    overlay_image = self.screenshot_handler.process_text(self.car_keyword, search_term)
                    print(f"获取的截图路径: {overlay_image}")
                    
                    # 4. 计算时间
                    start_pos = segment.text.find(content)
                    print(f"\n 时间计算:")
                    print(f"segment 文本: {segment.text}")
                    print(f"查找内容: {content}")
                    print(f"开始位置: {start_pos}")
                    
                    if start_pos == -1:
                        print("未找到匹配位置，抛出异常")
                        raise Exception("未找到匹配位置")
                        
                    total_chars = len(segment.text)
                    total_duration = segment.end_time - segment.begin_time
                    char_duration = total_duration / total_chars

                    # 3. 计算实际时间（考虑音效偏移）
                    text_start_time = segment.begin_time + (start_pos * char_duration)
                    # 如果有音效且音效在贴图位置之前，加上音效时长
                    if sound_effect and sound_effect.text_position < start_pos:
                        text_start_time += sound_effect.duration
                    
                    print(f"总字符数: {total_chars}")
                    print(f"总持续时间: {total_duration}")
                    print(f"每字符持续时间: {char_duration}")
                    
                    text_end_time = text_start_time + (len(content) * char_duration) + 1.5
                    
                    print(f"计算结果:")
                    print(f"开始时间: {text_start_time}")
                    print(f"结束时间: {text_end_time}")
                    print(f"持续时间: {text_end_time - text_start_time}")
                    
                    # 5. 返回完整结果
                    result = OverlayAnalysisResult(
                        text_position=start_pos, 
                        begin_time=text_start_time,
                        end_time=text_end_time,
                        duration=text_end_time - text_start_time , #加1.5秒优化用户观感
                        search_keyword=search_term,
                        overlay_image=overlay_image,
                        text_content=content,
                        params=None,
                        process_type = 'overlay'
                    )
                    print(f"\n 最终返回结果: {result}")
                    return result
                    
        except Exception as e:
            print(f"\n 处理过程中出现异常: {str(e)}")
            raise

    def _extract_car_keyword(self, full_text: str) -> str:
        """
        从整体文本提取 car 关键词
        这里需要实现文本总结的逻辑
        """
        
        client = OpenAI(
            api_key=api_key, 
            base_url=base_url,
            http_client=httpx.Client(
                proxies={
                    "http://": f"http://{proxy_host}:{proxy_port}",
                    "https://": f"http://{proxy_host}:{proxy_port}"
                })
        )
        system_prompt = "你是汽车关键词分类员，根据口播稿内容提取出这篇文案所描述车的完整车名，如理想L7，小鹏G9，宝马X3等。必须携带品牌和车型！！！直接输出车名，因为我要直接将你的输出作为API的入参，所以禁止出现多余的信息或标点符号."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_text}
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        result_content = response.choices[0].message.content
        print(result_content)
        return result_content

    def _get_content_text(self, text: str) -> Optional[str]:
        """获取标签内容"""
        match = re.search(self.content_pattern, text)
        if match:
            print(f"匹配组: {match.groups()}")
            print(f"group(1): {match.group(1)}")
            return match.group(1)
        else:
            print("未匹配到内容")
            return None
        

    def _get_tag_keyword(self, text: str) -> Optional[str]:
        """获取关键词"""
        print(f"\n 正则匹配测试:")
        print(f"输入文本: {text}")
        print(f"正则表达式: {self.tag_pattern}")
        
        match = re.search(self.tag_pattern, text)
        print(f"匹配结果: {match}")
        
        if match:
            print(f"匹配组: {match.groups()}")
            print(f"group(1): {match.group(1)}")
            return match.group(1)
        else:
            print("未匹配到关键词")
            return None

            
    def _map_keyword_to_search_term(self, keyword: str) -> str:
        """映射搜索关键词"""
        client = OpenAI(
            api_key=api_key, 
            base_url=base_url,
            http_client=httpx.Client(
                proxies={
                    "http://": f"http://{proxy_host}:{proxy_port}",
                    "https://": f"http://{proxy_host}:{proxy_port}"
                })
        )
        system_prompt = "你是汽车关键词分类员，将我输入的内容匹配到合适的**一个关键词**，并直接输出该关键词，以下是你可以选择的参数列表：[加速时间，刹车距离，油耗/能耗，噪音，中控方向盘，乘坐空间，天窗规格，储物空间，后备箱，车身尺寸，车轮轮胎，动力系统，车辆悬架，底盘细节，防撞梁，涉水性，四驱结构，四驱性能，保养周期，保养性能，价格]因为我要直接将你的输出作为API的入参(str格式），所以禁止出现多余的信息或标点符号."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": keyword}
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
            
        result_content = response.choices[0].message.content
        print(result_content)
        return result_content
    
