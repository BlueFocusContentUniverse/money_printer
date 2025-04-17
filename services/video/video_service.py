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

import itertools
import math
import os
import random
import re
import subprocess
from typing import List
import streamlit as st
import http.client
import json
import requests
from PIL import Image
from typing import Dict
import cv2
import math
from typing import List
from filelock import FileLock
import tempfile
import shutil
from typing import Any, Dict, Optional

from services.video.texiao_service import gen_filter
from tools.file_utils import generate_temp_filename
from tools.tr_utils import tr
from tools.utils import random_with_system_time, run_ffmpeg_command, extent_audio
from services.resource.pexels_service import PexelsService

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)
# 视频出目录
video_output_dir = os.path.join(script_dir, "../../final")
video_output_dir = os.path.abspath(video_output_dir)

# work目录
work_output_dir = os.path.join(script_dir, "../../work")
work_output_dir = os.path.abspath(work_output_dir)

DEFAULT_DURATION = 5
API_BASE = "https://ai.blue-converse.com/api"
#API_KEY = "converse-ywdzCxUH2OLL3VTB8e3L8OEIlVxMErGJCV871iAk3J4YSa2wCXkzuKMuc2xI9nOxY"


def get_audio_duration(audio_file):
    """
    获取音频文件的时长（秒）
    :param audio_file: 音频文件路径
    :return: 音频时长（秒）
    :raises: ValueError: 当无法获取音频时长时抛出，包含详细错误信息
    """
    try:
        if not os.path.exists(audio_file):
            raise ValueError(f"音频文件不存在: {audio_file}")

        # 使用ffmpeg命令获取音频信息
        cmd = ['ffmpeg', '-i', audio_file]
        print("执行命令:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True)
        stderr_output = result.stderr.decode('utf-8')

        # 解析输出，找到时长信息
        duration_search = re.search(
            r'Duration: (?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)\.(?P<milliseconds>\d+)',
            stderr_output)

        if duration_search:
            hours = int(duration_search.group('hours'))
            minutes = int(duration_search.group('minutes'))
            seconds = int(duration_search.group('seconds'))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            print(f"音频 {os.path.basename(audio_file)} 时长: {total_seconds}秒")
            return total_seconds
        else:
            error_msg = f"没有生成有效的TTS音频。文件: {audio_file}\n"
            error_msg += f"FFMPEG输出: {stderr_output}"
            raise ValueError(error_msg)

    except subprocess.SubprocessError as e:
        error_msg = f"FFMPEG处理失败。文件: {audio_file}\n错误: {str(e)}"
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"处理音频时发生未知错误。文件: {audio_file}\n错误: {str(e)}"
        raise ValueError(error_msg)


def get_video_fps(video_path):
    # ffprobe 命令，用于获取视频的帧率
    ffprobe_cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    print(" ".join(ffprobe_cmd))

    try:
        # 运行 ffprobe 命令并捕获输出
        result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)

        # 检查命令是否成功执行
        if result.returncode != 0:
            print(f"Error running ffprobe: {result.stderr}")
            return None

        # 解析输出以获取帧率
        output = result.stdout.strip()
        if '/' in output:
            numerator, denominator = map(int, output.split('/'))
            fps = float(numerator) / float(denominator)
        else:
            fps = float(output)
        print("视频fps:", fps)
        return fps
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_video_info(video_file):
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of',
               'default=noprint_wrappers=1:nokey=1', video_file]
    print(" ".join(command))
    result = subprocess.run(command, capture_output=True)

    # 解析输出以获取宽度和高度
    output = result.stdout.decode('utf-8')
    # print("output is:",output)
    width_height = output.split('\n')
    width = int(width_height[0])
    height = int(width_height[1])

    print(f'Width: {width}, Height: {height}')
    return width, height


def get_image_info(image_file):
    # 打开图片
    img = Image.open(image_file)
    # 获取图片的宽度和高度
    width, height = img.size
    print(f'Width: {width}, Height: {height}')
    return width, height

