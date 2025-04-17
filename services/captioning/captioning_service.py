#  Copyright © [2024] 程序那些事
#
#  All rights reserved. This software and associated documentation files (the "Software") are provided for personal and educational use only. Commercial use of the Software is strictly prohibited unless explicit permission is obtained from the author.
#
#  Permission is hereby granted to any person to use, copy, and modify the Software for non-commercial purposes, provided that the following conditions are met:
#
#  1. The original copyright notice and this permission notice must be included in all copies or substantial portions of the Software.
#  2. Modifications, if any, must retain the original copyright information and must not imply that the modified version is an official version of the Software.
#  3. Any distribution of the Software or its modifications must retain the original copyright notice and include this permission notice.
#
#  For commercial use, including but not limited to selling, distributing, or using the Software as part of any commercial product or service, you must obtain explicit authorization from the author.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#  Author: 程序那些事
#  email: flydean@163.com
#  Website: [www.flydean.com](http://www.flydean.com)
#  GitHub: [https://github.com/ddean2009/MoneyPrinterPlus](https://github.com/ddean2009/MoneyPrinterPlus)
#
#  All rights reserved.
#
#

import json
import os
import platform
from typing import Optional
import time

from common.config.config import my_config
#from services.alinls.speech_process import AliRecognitionService
from services.audio.faster_whisper_recognition_service import FasterWhisperRecognitionService
#from services.audio.tencent_recognition_service import TencentRecognitionService
from services.captioning.common_captioning_service import Captioning
from services.captioning.caption_from_text_audio import CaptioningService, ChatTTSSegments
from services.hunjian.hunjian_service import get_session_video_scene_text,get_video_scene_text_list
from tools.utils import  get_must_session_option
import subprocess

from tools.file_utils import generate_temp_filename
import streamlit as st

from tools.utils import get_session_option

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)

font_dir = os.path.join(script_dir, '../../fonts')
font_dir = os.path.abspath(font_dir)

# windows路径需要特殊处理
if platform.system() == "Windows":
    font_dir = font_dir.replace("\\", "\\\\\\\\")
    font_dir = font_dir.replace(":", "\\\\:")

def split_by_punctuation(text: str) -> list[str]:
    """
    按标点符号分割文本
    """
    # 定义标点符号
    punctuations = ['。', '！', '？', '，', '；', '、']
    
    segments = []
    last_pos = 0
    
    for i, char in enumerate(text):
        if char in punctuations:
            segment = text[last_pos:i+1].strip()
            if segment:  # 确保不添加空段
                segments.append(segment)
            last_pos = i + 1
    
    # 处理最后一段（如果有的话）
    if last_pos < len(text):
        final_segment = text[last_pos:].strip()
        if final_segment:
            segments.append(final_segment)
    segments = [segment.rstrip(''.join(punctuations)) for segment in segments]
    return segments

