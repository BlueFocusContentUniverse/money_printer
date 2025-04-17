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
import random
import re
import string
import subprocess
import time
import yaml
from PIL.Image import Image
from typing import Tuple

def random_line(afile):
    lines = afile.readlines()
    return random.choice(lines)


def read_yaml(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data


def save_yaml(file_name, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True)


def is_chinese(char):
    if '\u4e00' <= char <= '\u9fff':
        return True
    else:
        return False


def split_at_first_chinese_char(s):
    for i, char in enumerate(s):
        # 检查字符是否是中文字符
        if '\u4e00' <= char <= '\u9fff':  # Unicode范围大致对应于常用中文字符
            return s[:i], s[i:]
    return s, ""  # 如果没有找到中文字符，返回原字符串和一个空字符串


def add_next_line_at_first_chinese_char(s):
    for i, char in enumerate(s):
        # 检查字符是否是中文字符
        if '\u4e00' <= char <= '\u9fff':  # Unicode范围大致对应于常用中文字符
            return s[:i] + "\n" + s[i:], max(len(s[:i]), len(s[i:]))
    return s, len(s)


def insert_newline(text):
    # 创建一个正则表达式，匹配任何标点符号
    punctuations = '[' + re.escape(string.punctuation) + ']'
    # 正则表达式匹配长度为30的字符串，后面紧跟空格或标点符号
    pattern = r'(.{30})(?=' + punctuations + r'|\s)'
    # 使用 re.sub 替换匹配的部分，在匹配到的字符串后添加换行符
    return re.sub(pattern, r'\1\n', text)

def verify_mp4_file(file_path: str) -> Tuple[bool, str]:
    """
    验证 MP4 文件是否完整可用
    返回: (是否有效, 错误信息)
    """
    if not os.path.exists(file_path):
        return False, "文件不存在"
        
    # 使用 ffprobe 检查文件完整性
    probe_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
                 '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1', 
                 file_path]
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"文件验证失败: {result.stderr}"
        if not result.stdout.strip():
            return False, "未检测到视频流"
        return True, ""
    except Exception as e:
        return False, f"验证过程出错: {str(e)}"

def generate_temp_filename(original_filepath, new_ext="", new_directory=None):
    """生成临时文件名并验证，确保文件完全生成"""
    # 获取文件的目录、文件名和扩展名
    directory, filename_with_ext = os.path.split(original_filepath)
    filename, ext = os.path.splitext(filename_with_ext)

    # 在文件名后添加 temp，但不改变扩展名
    new_filename = filename + '_temp' + ext

    # 确定新文件路径
    if new_directory:
        new_filepath = os.path.join(new_directory, new_filename)
    else:
        new_filepath = os.path.join(directory, new_filename)

    max_retries = 3
    wait_time = 2  # 等待时间（秒）

    for attempt in range(max_retries):
        try:
            if os.path.exists(new_filepath) and new_filepath.lower().endswith('.mp4'):
                # 等待文件写入完成
                time.sleep(wait_time)
                
                # 检查文件大小是否稳定
                initial_size = os.path.getsize(new_filepath)
                time.sleep(1)  # 再等待 1秒
                final_size = os.path.getsize(new_filepath)
                
                if initial_size == final_size and initial_size > 0:
                    # 文件大小稳定，进行验证
                    if verify_mp4_file(new_filepath):
                        print(f"{new_filepath} 该临时片段素材完整可用")
                        return new_filepath
                    
                print(f"警告: 临时文件 {new_filepath} 验证失败")
                try:
                    os.remove(new_filepath)
                    print(f"已删除无效的临时文件")
                except Exception as e:
                    print(f"删除临时文件失败: {str(e)}")
                
                if attempt < max_retries - 1:
                    print(f"等待后重试 (第{attempt + 1}次)")
                    time.sleep(wait_time)
            else:
                return new_filepath

        except Exception as e:
            print(f"处理临时文件时发生错误 (第{attempt + 1}次): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(wait_time)

    return new_filepath

def verify_mp4_file(filepath):
    """验证 MP4 文件是否完整可用"""
    try:
        cmd = ['ffprobe', '-v', 'error', filepath]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"验证过程发生异常: {str(e)}")
        return False