def get_video_duration_from_path(video_path: str) -> float:
    """
    获取视频时长
    Args:
        video_path: 视频路径
    Returns:
        float: 视频时长（秒）
    """
    try:
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")
            
        # 获取总帧数和帧率
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 计算时长
        duration = total_frames / fps
        
        cap.release()
        return duration
        
    except Exception as e:
        # 如果 cv2 失败，尝试使用 ffmpeg
        try:
            import subprocess
            cmd = [
                'ffprobe', 
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
            
        except Exception as e:
            raise Exception(f"获取视频时长失败: {str(e)}")
def get_video_duration(video_file):
    # 构建FFmpeg命令来获取视频时长
    command = ['ffprobe', '-i', video_file, '-show_entries', 'format=duration']
    # 执行命令并捕获输出
    print(" ".join(command))
    result = subprocess.run(command, capture_output=True)
    output = result.stdout.decode('utf-8')

    # 使用正则表达式从输出中提取时长
    duration_match = re.search(r'duration=(\d+\.\d+)', output)
    if duration_match:
        duration = float(duration_match.group(1))
        print("视频时长:", duration)
        return duration
    else:
        print(f"无法从输出中提取视频时长: {output}")
        return None


def get_video_length_list(video_list):
    video_length_list = []
    for video_file in video_list:
        length = get_video_duration(video_file)
        video_length_list.append(length)
    return video_length_list


def add_music(video_file, audio_file):
    try:
        # 验证输入文件是否存在
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"视频文件不存在: {video_file}")
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        output_file = generate_temp_filename(video_file)
        
        # 构造ffmpeg命令
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_file,
            '-i', audio_file,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            '-y',
            output_file
        ]
        
        print("执行命令:", " ".join(ffmpeg_cmd))
        
        # 执行ffmpeg命令并捕获输出
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        # 检查命令执行结果
        if result.returncode != 0:
            print("FFmpeg错误输出:", result.stderr)
            raise RuntimeError(f"FFmpeg命令执行失败: {result.stderr}")
            
        # 检查输出文件是否生成
        if not os.path.exists(output_file):
            raise RuntimeError("输出文件未生成")
            
        # 如果原文件存在，先删除
        if os.path.exists(video_file):
            os.remove(video_file)
            
        # 重命名输出文件
        os.rename(output_file, video_file)
        print("音频添加成功！")
        return video_file
        
    except Exception as e:
        print(f"添加音频时发生错误: {str(e)}")
        # 清理临时文件
        if os.path.exists(output_file):
            os.remove(output_file)
        raise



def add_background_music(video_file, audio_file, bgm_volume=0.5):
    output_file = generate_temp_filename(video_file)
    # 构建FFmpeg命令
    command = [
        'ffmpeg',
        '-i', video_file,  # 输入视频文件
        '-i', audio_file,  # 输入音频文件（背景音乐）
        '-filter_complex',
        f"[1:a]aloop=loop=0:size=100M[bgm];[bgm]volume={bgm_volume}[bgm_vol];[0:a][bgm_vol]amix=duration=first:dropout_transition=3:inputs=2[a]",
        # 在[1:a]之后添加了aloop过滤器来循环背景音乐。loop=0表示无限循环，size=200M和duration=300是可选参数，用于设置循环音频的大小或时长（这里设置得很大以确保足够长，可以根据实际需要调整），start=0表示从音频的开始处循环。
        '-map', '0:v',  # 选择视频流
        '-map', '[a]',  # 选择混合后的音频流
        '-c:v', 'copy',  # 复制视频流
        '-shortest',  # 输出时长与最短的输入流相同
        output_file  # 输出文件
    ]
    # 调用FFmpeg命令
    print(command)
    result = subprocess.run(command, capture_output=True, text=True)
    print("FFmpeg stdout:", result.stdout)
    print("FFmpeg stderr:", result.stderr)
    # 重命名最终的文件
    if os.path.exists(output_file):
        os.remove(video_file)
        os.renames(output_file, video_file)
        return video_file  # 返回处理成功的视频文件路径
    else:
        raise RuntimeError("背景音乐添加失败，输出文件未生成")


