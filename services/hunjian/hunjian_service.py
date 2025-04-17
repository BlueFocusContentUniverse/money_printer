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

import os
import subprocess

import streamlit as st
from typing import Tuple, List

from tools.file_utils import random_line_from_text_file
from tools.utils import get_must_session_option, random_with_system_time, extent_audio, run_ffmpeg_command

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)



#按照scene number提取文案路径和文案完整内容
def get_session_video_scene_text(task_params):
    """
    从 task_params 获取视频场景文本和目录
    返回：(视频目录列表, 视频文本列表)
    """
    video_text_list = task_params.get('video_scene_text_1_content')
    video_dir_list = task_params.get('video_scene_folder_1')
    return video_dir_list, video_text_list

def get_video_content_text(task_params):
    """
    获取视频内容文本列表
    :param task_params: 任务参数字典
    :return: 视频内容文本列表
    """
    video_dir_list, video_text_list = get_session_video_scene_text(task_params)
    return video_text_list

def get_format_video_scene_text_list(task_params):
    """
    获取格式化的视频脚本列表
    :param task_params: 任务参数字典
    :return: 格式化的视频脚本列表
    """
    video_format_scene_text_list = []
    text_content_path = task_params.get('video_scene_text_3')
    with open(text_content_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line is not None and line != "":
                line = line.strip('"\'').strip()
                video_format_scene_text_list.append(line.strip())
    return video_format_scene_text_list



def get_video_content_text_script(task_params):
    video_dir_list, video_text_list = get_session_video_scene_text(task_params)
    text_file_for_scene = video_text_list[0]
    video_content_text = []
    if os.path.exists(text_file_for_scene):  # 检查路径是否存在以判断它是文件
        with open(text_file_for_scene, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip('"\'').strip()
                video_content_text.append(line.strip())
    else:  # 如果路径不存在，假定它是文本内容
        for line in text_file_for_scene.splitlines():
            video_content_text.append(line.strip())

    return video_content_text

#随机选取一行作为text内容，返回单行text内容和视频路径
def get_video_scene_text_list(video_text_list):
    video_scene_text_list = []
    for video_text in video_text_list:
        if video_text is not None and video_text != "":
            video_line = random_line_from_text_file(video_text)
            video_scene_text_list.append(video_line)
        else:
            video_scene_text_list.append("")
    return video_scene_text_list


def get_video_text_from_list(video_scene_text_list):
    return " ".join(video_scene_text_list)


#选取的随机文本进行配音 ==> 选取明线脚本进行配音 返回音频文件列表和视频路径
def get_audio_and_video_list_local(audio_service, task_params):
    """
    获取音频和视频列表
    :param audio_service: 音频服务
    :param task_params: 任务参数字典，包含必要的配置信息
    :return: 音频输出文件列表，视频目录列表
    """
    audio_output_file_list = []
    video_dir_list, video_text_list = get_session_video_scene_text(task_params)

    video_text_list = task_params.get('video_scene_text_1').split('\n')
    video_dir_list = task_params.get('video_scene_folder_1').split('\n')
    # print (video_text_list)
    audio_output_file_list = []
    i = 0 
    for video_text in video_text_list:
        temp_file_name = str(random_with_system_time()) + str(i)
        i = i + 1
        audio_output_file = os.path.join(audio_service.audio_output_dir, str(temp_file_name) + ".wav")
        
        audio_service.chat_with_content(video_text.strip(), audio_output_file)
        #extent_audio(audio_output_file, 0.3)
        audio_output_file_list.append(audio_output_file)

    return audio_output_file_list, video_dir_list


def get_video_text():
    video_dir_list, video_text_list = get_session_video_scene_text()
    video_scene_text_list = get_video_scene_text_list(video_text_list)
    return get_video_text_from_list(video_scene_text_list)


def concat_audio_list(audio_output_dir,audio_output_file_list):
    temp_output_file_name = os.path.join(audio_output_dir, str(random_with_system_time()) + ".wav")
    concat_audio_file = os.path.join(audio_output_dir, "concat_audio_file.txt")
    try:
        with open(concat_audio_file, 'w', encoding='utf-8') as f:
            for audio_file in audio_output_file_list:
                f.write("file '{}'\n".format(os.path.abspath(audio_file)))
        
        # 调用ffmpeg来合并音频
        # 注意：这里假设ffmpeg在你的PATH中，否则你需要提供ffmpeg的完整路径
        command = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_audio_file,
            '-c', 'copy',  # 如果可能，直接复制流而不是重新编码
            temp_output_file_name
        ]
        
        # 执行 FFmpeg 命令
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 检查命令执行结果
        if result.returncode != 0:
            error_message = result.stderr.decode().strip()
            raise Exception(f"FFmpeg command failed: {error_message}")
        
        print(f"Audio files have been merged into {temp_output_file_name}")
        return temp_output_file_name
    
    except Exception as e:
        print(f"Error concatenating audio files: {e}")
        return None
    
    finally:
        # 完成后，删除临时文件
        os.remove(concat_audio_file)