def get_file_extension(filename):
    _, ext = os.path.splitext(filename)
    # return ext[1:]  # 去掉前面的点（.）
    return ext


import requests


def download_file_from_url(url, output_path):
    """
    从给定的URL下载文件并保存到指定的输出路径。

    参数:
    url (str): 要下载的文件的URL。
    output_path (str): 保存文件的本地路径。

    返回:
    None
    """
    try:
        # 发送GET请求到URL
        response = requests.get(url, stream=True)

        # 检查请求是否成功
        if response.status_code == 200:
            # 打开一个文件以二进制写模式
            with open(output_path, 'wb') as file:
                # 使用chunk迭代数据
                for chunk in response.iter_content(chunk_size=8192):
                    # 写入文件
                    file.write(chunk)
            print(f"文件已成功下载到 {output_path}")
        else:
            print(f"请求失败，状态码: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"发生了一个错误: {e}")


def random_line_from_text_file(text_file):
    # 从文本文件中随机读取文本
    with open(text_file, 'r', encoding='utf-8') as file:
        line = random_line(file)
        return line.strip()


def read_head(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='UTF-8') as file:
            # 读取文件内容
            head = file.readline()
            return head
    else:
        return ""


# 读取第一行之后 添加一个回车，适用于第一行是文章标题的情况
def read_file_with_extra_enter(file):
    with open(file, 'r', encoding='UTF-8') as f:
        # 读取文件内容
        content = f.read()
        # 使用splitlines()将内容分割成行列表
        lines = content.splitlines()
        # 检查列表是否为空，并且只处理第一行（如果存在）
        if lines:
            # 在第一行末尾添加换行符（如果它不存在）
            if not lines[0].endswith('\n'):
                lines[0] += '\n'
        # 使用join()将行重新组合成字符串
        cleaned_content = '\n'.join(lines)
        return cleaned_content


def read_file(file):
    # 打开文件
    with open(file, 'r', encoding='UTF-8') as file:
        # 读取文件内容
        content = file.read()
        return content


def write_to_file(content, file_name):
    with open(file_name, 'w', encoding='UTF-8') as file:
        file.write(content)


def list_all_files(video_dir, extension='.mp4'):
    return_files = []
    for root, dirs, files in os.walk(video_dir):
        for file in files:
            if file.endswith(extension):
                return_files.append(os.path.join(root, file))
    return sorted(return_files)


def list_files(video_dir, extension='.mp4'):
    return_files = []
    for file in os.listdir(video_dir):
        if file.endswith(extension):
            return_files.append(os.path.join(video_dir, file))
    return sorted(return_files)


def convert_mp3_to_wav(input, output, volume=1.5):
    # 构建ffmpeg命令
    cmd = [
        'ffmpeg',
        '-i', input,
        # '-ar', '44100',
        # '-ac', '2',
        '-filter:a', f'volume={volume}',
        output
    ]
    # 运行ffmpeg命令
    subprocess.run(cmd)


def save_uploaded_file(uploaded_file, save_path):
    # 假设你已经获取了文件内容
    file_content = uploaded_file.read()
    # 将文件内容写入到服务器的文件系统中
    with open(save_path, 'wb') as f:
        f.write(file_content)


def split_text(text, min_length):
    # 首先按照。！；拆分文本
    paragraph_segments = re.split(r'[。！？；.!?;]', text)

    merged_segments = []

    for paragraph in paragraph_segments:
        if paragraph:  # 确保段落非空
            # 然后按照空格、逗号、冒号拆分段落
            sub_segments = re.split(r'[ ，：,:]+', paragraph.strip())

            # 初始化变量，用于累积片段
            current_segment = ""
            for sub_segment in sub_segments:
                # 如果当前片段加上新片段的长度小于min_length，累积片段
                if len(current_segment) + len(sub_segment) < min_length:
                    current_segment += sub_segment
                else:
                    # 否则，如果当前片段非空，将其添加到结果列表
                    if current_segment:
                        merged_segments.append(current_segment)
                    # 开始新的片段
                    current_segment = sub_segment

            # 如果最后累积的片段非空，也添加到结果列表
            if current_segment:
                merged_segments.append(current_segment)

    return merged_segments