def chat_query(
    session: requests.Session,
    query: str,
    app_id: str,
    API_KEY: str,
    tags: Optional[Dict] = None,
    stream: bool = False,
    detail: bool = False
) -> Dict[str, Any]:
    """
    在session会话中发送查询请求到API
    Args:
        session: requests.Session对象
        query: 查询内容
        chat_id: 对话ID
        app_id: 应用ID
        API_KEY: API密钥
        tags: 标签信息
        files: 文件列表
        c_time: 创建时间
        data_id: 数据ID
        stream: 是否使用流式响应
        detail: 是否返回详细信息
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "variables": {
            "query": query,
            "tags": json.dumps(tags) if tags else '{"tags":{"$or":[""]}}',
        },
        "appId": app_id,
        "detail": detail,
        "stream": stream
    }

    try:
        response = session.post(
            f"{API_BASE}/v1/chat/completions",
            headers=headers,
            json=payload
        )
        print(headers,payload)
        if response.status_code != 200:
            print(f"状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            try:
                print(f"响应内容: {response.json()}")
            except:
                print(f"响应文本: {response.text}")
                
        response.raise_for_status()
        
        result = response.json()
        print("API 响应:", json.dumps(result, ensure_ascii=False, indent=2))
        return result
        
    except requests.exceptions.RequestException as e:
        error_response = {"error": str(e)}
        print("请求错误:", json.dumps(error_response, ensure_ascii=False, indent=2))
        return error_response


# services/video/video_service.py

class VideoMixService:
    def __init__(self, params):
        self.fps = params.get("video_fps", 30)
        segment_min_length = params.get("video_segment_min_length")
        self.segment_min_length = 2 if segment_min_length is None else segment_min_length
        
        segment_max_length = params.get("video_segment_max_length")
        self.segment_max_length = 15 if segment_max_length is None else segment_max_length
        self.target_width, self.target_height = map(int, params.get("video_size", "1920x1080").split('x'))
        self.enable_background_music = params.get("enable_background_music", False)
        self.background_music = params.get("background_music", "")
        self.background_music_volume = params.get("background_music_volume", 0.5)
        self.enable_video_transition_effect = params.get("enable_video_transition_effect", False)
        self.video_transition_effect_duration = params.get("video_transition_effect_duration", 1)
        self.video_transition_effect_type = params.get("video_transition_effect_type", "")
        self.video_transition_effect_value = params.get("video_transition_effect_value", "")
        self.default_duration = DEFAULT_DURATION
        self.slice_option_type = params.get("slice_option_type", "any")
        self.knowledgebase_id = params.get("knowledgebase_id", "")
        self.selected_video_tags = params.get("tags")
        self.session = requests.Session()
        if self.default_duration < self.segment_min_length:
            self.default_duration = self.segment_min_length
        self.work_dir = params.get('task_resource')
        self.lock_timeout = 60
        self.file_locks = {}
        self.chat_id = params.get("chat_id", "tiGhBShVfII1")
        self.app_id = params.get("app_id", "67b41906322c933b8d7fc5ee")
        self.API_KEY = params.get("API_KEY", "sk-1234567890")
        self.data_id = params.get("data_id", "")

    def _init_locks(self):
        """初始化文件锁"""
        self.file_locks = {}

    def _get_lock(self, file_path):
        """
        获取指定文件的锁
        如果锁不存在则创建新锁
        """
        if file_path not in self.file_locks:
            lock_file = f"{file_path}.lock"
            self.file_locks[file_path] = FileLock(lock_file, timeout=self.lock_timeout)
        return self.file_locks[file_path]
    
    def login_and_get_session(self, username, password): 
        retry_count = 0 
        max_retries = 2 
        login_url = "https://ai.blue-converse.com/api/support/user/account/loginByPassword" 
        team_switch_url = "https://ai.blue-converse.com/api/proApi/support/user/team/switch"
        login_payload = {
            "username": username,
            "password": password
        }

        team_payload = {
            "teamId": "65f407209e12313ab6e42dca"
        }

        while retry_count <= max_retries:
            try:
                # 第一步：密码登录
                response = self.session.post(login_url, json=login_payload)
                if response.status_code != 200:
                    print(f"登录失败: {response.status_code}, 正在重试 ({retry_count + 1}/{max_retries + 1})")
                    retry_count += 1
                    continue
                    
                # 获取并验证初始 token
                data = response.json()
                token = data.get('data', {}).get('token')
                if not token:
                    print(f"未找到 token, 正在重试 ({retry_count + 1}/{max_retries + 1})")
                    retry_count += 1
                    continue
                
                # 更新 session headers
                self.session.headers.update({'Cookie': f"token={token}"})
                print(f"登录成功,token:{token}")
                # 第二步：team switch
                team_response = self.session.put(team_switch_url, json=team_payload)
                if team_response.status_code != 200:
                    print(f"团队切换失败: {team_response.status_code}, 正在重试 ({retry_count + 1}/{max_retries + 1})")
                    retry_count += 1
                    continue
                    
                # 获取并验证新 token
                team_data = team_response.json()
                new_token = team_data.get('data', {}).get('token')
                if not new_token:
                    print(f"团队切换未返回 token, 正在重试 ({retry_count + 1}/{max_retries + 1})")
                    retry_count += 1
                    continue
                
                # 使用新 token 更新 session headers
                self.session.headers.update({'Cookie': f"token={new_token}"})
                print(f"登录成功 (尝试 {retry_count + 1}/{max_retries + 1})")
                return self.session
                    
            except Exception as e:
                print(f"登录过程出错: {e}, 正在重试 ({retry_count + 1}/{max_retries + 1})")
                retry_count += 1

        print("所有登录尝试均失败")
        return None

    def validate_video_orientation(self,video_path, selected_orientation):
        """验证视频方向是否符合要求"""
        try:
            # 获取视频尺寸
            width, height = get_video_info(video_path)  # 你之前写的获取视频信息函数
            # 添加空值检查
            if width is None or height is None:
                self._log(f"错误: 无法获取视频尺寸 - {video_path}")
                return False
                
            if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
                self._log(f"错误: 视频尺寸类型无效 - width: {type(width)}, height: {type(height)}")
                return False
            if selected_orientation == "portrait":
                return height > width  # 竖屏
            elif selected_orientation == "landscape":
                return width > height  # 横屏
            else:  # any
                return True
                
        except Exception as e:
            st.error(f"视频验证失败: {str(e)}")
            return False
            
    def verify_video_file(self,video_file):
        """验证视频文件是否可用"""
        if not os.path.exists(video_file):
            return False
            
        probe_cmd = ['ffprobe', '-v', 'error', video_file]
        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
        
    def fetch_videos_from_pexels(self, remaining_duration: float, query: str) -> List[str]:
        pexels_service = PexelsService()
        matching_videos = []
        total_length = 0.0
        search_limit = 5  # 设置搜索上限，可根据需要调整
        page_size = 10  # 每页返回的视频数量

        for page in range(1, search_limit + 1):
            videos, page_length = pexels_service.handle_video_resource(query, remaining_duration, page_size)

            if not videos:
                break  # 没有更多搜索结果，退出循环

            for video_path in videos:
                video_duration = get_video_duration(video_path)

                if video_duration > remaining_duration:
                    # 如果视频长度超过剩余所需时长，进行裁剪
                    trimmed_video_path = self.trim_video(video_path, remaining_duration)
                    matching_videos.append(trimmed_video_path)
                    total_length += remaining_duration
                    remaining_duration = 0
                    break
                else:
                    matching_videos.append(video_path)
                    total_length += video_duration
                    remaining_duration -= video_duration

            if remaining_duration <= 0:
                break  # 已获取足够的视频资源，退出循环

        return matching_videos
    
    def trim_video(self, video_path: str, target_duration: float) -> str:
        # 使用ffmpeg命令裁剪视频
        # 实现细节根据实际需求进行调整
        trimmed_video_path = generate_temp_filename(video_path)
        # ... 执行ffmpeg命令 ...
        video_duration = get_video_duration(video_path)
        video_width, video_height = get_video_info(video_path)
        if video_width / video_height > self.target_width / self.target_height:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-r', str(self.fps),
                '-an', 
                '-t', str(target_duration),
                '-y',
                trimmed_video_path
            ]
        # 竖屏视频
        else:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-r', str(self.fps),
                '-an', 
                '-t', str(target_duration),
                '-y',
                trimmed_video_path
            ]
        print(" ".join(cmd))
        try:
            run_ffmpeg_command(cmd)
            print(f"视频处理成功: {trimmed_video_path}")
            if not os.path.exists(trimmed_video_path):
                raise FileNotFoundError(f"Output file {trimmed_video_path} was not created")
        except Exception as e:
            print(f"处理失败: {str(e)}")
            raise
        return trimmed_video_path

    def copy_to_temp_dir(self, video_file):
        """
        将视频文件复制到临时目录
        返回临时文件路径
        """
        try:
            # 生成临时文件名
            temp_filename = f"temp_{os.path.basename(video_file)}"
            temp_path = os.path.join(self.work_dir, temp_filename)
            
            # 复制文件
            shutil.copy2(video_file, temp_path)
            return temp_path
        except Exception as e:
            print(f"复制文件到临时目录失败: {video_file}, 错误: {e}")
            return None

    def match_videos_from_dir(self, video_dir, audio_file, requirement, is_head=False):
        matching_videos = []
        # 获取音频时长
        audio_duration = get_audio_duration(audio_file)
        print("音频时长:" + str(audio_duration))
        # 发送POST请求获取视频
        
        if not self.session:
            print("无法获取会话，停止操作")
            return [], 0

        # self.session.headers.update({
        # 'Accept': 'application/json',
        # 'Content-Type': 'application/json'  # 改为 application/json 因为使用 json 参数
        # })

        # payload = {
        #     "datasetId": str(self.knowledgebase_id),
        #     "datasetMaxNum":100,
        #     "datasetSearchExtensionBg": "根据用户输入的画面要求匹配最合适的素材，品牌车型匹配为最高优先级",
        #     "datasetSearchExtensionModel": "chatgpt-4o-latest",
        #     "datasetSearchUsingExtensionQuery": True,
        #     "limit": 50000,
        #     "searchMode": "mixedRecall",
        #     "similarity": 0,
        #     "text": requirement,
        #     "usingReRank": False
        # }

        retry_count = 0
        max_retries = 2
        media_files = []
        id_list = []

        while retry_count <= max_retries:
            try:
                # 使用新的 chat_query 函数获取媒体文件
                response = chat_query(
                    session=self.session,
                    query=requirement,
                    app_id=self.app_id,
                    tags={"tags": {"$or":  self.selected_video_tags}} if self.selected_video_tags else {"tags":{"$or":[""]}},
                    API_KEY=self.API_KEY # 添加 tags 参数
                )
                
                # 从 responseData 中找到 pluginOutput 节点
                for node in response.get("responseData", []):
                    if node.get("moduleType") == "pluginOutput":
                        # 从 pluginOutput 的 list 中提取所有的 'a' 值
                        plugin_output = node.get("pluginOutput", {})
                        media_files = [item.get("a") for item in plugin_output.get("list", []) if item.get("a")]
                        if media_files:
                            print(f"找到 {len(media_files)} 个媒体文件")
                            break
                
                if media_files:
                    break
                else:
                    print(f"未找到媒体文件，正在重试 ({retry_count + 1}/{max_retries + 1})")
                    retry_count += 1
                    
            except Exception as e:
                print(f"发生错误: {e}, 正在重试 ({retry_count + 1}/{max_retries + 1})")
                retry_count += 1

        #获取返回json的a list
        #获取视频信息media_files

        total_length = 0
        i = 0
        for video_file in media_files:
            try:    # 获取文件锁
                with self._get_lock(video_file):
                    print(f"获取到文件锁: {video_file}")
                    
                    # 验证视频文件
                    if not self.verify_video_file(video_file):
                        print(f"视频文件验证失败: {video_file}")
                        continue
                    
                    if video_file in matching_videos:
                        print(f"警告: 视频文件已存在于列表中，跳过: {video_file}")
                        continue
                    if video_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        video_duration = self.default_duration
                    else:
                        # 添加视频格式验证
                        try:
                            # 添加视频格式验证
                            if not self.verify_video_file(video_file):
                                print(f"警告: 视频文件 {video_file} 无效或损坏")
                                continue
                                
                            video_duration = get_video_duration(video_file)
                            if video_duration is None:
                                print(f"无法获取视频时长: {video_file}")
                                continue

                            if not self.validate_video_orientation(video_file, self.slice_option_type):
                                print(f"警告: 视频方向不符合要求 - {video_file}")
                                print(f"预期方向: {self.slice_option_type}")
                                continue
                                
                            if video_duration < self.segment_min_length:
                                print(f"视频素材不符合最小长度要求: {video_file}")
                                print(f"当前时长: {video_duration}秒, 最小要求: {self.segment_min_length}秒")
                                continue
                                
                            if video_duration > self.segment_max_length:
                                print(f"视频时长超出最大限制,将被裁剪 - {video_file}")
                                print(f"原始时长: {video_duration}秒, 最大限制: {self.segment_max_length}秒")
                                video_duration = self.segment_max_length

                        except FileNotFoundError as e:
                            print(f"视频文件不存在: {video_file}")
                            print(f"错误详情: {str(e)}")
                            continue
                            
                        except PermissionError as e:
                            print(f"没有权限访问视频文件: {video_file}")
                            print(f"错误详情: {str(e)}")
                            continue
                            
                        except subprocess.CalledProcessError as e:
                            print(f"处理视频时发生错误: {video_file}")
                            print(f"命令返回值: {e.returncode}")
                            print(f"错误输出: {e.stderr}")
                            continue
                            
                        except Exception as e:
                            print(f"处理视频时发生未知错误: {video_file}")
                            print(f"错误类型: {type(e).__name__}")
                            print(f"错误详情: {str(e)}")
                            continue

                    print("total length:", total_length, "audio length:", audio_duration)
                    if total_length < audio_duration:
                            # 复制文件到临时目录
                        temp_path = self.copy_to_temp_dir(video_file)
                        if temp_path is None:
                            continue
                            
                        if self.enable_video_transition_effect:
                            if i == 0 and is_head:
                                total_length = total_length + video_duration
                            else:
                                total_length = total_length + video_duration - float(
                                    self.video_transition_effect_duration)
                        else:
                            total_length = total_length + video_duration
                            
                        matching_videos.append(temp_path)
                        i = i + 1
                    else:
                        extend_length = audio_duration - total_length
                        extend_length = int(math.ceil(extend_length))
                        if extend_length > 0:
                            extent_audio(audio_file, extend_length)
                        break
                            
            except TimeoutError:
                print(f"等待文件锁超时: {video_file}")
                continue
            except Exception as e:
                print(f"处理视频过程中出错: {video_file}, 错误: {e}")
                continue
            finally:
                print(f"释放文件锁: {video_file}")

            # 检查重复视频
            
        print("total length:", total_length, "audio length:", audio_duration)

        if total_length < audio_duration:
            print(f"视频总时长不足，尝试从Pexels获取额外视频资源...")
            remaining_duration = audio_duration - total_length
            query = "car"  # 替换为实际的搜索查询
            additional_videos = self.fetch_videos_from_pexels(remaining_duration, query)
            for video_path in additional_videos:
                    temp_path = self.copy_to_temp_dir(video_path)
                    if temp_path:
                        matching_videos.append(temp_path)
                        total_length += get_video_duration(temp_path)

        if total_length < audio_duration:
            st.toast(tr("You Need More Resource"), icon="⚠️")
            st.stop()
        return matching_videos, total_length
    
    def __del__(self):
        """清理资源"""
        try:
            # 添加属性存在性检查
            if hasattr(self, 'file_locks'):
                for lock in self.file_locks.values():
                    if hasattr(lock, 'is_locked') and lock.is_locked:
                        lock.release()
                    
            # 可选：清理临时文件
            if hasattr(self, 'work_dir') and self.work_dir and os.path.exists(self.work_dir):
                shutil.rmtree(self.work_dir)
        except Exception as e:
            print(f"清理资源时出错: {e}")


# services/video/video_service.py
class VideoProcessingError(Exception):
    """视频处理专用异常类"""
    pass

class VideoService:
    def __init__(self, video_list, audio_file, params):
        self.video_list = video_list
        self.audio_file = audio_file
        self.fps = params.get("video_fps", 30)
        self.seg_min_duration = params.get("video_segment_min_length", 5)
        self.seg_max_duration = params.get("video_segment_max_length", 15)
        self.target_width, self.target_height = map(int, params.get("video_size", "1920x1080").split('x'))
        self.enable_background_music = params.get("enable_background_music", False)
        self.background_music = params.get("background_music", "")
        self.background_music_volume = params.get("background_music_volume", 0.5)
        self.enable_video_transition_effect = params.get("enable_video_transition_effect", False)
        self.video_transition_effect_duration = params.get("video_transition_effect_duration", 1)
        self.video_transition_effect_type = params.get("video_transition_effect_type", "")
        self.video_transition_effect_value = params.get("video_transition_effect_value", "")
        self.default_duration = DEFAULT_DURATION
        if self.default_duration < self.seg_min_duration:
            self.default_duration = self.seg_min_duration
        self.work_dir = params.get('task_resource')
        

    def get_video_filter(self, video_width, video_height):
        """根据输入视频尺寸生成有效的滤镜参数"""
        
        # 计算缩放尺寸
        if video_width / video_height > self.target_width / self.target_height:
            # 横屏视频，按高度缩放
            scale_height = self.target_height
            scale_width = -2  # 自动计算宽度并保持比例
            vf = f"scale={scale_width}:{scale_height}"
        else:
            # 竖屏视频，按宽度缩放
            scale_width = self.target_width
            scale_height = -2  # 自动计算高度并保持比例
            vf = f"scale={scale_width}:{scale_height}"
        
        # 添加居中裁剪
        vf += f",crop={self.target_width}:{self.target_height}:'min(0,\
            (iw-{self.target_width})/2)':'min(0,(ih-{self.target_height})/2)'"
        
        return vf

    def normalize_video(self):
        return_video_list = []
        for media_file in self.video_list:
            # 如果当前文件是图片，添加转换为视频的命令
            if media_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                output_name = generate_temp_filename(media_file, ".mp4", self.work_dir)
                # 判断图片的纵横比和
                img_width, img_height = get_image_info(media_file)
                if img_width / img_height > self.target_width / self.target_height:
                    # 转换图片为视频片段 图片的视频帧率必须要跟视频的帧率一样，否则可能在最后的合并过程中导致 合并过后的视频过长
                    # ffmpeg_cmd = f"ffmpeg -loop 1 -i '{media_file}' -c:v h264 -t {self.default_duration} -r {self.fps} -vf 'scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2' -y {output_name}"
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-loop', '1',
                        '-i', media_file,
                        '-c:v', 'h264',
                        '-t', str(self.default_duration),
                        '-r', str(self.fps),
                        '-vf',
                        f'scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                        '-y', output_name]
                else:
                    # ffmpeg_cmd = f"ffmpeg -loop 1 -i '{media_file}' -c:v h264 -t {self.default_duration} -r {self.fps} -vf 'scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2' -y {output_name}"
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-loop', '1',
                        '-i', media_file,
                        '-c:v', 'h264',
                        '-t', str(self.default_duration),
                        '-r', str(self.fps),
                        '-vf',
                        f'scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                        '-y', output_name]
                print(" ".join(ffmpeg_cmd))
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                return_video_list.append(output_name)

            else:
                # 当前文件是视频文件
                print(f"检测到视频文件，准备处理...")
                video_duration = get_video_duration(media_file)
                video_width, video_height = get_video_info(media_file)
                print(f"视频信息 - 时长: {video_duration}秒, 尺寸: {video_width}x{video_height}")
                output_name = generate_temp_filename(media_file, new_directory=self.work_dir)
                if self.seg_min_duration > video_duration:
                    # 需要扩展视频
                    stretch_factor = float(self.seg_min_duration) / float(video_duration)  # 拉长比例
                    print(f"视频时长 ({video_duration}秒) 小于最小要求 ({self.seg_min_duration}秒)，需要调整...")
                    # 构建FFmpeg命令
                    if video_width / video_height > self.target_width / self.target_height:
                        command = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),
                            '-an', 
                            '-vf', 
                            f"scale='if(gt(a,{self.target_width}/{self.target_height}),{self.target_width},-1)':'if(gt(a,{self.target_width}/{self.target_height}),-1,{self.target_height})',pad={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            '-y',
                            output_name
                        ]
                    else:
                        command = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),
                            '-an', 
                            '-vf', 
                            f"scale='if(gt(a,{self.target_width}/{self.target_height}),{self.target_width},-1)':'if(gt(a,{self.target_width}/{self.target_height}),-1,{self.target_height})',pad={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            '-y',
                            output_name
                        ]
                    print(" ".join(command))
                    try:
                        run_ffmpeg_command(command)
                        print(f"视频处理成功: {output_name}")
                    except Exception as e:
                        print(f"处理失败: {str(e)}")
                        raise

                elif self.seg_max_duration < video_duration:
                    print(f"视频时长 ({video_duration}秒) 超过最大限制 ({self.seg_max_duration}秒)，将进行裁剪...")
                    if video_width / video_height > self.target_width / self.target_height:
                        cmd = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),
                            '-an', 
                            '-t', str(self.seg_max_duration),
                            '-vf',self.get_video_filter(video_width, video_height),
                            '-y',
                            output_name
                        ]
                    # 竖屏视频
                    else:
                        cmd = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),
                            '-an', 
                            '-t', str(self.seg_max_duration),
                            '-vf',self.get_video_filter(video_width, video_height),
                            '-y',
                            output_name
                        ]
                    print(" ".join(cmd))
                    try:
                        run_ffmpeg_command(cmd)
                        print(f"视频处理成功: {output_name}")
                        if not os.path.exists(output_name):
                            raise FileNotFoundError(f"Output file {output_name} was not created")
                    except Exception as e:
                        print(f"处理失败: {str(e)}")
                        raise
                else:
                    if video_width / video_height > self.target_width / self.target_height:
                        command = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),
                            '-an', 
                            '-vf', 
                            f"scale='if(gt(a,{self.target_width}/{self.target_height}),{self.target_width},-1)':'if(gt(a,{self.target_width}/{self.target_height}),-1,{self.target_height})',pad={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            '-y',
                            output_name
                        ]
                    else:
                        command = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),
                            '-an', 
                            '-vf', 
                            f"scale='if(gt(a,{self.target_width}/{self.target_height}),{self.target_width},-1)':'if(gt(a,{self.target_width}/{self.target_height}),-1,{self.target_height})',pad={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            '-y',
                            output_name
                        ]
                    print(" ".join(command))
                    try:
                        run_ffmpeg_command(command)
                        print(f"视频处理成功: {output_name}")
                    except Exception as e:
                        print(f"处理失败: {str(e)}")
                        raise
                # 重命名最终的文件
                # if os.path.exists(output_name):
                #     os.remove(media_file)
                #     os.renames(output_name, media_file)
                return_video_list.append(output_name)
        self.video_list = return_video_list
        return return_video_list

    def generate_video_with_audio(self):
        try: 
            print("\n=== 开始生成最终视频 ===")

                        # 1. 准备阶段
            try:
                if self.work_dir is None:
                    raise ValueError("work_dir 未设置")
                    
                if not isinstance(self.work_dir, (str, bytes)):
                    raise TypeError(f"work_dir 类型错误，期望 str 或 bytes，实际是 {type(self.work_dir)}")
                
                random_name = str(random_with_system_time())
                try:
                    merge_video = os.path.join(self.work_dir, f"final-{random_name}.mp4")
                except Exception as path_error:
                    raise ValueError(f"构建 merge_video 路径失败: {str(path_error)}")
                    
                try:
                    temp_video_filelist_path = os.path.join(self.work_dir, 'generate_video_with_audio_file_list.txt')
                except Exception as path_error:
                    raise ValueError(f"构建 temp_video_filelist_path 路径失败: {str(path_error)}")

                
                print(f"输出文件: {merge_video}")
            except Exception as e:
                # 不要返回 None，而是抛出异常
                raise VideoProcessingError(f"准备阶段失败: {str(e)}")
            
            # 2. 视频文件验证
            print("\n[1/5] 验证视频文件...")
            if not self._validate_video_files(temp_video_filelist_path):
                raise VideoProcessingError("视频文件验证失败")
                
            # 3. 视频拼接
            print("\n[2/5] 执行视频拼接...")
            if not self._concat_videos(temp_video_filelist_path, merge_video):
                raise VideoProcessingError("视频拼接失败")
                
            # 4. 转场效果处理
            if self.enable_video_transition_effect and len(self.video_list) > 1:
                print("\n[3/5] 添加转场效果...")
                if not self._apply_transition_effects(merge_video):
                    raise VideoProcessingError("添加转场效果失败")
            else:
                print("\n[3/5] 跳过转场效果...")
                
            # 5. 添加主音频
            print("\n[4/5] 添加主音频...")
            if not self._add_main_audio(merge_video):
                raise VideoProcessingError("添加主音频失败")
            
            # 6. 添加背景音乐
            if self.enable_background_music:
                print("\n[5/5] 添加背景音乐...")
                if not self._add_background_music(merge_video):
                    raise VideoProcessingError("添加背景音乐失败")
            else:
                print("\n[5/5] 跳过背景音乐...")
                
            # 清理临时文件
            try:
                self._cleanup_temp_files(temp_video_filelist_path)
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")
                
            # 最终检查
            if os.path.exists(merge_video):
                print(f"\n=== 视频生成完成 ===")
                print(f"最终文件: {merge_video}")
                print(f"文件大小: {os.path.getsize(merge_video) / (1024*1024):.2f} MB")
                return merge_video
            else:
                raise VideoProcessingError("最终视频文件不存在")
                
        except Exception as e:
            print("视频生成过程中发生错误")
            # 重要：必须抛出异常，而不是返回 None
            raise VideoProcessingError(f"视频生成失败: {str(e)}")
        
    def _validate_video_files(self, temp_video_filelist_path):
        """验证所有视频文件"""
        try:
        # 创建文件列表
            with open(temp_video_filelist_path, 'w') as f:
                for video_file in self.video_list:
                    f.write(f"file '{video_file}'\n")

        # 验证文件
            with open(temp_video_filelist_path, 'r') as f:
                video_files = [line.strip().split("'")[1] for line in f.readlines() if "file" in line]
            
            print(f"待处理视频数量: {len(video_files)}")
            
            for idx, video_file in enumerate(video_files, 1):
                print(f"验证文件 [{idx}/{len(video_files)}]: {video_file}")
                
                if not os.path.exists(video_file):
                    print(f"错误: 文件不存在")
                    return False
                    
                try:
                    probe_cmd = ['ffprobe', '-v', 'error', video_file]
                    result = subprocess.run(probe_cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"错误: 文件格式无效")
                        print(f"错误信息: {result.stderr}")
                        print(f"标准输出: {result.stdout}")
                        return False
                except Exception as e:
                    print(f"验证失败: {str(e)}")
                    return False
                    
            return True
    
        except Exception as e:
            print(f"文件验证过程发生错误: {str(e)}")
            return False
    def _concat_videos(self, temp_video_filelist_path, merge_video):
        """执行视频拼接"""
        try:
            ffmpeg_concat_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_video_filelist_path,
            '-c', 'copy',
            '-fflags', '+genpts',
            '-y',
            merge_video
            ]

            print("执行拼接命令...")
            process = subprocess.Popen(
                ffmpeg_concat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
    
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            
            if process.returncode == 0:
                return True
            else:
                print("拼接失败")
                return False
        
        except Exception as e:
            print(f"拼接过程发生错误: {str(e)}")
            return False
    def _apply_transition_effects(self, video_file):
        """添加转场效果"""
        try:
            video_length_list = get_video_length_list(self.video_list)
            zhuanchang_txt = gen_filter(
            video_length_list,
            None,
            None,
            self.video_transition_effect_type,
            self.video_transition_effect_value,
            self.video_transition_effect_duration,
            False
            )
            files_input = [['-i', f] for f in self.video_list]
            ffmpeg_cmd = ['ffmpeg', 
                        *itertools.chain(*files_input),
                        '-filter_complex', zhuanchang_txt,
                        '-map', '[video]',
                        '-y',
                        video_file]
                        
            print("应用转场效果...")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"添加转场效果时发生错误: {str(e)}")
            return False
    def _add_main_audio(self, video_file):
        """添加主音频"""
        try:
            print(f"添加主音频: {self.audio_file}")

            
            # 验证输入文件
            if not os.path.exists(video_file):
                print(f"错误: 视频文件不存在: {video_file}")
                return None
                
            if not os.path.exists(self.audio_file):
                print(f"错误: 音频文件不存在: {self.audio_file}")
                return None
                
            # 验证文件大小
            if os.path.getsize(video_file) == 0:
                print(f"错误: 视频文件大小为0: {video_file}")
                return None
                
            if os.path.getsize(self.audio_file) == 0:
                print(f"错误: 音频文件大小为0: {self.audio_file}")
                return None
            
            # 添加音频
            result = add_music(video_file, self.audio_file)
            if result is None:
                print("添加音频失败")
                return None
                
            # 验证输出文件
            if not os.path.exists(result):
                print(f"错误: 输出文件不存在: {result}")
                return None
                
            return result
            
        except Exception as e:
            print(f"添加主音频时发生错误: {str(e)}")
            print(f"错误类型: {type(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return None


    def _add_background_music(self, video_file):
        """添加背景音乐"""
        try:
            print(f"添加背景音乐: {self.background_music}")
            return add_background_music(
            video_file,
            self.background_music,
            self.background_music_volume
            )
        
        except Exception as e:
            print(f"添加背景音乐时发生错误: {str(e)}")
            return False

    def _cleanup_temp_files(self, *files):
        """清理临时文件"""
        for file in files:
            try:
                if os.path.exists(file):
                    os.remove(file)
                print(f"已删除临时文件: {file}")
            except Exception as e:
                print(f"删除临时文件失败: {file}, 错误: {str(e)}")

    def update_video_list(self,video_path_list):
        self.video_list = video_path_list
    
    def normalize_video_list(self, video_list: List[str]) -> List[Dict]:
        """
        处理视频列表，生成带有连续时间信息的字典列表
        Args:
            video_list: List[str] 视频路径列表
        Returns:
            List[Dict]: 包含视频信息的字典列表
            {
                'path': str,
                'start_time': float,
                'end_time': float,
                'duration': float
            }
        """
        normalized_list = []
        current_time = 0.0  # 时间累计器
        
        for video_path in video_list:
            # 获取视频时长
            duration = get_video_duration_from_path(video_path)
            # 处理视频
            
            
            # 添加视频信息
            video_info = {
                'path': video_path,
                'start_time': current_time,
                'end_time': current_time + duration,
                'duration': duration
            }
            normalized_list.append(video_info)
            
            # 更新下一个视频的开始时间
            current_time += duration

        return normalized_list

       