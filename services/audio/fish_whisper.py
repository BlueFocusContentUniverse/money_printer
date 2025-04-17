import os
import json
import httpx
import ormsgpack
import asyncio
from typing import List, Dict, Any
from pathlib import Path

from common.config.config import my_config

class FishSpeechRecognizer:
    def __init__(self):
        """初始化 Fish Audio ASR 服务"""
        self.api_key = my_config['audio']['fish_audio']['api_key']

        if not self.api_key:
            raise ValueError("请设置 Fish Audio api key")
        
        self.api_url = "https://api.fish.audio/v1/asr"

    def transcribe_audio(self, audio_file_path: str):
        """同步调用 Fish Audio ASR API 进行音频转写"""
        try:
            # 读取音频文件
            with open(audio_file_path, "rb") as audio_file:
                audio_data = audio_file.read()
            
            # 准备请求数据
            request_data = {
                "audio": audio_data,
                "language": "zh",  # 指定语言为中文
                "ignore_timestamps": False  # 获取精确时间戳
            }
            
            # 发送请求
            with httpx.Client() as client:
                response = client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/msgpack",
                    },
                    content=ormsgpack.packb(request_data),
                    timeout=None  # 对于长音频，可能需要较长时间
                )
                
                # 检查响应状态
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                
                print("Fish Audio ASR 响应:", result)
                return result
                
        except Exception as e:
            raise RuntimeError(f"Fish Audio ASR API 调用失败: {str(e)}")

    async def transcribe_audio_async(self, audio_file_path: str):
        """异步调用 Fish Audio ASR API"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.transcribe_audio, audio_file_path
        )

    def transcribe_video_audio(self, audio_path: str, output_dir: str):
        """处理音频文件并保存结果"""
        try:
            # 直接转写音频
            transcription = self.transcribe_audio(audio_path)
            print("Transcription type:", type(transcription))  # 添加调试信息

            # 初始化结果列表
            simplified_segments = []
            
            # 处理音频开始的静音部分
            if 'segments' in transcription and len(transcription['segments']) > 0:
                first_segment = transcription['segments'][0]
                if first_segment['start'] > 0:
                    simplified_segments.append({
                        "start": 0,
                        "end": first_segment['start'],
                        "text": ""
                    })
            
            # 定义中文标点符号列表
            punctuation_marks = ['。', '！', '？', '；', '，',  '!', '?', ';', ',']
            
            # 处理所有segments和它们之间的间隔
            for i, segment in enumerate(transcription['segments']):
                text = segment['text']
                start_time = segment['start']
                end_time = segment['end']
                duration = end_time - start_time
                
                # 如果文本为空，直接添加原始segment
                if not text.strip():
                    simplified_segments.append({
                        "start": start_time,
                        "end": end_time,
                        "text": text
                    })
                    continue
                
                # 计算每个字符的平均时长
                chars_count = len(text)
                time_per_char = duration / chars_count if chars_count > 0 else 0
                
                # 根据标点符号拆分文本
                sub_segments = []
                last_cut = 0
                
                # 查找所有标点符号位置
                for j, char in enumerate(text):
                    if char in punctuation_marks or j == len(text) - 1:
                        # 如果是最后一个字符且不是标点，需要包含这个字符
                        end_idx = j + 1
                        sub_text = text[last_cut:end_idx]
                        
                        # 计算这部分文本的时长和时间戳
                        sub_duration = len(sub_text) * time_per_char
                        sub_start = start_time + last_cut * time_per_char
                        sub_end = sub_start + sub_duration
                        
                        # 添加到子segments列表
                        sub_segments.append({
                            "start": sub_start,
                            "end": sub_end,
                            "text": sub_text
                        })
                        
                        # 更新下一段的起始位置
                        last_cut = end_idx
                
                # 如果没有找到任何标点符号，使用原始segment
                if not sub_segments:
                    simplified_segments.append({
                        "start": start_time,
                        "end": end_time,
                        "text": text
                    })
                else:
                    # 按字数限制进行二次分割
                    final_segments = []
                    max_chars = 15  # 最大字符数限制
                    
                    for sub_seg in sub_segments:
                        sub_text = sub_seg["text"]
                        sub_start = sub_seg["start"]
                        sub_end = sub_seg["end"]
                        
                        # 如果文本长度超过限制，进行分割
                        if len(sub_text) > max_chars:
                            # 计算分割点（尽量在中间位置）
                            mid_point = len(sub_text) // 2
                            
                            # 分割文本
                            first_part = sub_text[:mid_point]
                            second_part = sub_text[mid_point:]
                            
                            # 计算每部分的时间戳
                            first_duration = len(first_part) * time_per_char
                            first_end = sub_start + first_duration
                            
                            # 添加两部分到最终列表
                            final_segments.append({
                                "start": sub_start,
                                "end": first_end,
                                "text": first_part
                            })
                            final_segments.append({
                                "start": first_end,
                                "end": sub_end,
                                "text": second_part
                            })
                        else:
                            # 文本长度在限制内，直接添加
                            final_segments.append(sub_seg)
                    
                    # 添加所有处理后的子segments
                    simplified_segments.extend(final_segments)
                
                # 检查与下一个segment之间是否有间隔
                if i < len(transcription['segments']) - 1:
                    next_segment = transcription['segments'][i + 1]
                    if next_segment['start'] > segment['end']:
                        simplified_segments.append({
                            "start": segment['end'],
                            "end": next_segment['start'],
                            "text": ""
                        })
            
            # 处理最后一个segment之后的静音部分
            if transcription['segments']:
                last_segment = transcription['segments'][-1]
                if last_segment['end'] < transcription['duration']:
                    simplified_segments.append({
                        "start": last_segment['end'],
                        "end": transcription['duration'],
                        "text": ""
                    })
            
            # 保存转写结果
            audio_name = os.path.splitext(os.path.basename(audio_path))[0]
            output_path = os.path.join(output_dir, f"{audio_name}_fish_analysis_results.json")
            
            # 同步写入 JSON 文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(simplified_segments, f, ensure_ascii=False, indent=2)
            
            return simplified_segments
        except Exception as e:
            raise RuntimeError(f"处理音频失败: {str(e)}")

    @staticmethod
    async def _extract_audio(video_path: str) -> str:
        """从视频中提取音频"""
        audio_path = video_path.rsplit(".", 1)[0] + ".wav"
        
        # 首先获取视频时长
        duration_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
        duration_process = await asyncio.create_subprocess_shell(
            duration_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        duration_output, _ = await duration_process.communicate()
        total_duration = float(duration_output.decode().strip())
        
        # 使用 progress 参数显示处理进度
        cmd = (
            f'ffmpeg -y -hwaccel auto -i "{video_path}" '
            f'-vn -acodec pcm_s16le -ar 16000 -ac 1 '
            f'-threads 0 -progress pipe:1 "{audio_path}"'
        )
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            line = line.decode().strip()
            if line.startswith('out_time_ms='):
                current_time = int(line.split('=')[1]) / 1000000  # 转换为秒
                progress = (current_time / total_duration) * 100
                print(f'\r处理进度: {progress:.1f}%', end='')
        
        await process.wait()
        print('\n音频提取完成')
        
        return audio_path

def test_fish_speech_recognizer():
    """测试FishSpeechRecognizer的功能"""
    try:
        # 初始化识别器
        recognizer = FishSpeechRecognizer()
        
        # 测试音频路径和输出目录
        audio_path = "/path/to/your/test/audio.wav"  # 替换为实际的测试音频路径
        output_dir = "output"
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 执行转写
        print("开始处理音频...")
        result = recognizer.transcribe_video_audio(audio_path, output_dir)
        print("处理完成！")
        print(f"转写结果已保存到: {output_dir}")
        print(f"转写结果示例: {result[:2]}")  # 打印前两个片段
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")

if __name__ == "__main__":
    test_fish_speech_recognizer() 