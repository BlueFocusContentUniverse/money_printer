from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional,Dict
from enum import Enum
from services.captioning.caption_from_text_audio import ChatTTSSegments



@dataclass
class ProcessConfig:
    """处理配置"""
    need_overlay: bool = False
    need_sound_effect: bool = False
    need_transition: bool = False
    overlay_image: Optional[str] = None

class MaterialProcessError(Exception):
    """素材处理异常"""
    pass
    
class MaterialProcessor:
    """素材处理主类"""
    def __init__(self):
        self.processors: Dict[str, BaseProcessor] = {}  # 改用字典存储处理器
    
    def process_material(self, video_path: str, text: str, 
                        tts_segments: List[ChatTTSSegments]) -> str:
        """处理单个素材"""
        try:
            # 1. 分析文本，确定需要的处理器
            needed_processors = self._analyze_text(text)
            
            # 2. 初始化所需处理器
            self._init_needed_processors(needed_processors)
            
            # 3. 按需处理
            current_path = video_path
            for processor_type, config in needed_processors.items():
                processor = self.processors.get(processor_type)
                if processor:
                    # 处理器自己负责获取和处理时间段
                    current_path = processor.process(
                        current_path,
                        text, 
                        tts_segments,
                        config
                    )
            
            return current_path
            
        except Exception as e:
            raise MaterialProcessError(f"处理失败: {str(e)}")

    def _analyze_text(self, text: str) -> Dict[str, ProcessConfig]:
        """分析文本，返回需要的处理器及其配置"""
        try:
            needed_processors = {}
            
            # 判断是否需要贴图
            if self._need_overlay(text):
                config = ProcessConfig(need_overlay=True)
                needed_processors['overlay'] = config
                
            # 后续可以添加其他处理器的判断
            
            return needed_processors
            
        except Exception as e:
            raise MaterialProcessError(f"文本分析失败: {str(e)}")

    def _init_needed_processors(self, needed_processors: Dict[str, ProcessConfig]):
        """初始化需要的处理器"""
        processor_map = {
           """ 'overlay': OverlayProcessor,"""
            'sound': SoundEffectProcessor,
            'transition': TransitionProcessor
        }
        
        for processor_type in needed_processors:
            if processor_type not in self.processors:
                processor_class = processor_map.get(processor_type)
                if processor_class:
                    self.processors[processor_type] = processor_class()

class BaseProcessor(ABC):
    """处理器基类"""
    @abstractmethod
    def should_process(self, config: ProcessConfig) -> bool:
        """判断是否需要处理"""
        pass
    
    @abstractmethod
    def get_segments(self, text: str, tts_segments: List[ChatTTSSegments]) -> List[ChatTTSSegments]:
        """获取处理器需要的时间段"""
        pass
    
    @abstractmethod
    def process(self, video_path: str, 
                text: str,
                tts_segments: List[ChatTTSSegments], 
                config: ProcessConfig) -> str:
        """处理素材"""
        pass


class SoundEffectProcessor(BaseProcessor):
    """音效处理器"""
    def should_process(self, config: ProcessConfig) -> bool:
        return config.need_sound_effect
    
    def process(self, video_path: str, 
               segments: List[ChatTTSSegments], 
               config: ProcessConfig) -> str:
        # 音效处理逻辑
        return video_path

class TransitionProcessor(BaseProcessor):
    """转场处理器"""
    def should_process(self, config: ProcessConfig) -> bool:
        return config.need_transition
    
    def process(self, video_path: str, 
               segments: List[ChatTTSSegments], 
               config: ProcessConfig) -> str:
        # 转场处理逻辑
        return video_path