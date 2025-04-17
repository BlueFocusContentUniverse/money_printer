import openai
from openai import OpenAI
from typing import Dict
from pathlib import Path
import aiohttp
import asyncio
import os
import json
import aiofiles

class SpeechRecognizer:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    async def transcribe_audio_async(self, audio_file_path: str):
        """异步调用 Whisper API 进行音频转写"""
        try:
            client = OpenAI(
                base_url="https://nwxbqdio.cloud.sealos.io/v1",
                api_key="sk-fP9srnCe924dcrKGWn6yuN7MRP9ugFWlWDCubNQDbjblBBxg"
                )
            with open(audio_file_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper",
                    file=audio_file,
                    response_format="verbose_json",  # 获取详细时间戳信息
                    timestamp_granularities=["segment"]  # 获取段落级别时间戳
                )
                #print(f"Token usage: {token_usage}")
                return response
                
            
        except Exception as e:
            raise RuntimeError(f"Whisper API 调用失败: {str(e)}")
            
    async def transcribe_video_audio(self, video_path: str, output_dir: str):
        """处理视频文件的音频并保存结果"""
        try:
            # 1. 提取音频
            audio_path = await self._extract_audio(video_path)
            
            # 2. 转写音频
            transcription = await self.transcribe_audio_async(audio_path)

            # 初始化结果列表
            simplified_segments = []
            
            # 处理音频开始的静音部分
            if transcription.segments and transcription.segments[0].start > 0:
                simplified_segments.append({
                    "start": 0,
                    "end": transcription.segments[0].start,
                    "text": "未识别出明显声音"
                })
            
            # 处理所有segments和它们之间的间隔
            for i, segment in enumerate(transcription.segments):
                simplified_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })
                
                # 检查与下一个segment之间是否有间隔
                if i < len(transcription.segments) - 1:
                    next_segment = transcription.segments[i + 1]
                    if next_segment.start > segment.end:
                        simplified_segments.append({
                            "start": segment.end,
                            "end": next_segment.start,
                            "text": "未识别出明显声音"
                        })
            
            # 处理最后一个segment之后的静音部分
            if transcription.segments:
                last_segment = transcription.segments[-1]
                if last_segment.end < transcription.duration:
                    simplified_segments.append({
                        "start": last_segment.end,
                        "end": transcription.duration,
                        "text": "未识别出明显声音"
                    })
            
            # 3. 保存转写结果
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(output_dir, f"{video_name}_whisper_analysis_results.json")
            
            # 使用 aiofiles 异步写入 JSON 文件
            async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(simplified_segments, ensure_ascii=False, indent=2))
            
            return simplified_segments
        except Exception as e:
            raise RuntimeError(f"处理视频音频失败: {str(e)}")

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
    
async def test_speech_recognizer():
    """测试SpeechRecognizer的功能"""
    try:
        # 从环境变量获取API密钥
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("错误：请设置OPENAI_API_KEY环境变量")
            return

        # 初始化识别器
        recognizer = SpeechRecognizer(api_key)
        
        # 测试视频路径和输出目录
        video_path = "/home/apps/video_script_checker/data/7f9ef218-344c-44ca-b46a-76323364825f_video.mp4"  # 替换为实际的测试视频路径
        output_dir = "output"
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 执行转写
        print("开始处理视频...")
        result = await recognizer.transcribe_video_audio(video_path, output_dir)
        print("处理完成！")
        print(f"转写结果已保存到: {output_dir}")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
    

