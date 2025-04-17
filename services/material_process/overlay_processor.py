from typing import List, Optional,Dict,Any
from dataclasses import dataclass
from services.material_process.screenshot import ScreenshotHandler
from services.material_process.material_processor import ProcessConfig,BaseProcessor
from services.captioning.caption_from_text_audio import ChatTTSSegments
from services.video.video_service import VideoService
from services.material_process.overlay_image import overlay_image_on_video
from services.material_process.overlay_analyzer import OverlayAnalysisResult
import subprocess
import re
import os
from openai import OpenAI
import yaml


    


@dataclass

class OverlayTimeRange:
    """贴图时间范围"""
    should_process: bool
    analysis_result:Optional[OverlayAnalysisResult] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class OverlayProcessor:
    """贴图处理器"""
    def __init__(self,video_processor: VideoService):
        self.screenshot_handler = ScreenshotHandler()
        self.video_processor = video_processor
        #self.analyzer = OverlayAnalyzer()
        
    
    @staticmethod
    def should_process(analysis_results: List[OverlayAnalysisResult], 
                  current_time: float,
                  end_time: float,
                  video_duration: float) -> OverlayTimeRange:
        """
        判断当前素材是否需要贴图及贴图时间范围
        Args:
            analysis_results: 贴图分析结果列表
            current_time: 当前素材在口播中的开始时间
            end_time: 当前素材在口播中的结束时间
            video_duration: 当前视频片段的时长
        Returns:
            OverlayTimeRange: 包含是否处理和相对于视频片段的时间范围
        """
        for analysis_result in analysis_results:
            if not analysis_result or not analysis_result.overlay_image:
                continue

            overlay_start = analysis_result.begin_time
            overlay_end = analysis_result.end_time

            # 情况 1: 当前时间在贴图区间内
            if overlay_start <= current_time <= overlay_end:
                actual_end = min(end_time, overlay_end)
                # 转换为相对时间
                relative_start = 0  # 从视频开始
                relative_end = (actual_end - current_time)  # 相对结束时间
                print(f"情况 1: 当前时间 {current_time} 在贴图区间内，处理时间范围: {relative_start} 到 {relative_end}")
                return OverlayTimeRange(
                    should_process=True,
                    analysis_result = analysis_result,
                    start_time=relative_start,
                    end_time=relative_end
                )
            
            # 情况 2: 当前时间在贴图区间前，但结束时间在区间内
            if current_time < overlay_start and overlay_start <= end_time:
                actual_end = min(end_time, overlay_end)
                # 转换为相对时间
                relative_start = overlay_start - current_time  # 从视频中间开始
                relative_end = actual_end - current_time  # 相对结束时间
                print(f"情况 2: 当前时间 {current_time} 在贴图区间前，处理时间范围: {relative_start} 到 {relative_end}")
                return OverlayTimeRange(
                    should_process=True,
                    analysis_result = analysis_result,
                    start_time=relative_start,
                    end_time=relative_end
                )
            
            # 情况 3: 贴图区间在当前片段中间
            if current_time < overlay_start and end_time > overlay_end:
                # 转换为相对时间
                relative_start = overlay_start - current_time
                relative_end = overlay_end - current_time
                print(f"情况 3: 贴图区间在当前片段中间，处理时间范围: {relative_start} 到 {relative_end}")
                return OverlayTimeRange(
                    should_process=True,
                    analysis_result = analysis_result,
                    start_time=relative_start,
                    end_time=relative_end
                )
        print("没有需要处理的贴图")
        return OverlayTimeRange(should_process=False)

    def process(self, video_path: str, 
           time_range: OverlayTimeRange) -> str:
        """处理视频添加贴图"""
        analysis_result = time_range.analysis_result
        try:
            if not time_range.should_process:
                return video_path
                
            # 1. 初始化视频处理器 
            # 2. 处理视频
            #processed_path = self.video_processor.normalize_video(video_path)
            if not analysis_result:
                print(f"分析结果为空，跳过处理")
                return video_path
            
            if not analysis_result.overlay_image:
                print(f"贴图路径为空，跳过处理")
                return video_path
                
            if not time_range.should_process:
                print(f"不需要处理，跳过")
                return video_path
            # 3. 添加贴图
            return self._apply_overlay(
                video_path, 
                analysis_result.overlay_image,
                time_range.start_time,
                time_range.end_time
            )
            
        except Exception as e:
            raise 

    def _apply_overlay(self, video_path: str, 
                overlay_image: str,
                start_time: float,
                end_time: float) -> str:
        """应用贴图
        Args:
            video_path: 输入视频路径
            overlay_image: 贴图图片路径
            start_time: 开始时间
            end_time: 结束时间
        Returns:
            str: 处理后的视频路径，如果处理失败则返回原始视频路径
        """
        print("开始应用贴图")
        try:
            base_name = os.path.basename(video_path)
            output_path = f"{os.path.splitext(base_name)[0]}_overlay.mp4"
            overlay_image_on_video(
                video_path=video_path,
                image_path=overlay_image,
                output_path=output_path,
                start_time=start_time,
                end_time=end_time,
                opacity=0.9,  # 可以作为配置参数
                padding=100,   # 可以作为配置参数
                fade_duration=0.0,  # 可以作为配置参数
                quality='high'  # 可以作为配置参数
            )
            
            # 检查输出文件是否存在且大小正常
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            else:
                print(f"贴图处理后的文件无效或不存在: {output_path}")
                return video_path
                
        except Exception as e:
            print(f"贴图处理失败: {str(e)}")
            return video_path