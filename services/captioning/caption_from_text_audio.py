from dataclasses import dataclass
from typing import List
import librosa
from pydub import AudioSegment

class ChatTTSSegments:
    def __init__(self, text, begin_time, end_time, duration=None, process_type=None):
        self.text = text
        self.begin_time = begin_time
        self.end_time = end_time
        self.duration = duration
        self.process_type = process_type

    def __str__(self):
        return f"{self.text} {self.begin_time} {self.end_time}"

class CaptioningService:
    def __init__(self):
        
        self.results: List[ChatTTSSegments] = []

    def convert_to_srt_format(self,results: List[ChatTTSSegments]) -> str:
        def format_time(seconds: float) -> str:
            """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            milliseconds = int((seconds % 1) * 1000)
            seconds = int(seconds)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

        srt_parts = []
        for index, result in enumerate(results, 1):
            # 格式化开始和结束时间
            start_time = format_time(result.begin_time)
            end_time = format_time(result.end_time)
            
            # 构建 SRT 格式字幕块
            srt_block = f"{index}\n{start_time} --> {end_time}\n{result.text}\n"
            srt_parts.append(srt_block)

        return "\n".join(srt_parts)

    def generate_caption(self, audio_files: List[str], contents: List[str]) -> List[ChatTTSSegments]:
        print("字幕音频列表",audio_files)
        print("字幕文字列表",contents)
        """
        根据音频文件列表和内容列表生成字幕结果
        
        Args:
            audio_files: 音频文件路径列表
            contents: 对应的文本内容列表
            
        Returns:
            List[ChatTTSSegments]: 识别结果列表
        """
        # 确保音频文件列表和内容列表长度相同
        if len(audio_files) != len(contents):
            raise ValueError("音频文件列表和内容列表长度不匹配")
        
        self.results = []
        current_time = 0.0
        
        for audio_file, content in zip(audio_files, contents):
            try:
                # 获取音频时长
                sound = AudioSegment.from_wav(audio_file)
                audio_duration = sound.duration_seconds
                #audio_duration = librosa.get_duration(path=audio_file)
                
                # 创建结果对象
                self.results.append(
                    ChatTTSSegments(
                        text=content,
                        begin_time=current_time,
                        end_time=current_time + audio_duration,
                        duration=audio_duration,
                        process_type= None

                    )
                )
                
                # 更新下一段的开始时间
                current_time += audio_duration
                
            except Exception as e:
                raise Exception(f"处理音频文件 {audio_file} 时出错: {str(e)}")

        
        return self.results
    
    

    def get_results(self) -> List[ChatTTSSegments]:
        """获取当前的识别结果列表"""
        return self.results

    def clear_results(self):
        """清空当前的识别结果列表"""
        self.results = []
