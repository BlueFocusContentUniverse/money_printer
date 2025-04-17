import os
import io
import base64
from pathlib import Path
import datetime
import time
import uuid

import httpx
import ormsgpack
from pydantic import BaseModel
from typing import Literal, Optional
from pydub import AudioSegment
from pydub.playback import play

from common.config.config import my_config
from tools.utils import must_have_value, random_with_system_time
from .tts_audio_editor import AudioCutConfig, TTSAudioCutter

#
class ServeReferenceAudio(BaseModel):
    audio: bytes
    text: str


class ServeTTSRequest(BaseModel):
    text: str
    chunk_length: int = 200
    format: Literal["wav", "pcm", "mp3"] = "mp3"
    mp3_bitrate: Literal[64, 128, 192] = 128
    references: list[ServeReferenceAudio] = []
    reference_id: Optional[str] = None
    normalize: bool = True
    latency: Literal["normal", "balanced"] = "normal"


class FishAudioService:
    def __init__(self, task_params=None, audio_output_dir=None):
        """初始化 Fish Audio 服务
        :param task_params: 任务参数字典，包含所有配置参数
        :param audio_output_dir: 音频输出目录
        """
        if task_params is None:
            task_params = {}

        # 从配置获取 API Key
        self.api_key = my_config['audio']['fish_audio']['api_key']
        must_have_value(self.api_key, "请设置 Fish Audio api key")
        
        # 确保输出目录存在
        self.audio_output_dir = audio_output_dir
        if self.audio_output_dir:
            os.makedirs(self.audio_output_dir, exist_ok=True)
        
        self.api_url = "https://api.fish.audio/v1/tts"

        # 音频生成相关参数
        self.reference_id = task_params.get('reference_id','1f38cc50efde487fafbb1f13a9041117')
        self.mp3_bitrate = task_params.get('mp3_bitrate', 128)
        self.chunk_length = task_params.get('chunk_length', 200)
        self.latency_mode = task_params.get('latency_mode', 'normal')
        
        # 音频剪切相关参数
        self.enable_audio_cut = task_params.get('enable_audio_cut', True)
        if self.enable_audio_cut:
            self.audio_cut_config = AudioCutConfig(
                threshold=task_params.get('audio_cut_threshold', -50),
                min_silence_len=task_params.get('audio_cut_min_silence_len', 500),
                keep_silence=task_params.get('audio_cut_keep_silence', 0)
            )
            self.audio_cutter = TTSAudioCutter(self.audio_cut_config)

        self.audio_gain_db = 5

    def read_with_content(self, content):
        """读取内容并播放音频"""
        wav_file = os.path.join(self.audio_output_dir, f"{random_with_system_time()}.wav")
        print("wav_file_path: ", wav_file)
        temp_file = self.chat_with_content(content, wav_file)
        if temp_file:
            audio = AudioSegment.from_file(temp_file, format="wav")
            play(audio)

    def chat_with_content(self, content, audio_output_file):
        """生成语音并保存到文件
        :param content: 要转换的文本内容
        :param audio_output_file: 输出音频文件路径（WAV格式）
        :return: 生成的音频文件路径，失败返回 None
        """
        if not content or not content.strip():
            print("Error: Empty content")
            return None

        if not audio_output_file:
            print("Error: No output file specified")
            return None

        request = ServeTTSRequest(
            text=content,
            format="mp3",  # 请求MP3格式
            reference_id=self.reference_id,
            mp3_bitrate=self.mp3_bitrate,
            chunk_length=self.chunk_length,
            latency=self.latency_mode
        )

        try:
            with (
                httpx.Client() as client,
                io.BytesIO() as buffer
            ):
                # 使用流式请求
                with client.stream(
                    "POST",
                    self.api_url,
                    content=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                    headers={
                        "authorization": f"Bearer {self.api_key}",
                        "content-type": "application/msgpack",
                    },
                    timeout=None
                ) as response:
                    response.raise_for_status()
                    total = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    # 将数据流式写入内存缓冲区
                    for chunk in response.iter_bytes():
                        buffer.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            progress = (downloaded / total) * 100
                            print(f"\r下载进度: {progress:.1f}%", end='', flush=True)
                    
                    if total:
                        print()  # 换行

                    # 将缓冲区指针重置到开始位置
                    buffer.seek(0)
                    
                    # 从内存缓冲区加载MP3音频并转换为WAV
                    try:
                        audio = AudioSegment.from_mp3(buffer)
                        
                        # 检查音频是否有效
                        # print(f"\n音频长度: {len(audio)}ms")
                        # print(f"音频参数 - 通道数: {audio.channels}, 采样率: {audio.frame_rate}, 采样宽度: {audio.sample_width}")
                        
                        if hasattr(self, 'audio_gain_db') and self.audio_gain_db != 0:
                            original_volume = audio.dBFS
                            audio = audio.apply_gain(self.audio_gain_db)
                            # print(f"应用音频增益: {self.audio_gain_db}dB, 原始音量: {original_volume:.2f}dB, 调整后音量: {audio.dBFS:.2f}dB")
                        
                        # 导出为WAV格式
                        audio.export(audio_output_file, format="wav")
                        
                        print(f"保存音频文件到: {audio_output_file}")
                        # print(f"文件大小: {os.path.getsize(audio_output_file)} bytes")

                        # 音频剪切处理
                        if self.enable_audio_cut:
                            output_path = Path(audio_output_file)
                            temp_output = output_path.parent / f"{output_path.stem}_{uuid.uuid4()}.temp{output_path.suffix}"
                            
                            try:
                                os.rename(audio_output_file, str(temp_output))
                                original_duration, cut_duration = self.audio_cutter.cut_audio(
                                    str(temp_output),
                                    audio_output_file
                                )
                                # print(f"音频剪切: 原始时长={original_duration:.2f}s, "
                                #       f"剪切后时长={cut_duration:.2f}s")
                            except Exception as e:
                                print(f"音频剪切失败: {e}")
                                if temp_output.exists():
                                    if Path(audio_output_file).exists():
                                        Path(audio_output_file).unlink()
                                    os.rename(str(temp_output), audio_output_file)

                        return audio_output_file

                    except Exception as e:
                        print(f"音频处理错误: {e}")
                        # 如果处理失败，尝试保存原始数据以供调试
                        debug_file = Path(audio_output_file).with_suffix('.mp3.debug')
                        with open(debug_file, 'wb') as f:
                            buffer.seek(0)
                            f.write(buffer.read())
                        print(f"已保存原始数据到: {debug_file}")
                        raise

        except httpx.RequestError as e:
            print(f"请求错误: {e}")
        except Exception as e:
            print(f"错误: {e}")
        
        return None

    