def format_time(seconds: float) -> str:
    """
    将秒数转换为字幕时间格式 HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = seconds % 60
    milliseconds = int((seconds_part % 1) * 1000)
    seconds_whole = int(seconds_part)
    
    return f"{hours:02d}:{minutes:02d}:{seconds_whole:02d},{milliseconds:03d}"

def calculate_mid_time(begin_time: float, end_time: float, first_text: str, second_text: str) -> float:
    """
    根据文本长度比例计算中间时间点
    """
    total_duration = end_time - begin_time
    total_length = len(first_text) + len(second_text)
    
    # 根据文本长度比例分配时间
    first_ratio = len(first_text) / total_length
    mid_time = begin_time + (total_duration * first_ratio)
    
    # 确保每段至少有最小显示时间（例如 1秒）
    MIN_DURATION = 1.0
    if (mid_time - begin_time) < MIN_DURATION:
        mid_time = begin_time + MIN_DURATION
    elif (end_time - mid_time) < MIN_DURATION:
        mid_time = end_time - MIN_DURATION
        
    return mid_time

def process_text(text: str) -> tuple[str, str | None, bool]:
    """
    处理文本并返回适当的格式
    返回值: (处理后的文本, 第二部分文本, 是否需要分段)
    """
    # 强停顿符号（优先分割）
    primary_splits = ['。', '！', '？', '；']
    # 弱停顿符号（次优先分割）
    secondary_splits = ['，', '、', ' ']
    
    # 短文本直接返回
    if len(text) <= 10:
        return text, None, False
    
    # 寻找最佳分割点
    def find_split_point(text: str) -> int:
        # 从前向后搜索分割点
        text_len = len(text)
        target_len = text_len // 2  # 目标长度大约在中间位置
        
        # 先寻找强停顿符号
        best_position = -1
        for i in range(text_len):
            if text[i] in primary_splits:
                if i >= target_len // 2:  # 确保第一段不会太短
                    best_position = i
                    break
        
        # 如果没找到强停顿符号，寻找弱停顿符号
        if best_position == -1:
            for i in range(text_len):
                if text[i] in secondary_splits:
                    if i >= target_len // 2:
                        best_position = i
                        break
        
        # 如果都没找到，返回中点
        if best_position == -1:
            best_position = target_len
            
        return best_position
    
    # 根据文本长度决定分行还是分段
    if len(text) <= 20:  # 适中长度文本分行显示
        split_point = find_split_point(text)
        return f"{text[:split_point+1]}\n{text[split_point+1:]}", None, False
    else:  # 长文本分段显示
        split_point = find_split_point(text)
        return text[:split_point+1], text[split_point+1:], True

def generate_srt(results, output_file):
    subtitle_entries = []
    subtitle_index = 1
    
    for result in results:
        if not result.text or result.text.isspace():
            continue
        
        # 清理文本中的多余空格
        text = ' '.join(result.text.split())
        
        # 按标点符号分割
        segments = split_by_punctuation(text)
        
        if not segments:
            continue
            
        # 计算每段的时长
        total_time = result.end_time - result.begin_time
        segment_time = total_time / len(segments)
        
        # 生成每段字幕
        for i, segment in enumerate(segments):
            start_time = result.begin_time + (i * segment_time)
            end_time = start_time + segment_time
            
            entry = {
                'index': subtitle_index,
                'start': format_time(start_time),
                'end': format_time(end_time),
                'text': segment
            }
            subtitle_entries.append(entry)
            subtitle_index += 1
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in subtitle_entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['text']}\n\n")
# 生成字幕
def generate_caption(captioning_output, task_params):
    captioning = Captioning()
    captioning.initialize()
    speech_recognizer_data = captioning.speech_recognizer_from_user_config()
    # print(speech_recognizer_data)
    recognition_type = task_params.get('recognition_audio_type')
    if recognition_type == "local" or "local_enhance":
        caption_service = CaptioningService()
        video_dir_list, video_text_list = get_session_video_scene_text()
                # 读取 video_text_list 文件并将每一行内容存入列表
        with open(video_text_list[0], 'r', encoding='utf-8') as file:
            video_text_list = file.readlines()
            video_text_list = [line.strip() for line in video_text_list]  # 去除每行的换行符

        result_list = caption_service.generate_caption(get_must_session_option("audio_output_file_list","请先生成配音文件"),video_text_list)
        if result_list is None:
            return
        captioning._offline_results= result_list
        for result in captioning._offline_results:
            print(f"Text: {result.text}, Begin Time: {result.begin_time}, End Time: {result.end_time}")
        
        # 使用方法
        generate_srt(result_list, captioning_output)
        #st.session_state["captioning_output"] = captioning_output
        return  caption_service.get_results()

        

            

        """selected_audio_provider = my_config['audio'].get('local_recognition',{}).get('provider','fasterwhisper')
        if selected_audio_provider =='fasterwhisper':
            print("selected_audio_provider: fasterwhisper")
            fasterwhisper_service = FasterWhisperRecognitionService()
            result_list = fasterwhisper_service.process(get_session_option("audio_output_file"),
                                                  get_session_option("audio_language"))
            print(result_list)
            if result_list is None:
                return
            captioning._offline_results = result_list"""



# 添加字幕
def add_subtitles(video_file, subtitle_file, font_name='Songti TC Bold', font_size=12, primary_colour='#FFFFFF',
                  outline_colour='#FFFFFF', margin_v=16, margin_l=4, margin_r=4, border_style=1, outline=0, alignment=2,
                  shadow=0, spacing=2):
    output_file = generate_temp_filename(video_file)
    primary_colour = f"&H{primary_colour[1:]}&"
    outline_colour = f"&H{outline_colour[1:]}&"
    # windows路径需要特殊处理
    if platform.system() == "Windows":
        subtitle_file = subtitle_file.replace("\\", "\\\\\\\\")
        subtitle_file = subtitle_file.replace(":", "\\\\:")
    vf_text = f"subtitles={subtitle_file}:fontsdir={font_dir}:force_style='Fontname={font_name},Fontsize={font_size},Alignment={alignment},MarginV={margin_v},MarginL={margin_l},MarginR={margin_r},BorderStyle={border_style},Outline={outline},Shadow={shadow},PrimaryColour={primary_colour},OutlineColour={outline_colour},Spacing={spacing}'"
    font_file = font_name
    # 构建FFmpeg命令
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_file,  # 输入视频文件
        '-vf', vf_text,  # 输入字幕文件
        '-y',
        output_file  # 输出文件
    ]
    print(" ".join(ffmpeg_cmd))
    # 调用ffmpeg
    subprocess.run(ffmpeg_cmd, check=True)
    # 重命名最终的文件
    if os.path.exists(output_file):
        os.remove(video_file)
        os.renames(output_file, video_file)


def test_subtitle_generation():
    # 模拟语音识别结果的简单类
    class MockResult:
        def __init__(self, text, begin_time, end_time):
            self.text = text
            self.begin_time = begin_time
            self.end_time = end_time
    
    # 创建测试用例
    test_results = [
        MockResult(
            "停个车能把我急出一身汗，作为一个开了 8年车的女司机，",
            0.0,    # 开始时间
            9.083   # 结束时间
        ),
        MockResult(
            "我最讨厌的就是那种转弯半径小的停车位，今天就遇到了一个这样的车位。",
            9.083,
            15.5
        ),
        MockResult(
            "短句测试。",
            15.5,
            17.0
        ),
        MockResult(
            "这是一个非常非常长的句子用来测试分段效果，因为我们需要验证长句子是否能够正确地被分成两段并且保持合理的显示时间。",
            17.0,
            25.0
        )
    ]
    
    # 生成测试用的字幕文件
    output_file = "test_subtitles.srt"
    generate_srt(test_results, output_file)
    
    # 打印生成的文件内容
    print("生成的字幕文件内容：")
    with open(output_file, 'r', encoding='utf-8') as f:
        print(f.read())

# 运行测试
if __name__ == "__main__":
    test_subtitle_generation()
