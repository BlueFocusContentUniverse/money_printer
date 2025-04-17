from typing import List, Optional,Dict,Any
from dataclasses import dataclass
from services.material_process.screenshot import ScreenshotHandler
from services.captioning.caption_from_text_audio import ChatTTSSegments
from services.video.video_service import VideoService
from pydub import AudioSegment
import subprocess
import re
import os
from openai import OpenAI
import yaml

# 读取配置文件
with open('common/config/config.yml', 'r') as file:
    config = yaml.safe_load(file)
# 从环境变量中读取 API Key 和 Base URL
os.environ['OPENAI_API_KEY'] = config['llm']['OpenAI']['api_key']
os.environ['OPENAI_API_BASE_URL'] = config['llm']['OpenAI']['base_url']

api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_API_BASE_URL")

@dataclass 
class SoundEffectResult:
    """音效分析结果"""
    """音效信息"""
    text_position: int      # 在文本中的位置
    sound_file: str        # 音效文件路径
    duration: float        # 音效时长
    effect_type: str     # 原始文本("叮")
    start_time: float      # 实际插入的开始时间
    end_time: float        # 结束时间(start_time + duration)


class SoundEffectAnalyzer:
    def __init__(self):
        """
        Args:
            pattern：正则匹配方法
         
        """
        self.pattern = r'\[S-([^\]]+)\](.*?)\[/S\]'  # [S-提示音]叮[/S]
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.sound_dir = config['paths']['sound_dir']
        self.available_sounds = self._scan_sound_files()

    def _scan_sound_files(self) -> List[str]:
        """扫描可用的音效文件"""
        sound_files = []
        if os.path.exists(self.sound_dir):
            for file in os.listdir(self.sound_dir):
                if file.endswith('.mp3'):
                    sound_files.append(os.path.splitext(file)[0])
        return sound_files
    
    def _map_sound_effect(self, sound_text: str) -> str:
        """使用GPT-4.0 Mini映射音效"""
        if sound_text in self.available_sounds:
            return sound_text
            
        prompt = f"""我有这些可用的音效文件：{', '.join(self.available_sounds)}
                    需要找到一个最匹配"{sound_text}"的音效，
                    只需要返回一个最匹配的文件名，不需要其他解释。"""
                    
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=50
        )
        
        suggested_sound = response.choices[0].message.content.strip()
        return suggested_sound if suggested_sound in self.available_sounds else self.available_sounds[0]


    def analyze(self, text: str, segment: ChatTTSSegments) -> Optional[SoundEffectResult]:
        """分析文本中的音效标记"""
        match = re.search(self.pattern, text)
        if not match:
            return None
            
        sound_text = match.group(2)   # 直接获取"叮"
        if not sound_text:
            return None
        # 获取音效文件路径和时长

        mapped_sound = self._map_sound_effect(sound_text)
        sound_file = os.path.join(self.sound_dir, f"{mapped_sound}.mp3")
        
        try:
            sound_effect = AudioSegment.from_file(sound_file)
            duration = len(sound_effect) / 1000
            
            text_position = match.start()
            char_duration = (segment.end_time - segment.begin_time) / len(segment.text)
            start_time = text_position * char_duration
            
            return SoundEffectResult(
                text_position=text_position,
                sound_file=sound_file,
                duration=duration,
                effect_type=sound_text,
                start_time=start_time,
                end_time=start_time + duration
            )
        except Exception as e:
            print(f"无法加载音效文件 {sound_file}: {str(e)}")
            return None