import concurrent.futures
import time
from datetime import datetime
from statistics import mean

def process_text(service, text, index):
    """处理单个文本并返回性能指标"""
    start_time = time.time()
    result = {
        'text': text,
        'index': index,
        'success': False,
        'duration': 0,
        'error': None
    }
    
    try:
        # 生成临时文件名
        temp_file = f"audio_output/test_{index}_{int(datetime.now().timestamp())}.wav"
        service.chat_with_content(text, temp_file)
        result['success'] = True
    except Exception as e:
        result['error'] = str(e)
    finally:
        result['duration'] = time.time() - start_time
        
    return result

def main():
    """并发测试 FishAudioService 的主函数"""
    # 设置测试参数
    test_params = {
        'reference_id': '50d3336eb06943dfa7c7c6bd245413e2',
        'mp3_bitrate': 128,
        'chunk_length': 200,
        'latency_mode': 'normal',
        'enable_audio_cut': False,
        'audio_cut_threshold': -50,
        'audio_cut_min_silence_len': 500,
        'audio_cut_keep_silence': 0,
        'format': 'wav'
    }
    
    # 创建输出目录
    output_dir = "audio_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化服务
    service = FishAudioService(
        task_params=test_params,
        audio_output_dir=output_dir
    )
    
    # 扩展测试文本
    test_texts = [
        "你好，这是一个测试音频。",
        "Fish Audio 提供了高质量的语音合成服务。",
        "让我们来测试一下中文和英文混合的句子：Hello World！",
        "这是一个较长的测试文本，用于测试系统处理长文本的能力。我们需要确保系统能够稳定地处理各种长度的文本内容。",
        "AI语音合成技术正在快速发展，它能够生成自然、流畅的语音，广泛应用于各个领域。"
    ] * 3  # 重复三次以增加测试量
    
    # 性能测试结果
    results = []
    
    print(f"开始并发测试，并发数：5，总测试数：{len(test_texts)}")
    start_time = time.time()
    
    # 使用线程池进行并发处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(process_text, service, text, i)
            for i, text in enumerate(test_texts, 1)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"完成测试 {result['index']}: "
                  f"耗时 {result['duration']:.2f}秒, ")
                  #f"{'成功' if result['success'] else f'失败: {result["error"]}'}")
    
    # 统计结果
    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    success_rate = (success_count / len(results)) * 100
    avg_duration = mean(r['duration'] for r in results)
    
    print("\n性能测试报告:")
    print(f"总测试数量: {len(results)}")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"平均处理时间: {avg_duration:.2f}秒")
    print(f"成功率: {success_rate:.2f}%")
    print(f"并发吞吐量: {len(results) / total_time:.2f} 请求/秒")

if __name__ == "__main__":
    main()