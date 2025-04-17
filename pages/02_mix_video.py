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

import streamlit as st
import sys
import os
import zipfile
import io
import json
import asyncio
from datetime import datetime
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)



from common.config.config import transition_types, fade_list, audio_languages, audio_types, load_session_state_from_yaml, \
    save_session_state_to_yaml, app_title, GPT_soVITS_languages, my_config,\
    chattts_enhanced_style_options, chattts_enhanced_name_options, chattts_enhanced_speed_options


from main import main_generate_ai_video_for_mix, main_try_test_audio, get_audio_voices, main_try_test_local_audio
from pages.common import common_ui
from tools.tr_utils import tr
from tools.utils import get_file_map_from_dir
from worker.celery import generate_video_task
from services.hunjian.hunjian_service import get_video_content_text, get_format_video_scene_text_list
from worker.task_record_manager import TaskRecordManager
from data.data_base_manager import DatabaseManager
import time
import uuid


# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)

default_bg_music_dir = os.path.join(script_dir, "../bgmusic")
default_bg_music_dir = os.path.abspath(default_bg_music_dir)

default_chattts_dir = os.path.join(script_dir, "../chattts")
default_chattts_dir = os.path.abspath(default_chattts_dir)

load_session_state_from_yaml('02_first_visit')

def init_session_state():
    """初始化会话状态"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    if 'tasks' not in st.session_state:
        st.session_state.tasks = {}

def get_or_create_user_id():
    """获取或创建用户ID"""
    cookie_name = "user_id"
    user_id = st.experimental_get_query_params().get(cookie_name, [None])[0]
    
    if not user_id:
        # 如果URL参数中没有user_id，检查session_state
        if 'user_id' not in st.session_state:
            # 生成新的user_id
            user_id = str(uuid.uuid4())
            st.session_state.user_id = user_id
            # 将user_id添加到URL参数中
            st.experimental_set_query_params(user_id=user_id)
        else:
            user_id = st.session_state.user_id
    else:
        st.session_state.user_id = user_id
    
    return user_id

def read_scene_text_content(file_path):
    """
    读取场景文本文件内容，按行返回非空内容
    
    Args:
        file_path: 文本文件路径
        
    Returns:
        list: 非空行内容列表
    """
    if not file_path:
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 读取所有行，去除空白字符，过滤掉空行
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        st.error(f"读取文件 {file_path} 失败: {str(e)}")
        return []

def generate_video_for_mix():
    """处理视频生成请求"""
    save_session_state_to_yaml()
    init_session_state()
    
    videos_count = st.session_state.get('videos_count', 1)
           # 获取并校验 scene_number
    scene_number = st.session_state.get('scene_number')
    if scene_number is None:
        scene_number = 3  # 设置默认值
    else:
        try:
            scene_number = int(scene_number)
        except (TypeError, ValueError):
            scene_number = 3  # 设置默认值
    scene_text_1 = read_scene_text_content(st.session_state.get('video_scene_text_1', ''))
    scene_text_2 = read_scene_text_content(st.session_state.get('video_scene_text_2', ''))
    scene_text_3 = read_scene_text_content(st.session_state.get('video_scene_text_3', ''))
    # 打印调试信息
    print("Scene number in generate_video_for_mix:", scene_number)
    for i in range(videos_count):
        # 准备任务参数
        task_params = {
            'user_id': get_or_create_user_id(),
            'scene_number': scene_number,
            # 添加视频场景文件夹和文本内容
            ## 口播
            'video_scene_folder_1': st.session_state.get('video_scene_folder_1'),
            'video_scene_text_1': st.session_state.get('video_scene_text_1', '').strip(),
            'video_scene_text_1_content': scene_text_1,
            ## 脚本
            'video_scene_folder_2': st.session_state.get('video_scene_folder_2'),
            'video_scene_text_2': st.session_state.get('video_scene_text_2', '').strip(),
            'video_scene_text_2_content': scene_text_2,
            ## 结构化脚本
            'video_scene_folder_3': st.session_state.get('video_scene_folder_3'),
            'video_scene_text_3': st.session_state.get('video_scene_text_3', '').strip(),
            'video_scene_text_3_content': scene_text_3,

            'video_dir_list': st.session_state.get('video_dir_list'),
            'audio_file_list': st.session_state.get('audio_file_list'),
            'enable_subtitles': st.session_state.get('enable_subtitles', False),
            'subtitle_params': {
                'font_name': st.session_state.get('subtitle_font'),
                'font_size': st.session_state.get('subtitle_font_size', 10),
                'primary_colour': st.session_state.get('subtitle_color'),
                'outline_colour': st.session_state.get('subtitle_border_color'),
                'outline': st.session_state.get('subtitle_border_width', 2),
                'alignment': st.session_state.get('subtitle_position')
            },
            # 添加音频服务需要的参数
            'refine_text': st.session_state.get('refine_text', False),
            'audio_seed': st.session_state.get('audio_seed'),
            'audio_voice': st.session_state.get('audio_voice'),
            'recognition_audio_type': st.session_state.get('recognition_audio_type'),
            'refine_text_prompt': st.session_state.get('refine_text_prompt', ''),
            'text_seed': st.session_state.get('text_seed'),
            'audio_temperature': st.session_state.get('audio_temperature'),
            'audio_top_p': st.session_state.get('audio_top_p'),
            'audio_top_k': st.session_state.get('audio_top_k'),
            'audio_style': st.session_state.get('audio_style'),
            'use_ssml_voice': st.session_state.get('use_ssml_voice', False),
            'use_random_voice': st.session_state.get('use_random_voice', False),
            # 添加视频和音频处理参数
            'video_fps': st.session_state.get('video_fps', 30),
            'video_segment_min_length': st.session_state.get('video_segment_min_length', 5),
            'video_segment_max_length': st.session_state.get('video_segment_max_length', 15),
            'video_size': st.session_state.get('video_size', '1920x1080'),
            'enable_background_music': st.session_state.get('enable_background_music', False),
            'background_music': st.session_state.get('background_music', ''),
            'background_music_volume': st.session_state.get('background_music_volume', 0.5),
            'enable_video_transition_effect': st.session_state.get('enable_video_transition_effect', False),
            'video_transition_effect_duration': st.session_state.get('video_transition_effect_duration', 1),
            'video_transition_effect_type': st.session_state.get('video_transition_effect_type', ''),
            'video_transition_effect_value': st.session_state.get('video_transition_effect_value', ''),
            'slice_option_type': st.session_state.get('slice_option_type', 'portrait'),
            'knowledgebase_id': st.session_state.get('knowledgebase_id', ''),
            
            
            # 音频剪切参数
            'enable_audio_cut': st.session_state.get('enable_audio_cut', True),
            'audio_cut_threshold': -50,
            'audio_cut_min_silence_len': 500,
            'audio_cut_keep_silence': 0
            

       
        }

        print(task_params)
        
        task_id = str(uuid.uuid4())
        
        # 立即创建任务记录
        task_manager = TaskRecordManager()
        initial_status = {
            'status': 'PENDING',
            'progress': 0,
            'message': '等待处理...',
            'result': {},
            'user_id': st.session_state.get('user_id', '')
        }
        task_manager.update_task_status(task_id, initial_status)
        
        # 保存到session state
        if 'tasks' not in st.session_state:
            st.session_state.tasks = {}
        st.session_state.tasks[task_id] = initial_status
        
        # 异步提交任务到Celery
        task = generate_video_task.apply_async(
            args=[task_params],
            task_id=task_id,  # 使用相同的task_id
            queue='high_priority',
            countdown=0
        )

        st.success(f'已创建新的视频生成任务 (ID: {task.id[:8]}...)')

        st.experimental_rerun()

def display_tasks_status():
    """显示所有任务状态，支持筛选、分页和批量下载"""
    st.subheader("任务状态")
    
    # 初始化session state变量
    if 'task_page' not in st.session_state:
        st.session_state.task_page = 1
    if 'selected_tasks' not in st.session_state:
        st.session_state.selected_tasks = []
    
    # 创建数据库管理器
    try:
        db_manager = DatabaseManager()
    except Exception as e:
        st.error(f"数据库连接失败: {str(e)}")
        st.info("请检查数据库配置和连接状态")
        return
    
    # 筛选条件区域
    with st.expander("筛选条件", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # 获取所有配置名称
            config_names = [""] + db_manager.get_config_names()
            selected_config = st.selectbox("业务分类", options=config_names, key="filter_config_name")
        
        with filter_col2:
            # 获取所有批次ID
            batch_ids = [""] + db_manager.get_batch_ids()
            selected_batch = st.selectbox("批次ID", options=batch_ids, key="filter_batch_id")
        
        with filter_col3:
            date_range = st.date_input("时间范围", value=[], key="filter_date_range")
            
        # 应用筛选按钮
        if st.button("应用筛选", key="apply_filter"):
            st.session_state.task_page = 1  # 重置页码
            st.experimental_rerun()
    
    # 准备筛选参数
    start_date = None
    end_date = None
    if len(st.session_state.get('filter_date_range', [])) == 2:
        start_date = st.session_state.filter_date_range[0]
        end_date = st.session_state.filter_date_range[1]
    
    # 获取筛选后的任务列表
    result = db_manager.get_filtered_tasks(
        page=st.session_state.task_page,
        page_size=20,
        config_name=st.session_state.get('filter_config_name', ''),
        batch_id=st.session_state.get('filter_batch_id', ''),
        start_date=start_date,
        end_date=end_date
    )
    
    tasks = result['tasks']
    total_pages = result['total_pages']
    
    # 添加更新按钮
    col_refresh, col_select_all, col_select_all_filtered = st.columns([1, 1, 1])
    with col_refresh:
        if st.button("🔄 更新任务队列", type="primary", key="refresh_tasks"):
            st.toast("正在更新任务列表...", icon="🔄")
            st.experimental_rerun()
    
    # 获取当前页面所有成功任务的ID
    current_page_success_task_ids = [task.get('task_id', '') for task in tasks if task.get('status') == 'SUCCESS']
    
    # 一键全选当前页功能
    with col_select_all:
        if current_page_success_task_ids:
            # 检查当前页面的成功任务是否都已被选中
            all_selected = all(task_id in st.session_state.selected_tasks for task_id in current_page_success_task_ids)
            
            if st.button("🔘 " + ("取消当前页全选" if all_selected else "当前页全选"), key="select_all_button"):
                if all_selected:
                    # 取消选中当前页面的所有任务，但保留其他页面的选择
                    st.session_state.selected_tasks = [task_id for task_id in st.session_state.selected_tasks 
                                                     if task_id not in current_page_success_task_ids]
                else:
                    # 选中当前页面的所有成功任务，并保留其他页面的选择
                    new_selected_tasks = st.session_state.selected_tasks.copy()
                    for task_id in current_page_success_task_ids:
                        if task_id not in new_selected_tasks:
                            new_selected_tasks.append(task_id)
                    st.session_state.selected_tasks = new_selected_tasks
                st.experimental_rerun()
    
    # 一键全选所有筛选结果功能
    with col_select_all_filtered:
        # 获取当前筛选条件下的所有成功任务ID
        all_filtered_tasks = db_manager.get_all_filtered_success_tasks(
            config_name=st.session_state.get('filter_config_name', ''),
            batch_id=st.session_state.get('filter_batch_id', ''),
            start_date=start_date,
            end_date=end_date
        )
        
        if all_filtered_tasks:
            all_filtered_task_ids = [task['task_id'] for task in all_filtered_tasks]
            # 检查所有筛选结果是否都已被选中
            all_filtered_selected = all(task_id in st.session_state.selected_tasks for task_id in all_filtered_task_ids)
            
            if st.button("🌐 " + ("取消筛选结果全选" if all_filtered_selected else "筛选结果全选"), key="select_all_filtered_button"):
                if all_filtered_selected:
                    # 取消选中所有筛选结果，但保留其他选择
                    st.session_state.selected_tasks = [task_id for task_id in st.session_state.selected_tasks 
                                                     if task_id not in all_filtered_task_ids]
                else:
                    # 选中所有筛选结果，并保留其他选择
                    new_selected_tasks = st.session_state.selected_tasks.copy()
                    for task_id in all_filtered_task_ids:
                        if task_id not in new_selected_tasks:
                            new_selected_tasks.append(task_id)
                    st.session_state.selected_tasks = new_selected_tasks
                st.experimental_rerun()
    
    # 显示任务总数和分页信息
    st.write(f"共 {result['total']} 个任务，当前第 {result['page']}/{total_pages} 页")
    
    if not tasks:
        st.info("当前没有任务")
        return
    
    # 创建任务列表表头
    col_select, col_batch, col_index, col_status, col_config, col_time, col_action = st.columns([0.5, 1, 1, 1, 2, 2, 1])
    with col_select:
        st.write("选择")
    with col_batch:
        st.write("批次")
    with col_index:
        st.write("索引")
    with col_status:
        st.write("状态")
    with col_config:
        st.write("业务分类")
    with col_time:
        st.write("更新时间")
    with col_action:
        st.write("操作")
    
    # 显示任务列表
    selected_task_ids = st.session_state.selected_tasks.copy()  # 先复制当前已选择的任务
    current_page_selected_ids = []  # 用于存储当前页面选中的任务ID
    
    for task in tasks:
        col_select, col_batch, col_index, col_status, col_config, col_time, col_action = st.columns([0.5, 1, 1, 1, 2, 2, 1])
        
        with col_select:
            # 只有成功的任务才能选择下载
            is_success = task.get('status') == 'SUCCESS'
            if is_success:
                task_id = task.get('task_id', '')
                is_selected = st.checkbox("", key=f"select_{task_id}", value=task_id in st.session_state.selected_tasks)
                if is_selected:
                    current_page_selected_ids.append(task_id)
                elif task_id in selected_task_ids:
                    # 如果之前选中但现在取消了，从列表中移除
                    selected_task_ids.remove(task_id)
        
        with col_batch:
            batch_id = task.get('batch_id', -1)
            st.text(f"{batch_id}")
            
        with col_index:
            index_id = task.get('index_id', '')
            index_display = index_id[:8] if index_id else '-1'
            st.text(f"{index_display}")
            
        with col_status:
            status = task.get('status', 'Unknown')
            status_color = {
                'SUCCESS': 'green',
                'FAILURE': 'red',
                'PENDING': 'blue',
                'STARTED': 'orange',
                'RETRY': 'yellow'
            }.get(status, 'gray')
            st.markdown(f"<span style='color:{status_color}'>{status}</span>", unsafe_allow_html=True)
            
        with col_config:
            config_name = task.get('config_name', '')
            st.text(f"{config_name}")
            
        with col_time:
            created_at = task.get('updated_at', '')
            if created_at:
                if isinstance(created_at, datetime):
                    created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
                st.text(f"{created_at}")
            else:
                st.text("-")
        
        with col_action:
            if task.get('status') == 'SUCCESS' and task.get('result_path'):
                if st.button("下载", key=f"download_{task.get('task_id')}"):
                    video_path = task.get('result_path')
                    if os.path.exists(video_path):
                        with open(video_path, 'rb') as f:
                            file_name = os.path.basename(video_path)
                            st.download_button(
                                label="点击下载",
                                data=f,
                                file_name=file_name,
                                mime="video/mp4",
                                key=f"download_button_{task.get('task_id')}"
                            )
                    else:
                        st.error("文件不存在")
    
    # 更新选中的任务，保留其他页面的选择
    for task_id in current_page_selected_ids:
        if task_id not in selected_task_ids:
            selected_task_ids.append(task_id)
    
    st.session_state.selected_tasks = selected_task_ids
    
    # 分页控制
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.session_state.task_page > 1:
            if st.button("上一页"):
                st.session_state.task_page -= 1
                st.experimental_rerun()
    
    with col2:
        if st.session_state.task_page < total_pages:
            if st.button("下一页"):
                st.session_state.task_page += 1
                st.experimental_rerun()
    
    with col3:
        page_input = st.number_input("跳转到页", min_value=1, max_value=total_pages, value=st.session_state.task_page, step=1)
        if page_input != st.session_state.task_page:
            st.session_state.task_page = page_input
            st.experimental_rerun()
    
    # 批量下载功能
    if st.session_state.selected_tasks:  # 使用session_state中的选择，而不是当前页面的选择
        if st.button(f"批量下载选中的视频 ({len(st.session_state.selected_tasks)} 个)"):
            with st.spinner('正在打包视频文件...'):
                # 准备ZIP文件
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for task_id in st.session_state.selected_tasks:  # 使用session_state中的选择
                        # 获取任务详情
                        task_detail = db_manager.get_task_by_id(task_id)
                        if task_detail and task_detail.get('result_path'):
                            video_path = task_detail.get('result_path')
                            if os.path.exists(video_path):
                                file_name = os.path.basename(video_path)
                                st.write(f"正在添加: {file_name}")
                                zip_file.write(video_path, file_name)
                            else:
                                st.warning(f"文件不存在: {video_path}")
                
                # 重置buffer的位置到开始
                zip_buffer.seek(0)
                
                # 使用 download_button 自动触发下载
                st.download_button(
                    label="下载准备完成，如果没有自动下载请点击此处",
                    data=zip_buffer,
                    file_name="selected_videos.zip",
                    mime="application/zip",
                    key="batch_download",
                )

def scan_and_process_ready_tasks():
    """扫描并处理准备就绪的任务"""
    db_manager = DatabaseManager()
    ready_tasks = db_manager.get_ready_tasks()
    
    for task in ready_tasks:
        # 清理字段名，移除表前缀
        cleaned_task = {}
        for key, value in task.items():
            # 处理带点的字段名，只保留点后面的部分
            clean_key = key.split('.')[-1]
            cleaned_task[clean_key] = value
            
        generate_video_task.apply_async(
            kwargs={'task_id':task['task_id']},  # 使用kwargs指定参数名
            
            queue='high_priority'
        )






# 然后是原有的其他功能...
def try_test_audio():
    main_try_test_audio()


def try_test_local_audio():
    main_try_test_local_audio()


def delete_scene_for_mix(video_scene_container):
    if 'scene_number' not in st.session_state or st.session_state['scene_number'] < 1:
        return
    st.session_state['scene_number'] = st.session_state['scene_number'] - 1
    save_session_state_to_yaml()


def add_more_scene_for_mix(video_scene_container):
    if 'scene_number' in st.session_state:
        # 固定3个场景
        if st.session_state['scene_number'] < 1:
            st.session_state['scene_number'] = st.session_state['scene_number'] + 1
        else:
            st.toast(tr("Maximum number of scenes reached"), icon="⚠️")
    else:
        st.session_state['scene_number'] = 1
    save_session_state_to_yaml()


def more_scene_fragment(video_scene_container):
    with video_scene_container:
        if 'scene_number' in st.session_state:
            for k in range(st.session_state['scene_number']):
                if k == 0:
                    st.subheader(tr("上传口播txt"))
                    st.text_input(label=tr("Video Scene Text"), placeholder=tr("Please input video scene text path"),
                                  key="video_scene_text_" + str(k + 1))
                elif k == 1:
                    st.subheader(tr("上传脚本txt"))
                    st.text_input(label=tr("Video Scene Resource"),
                                  placeholder=tr("Please input video scene resource folder path"),
                                  key="video_scene_folder_" + str(k + 1))
                    st.text_input(label=tr("Video Scene Text"), placeholder=tr("Please input video scene text path"),
                                  key="video_scene_text_" + str(k + 1))
                elif k == 2:
                    st.subheader(tr("上传格式化口播txt"))
                    st.text_input(label=tr("Video Scene Text"), placeholder=tr("Please input video scene text path"),
                                  key="video_scene_text_" + str(k + 1))



common_ui()



st.markdown(f"<h1 style='text-align: center; font-weight:bold; font-family:comic sans ms; padding-top: 0rem;'> \
            {app_title}</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;padding-top: 0rem;'>视频批量混剪任务看板</h2>", unsafe_allow_html=True)
st.session_state['scene_number'] = 3

# 场景设置
# mix_video_container = st.container(border=True)
# with mix_video_container:
#     st.subheader(tr("Mix Video"))
#     video_scene_container = st.container(border=True)
#     more_scene_fragment(video_scene_container)



# # 配音区域
# captioning_container = st.container(border=True)
# with captioning_container:
#     # 配音
#     st.subheader(tr("Video Captioning"))

#     llm_columns = st.columns(4)
#     with llm_columns[0]:
#         st.selectbox(label=tr("Choose audio type"), options=audio_types, format_func=lambda x: audio_types.get(x),
#                      key="audio_type")

#     if st.session_state.get("audio_type") == "remote":
#         llm_columns = st.columns(4)
#         audio_voice = get_audio_voices()
#         with llm_columns[0]:
#             st.selectbox(label=tr("Audio language"), options=audio_languages,
#                          format_func=lambda x: audio_languages.get(x), key="audio_language")
#         with llm_columns[1]:
#             st.selectbox(label=tr("Audio voice"),
#                          options=audio_voice.get(st.session_state.get("audio_language")),
#                          format_func=lambda x: audio_voice.get(st.session_state.get("audio_language")).get(x),
#                          key="audio_voice")
#         with llm_columns[2]:
#             st.selectbox(label=tr("Audio speed"),
#                          options=["normal", "fast", "faster", "fastest", "slow", "slower", "slowest"],
#                          key="audio_speed")
#         with llm_columns[3]:
#             st.button(label=tr("Testing Audio"), type="primary", on_click=try_test_audio)
#     if st.session_state.get("audio_type") == "local":
#         selected_local_audio_tts_provider = my_config['audio'].get('local_tts', {}).get('provider', '')
#         if not selected_local_audio_tts_provider:
#             selected_local_audio_tts_provider = 'chatTTS'
#         if selected_local_audio_tts_provider == 'chatTTS':
#             llm_columns = st.columns(5)
#             with llm_columns[0]:
#                 st.checkbox(label=tr("Refine text"), key="refine_text")
#                 st.text_input(label=tr("Refine text Prompt"), placeholder=tr("[oral_2][laugh_0][break_6]"),
#                               key="refine_text_prompt")
#             with llm_columns[1]:
#                 st.slider(label=tr("Text Seed"), min_value=1, value=20, max_value=4294967295, step=1,
#                           key="text_seed")
#             with llm_columns[2]:
#                 st.slider(label=tr("Audio Temperature"), min_value=0.03, value=0.3, max_value=1.0, step=0.01,
#                           key="audio_temperature")
#             with llm_columns[3]:
#                 st.slider(label=tr("top_P"), min_value=0.1, value=0.7, max_value=0.9, step=0.1,
#                           key="audio_top_p")
#             with llm_columns[4]:
#                 st.slider(label=tr("top_K"), min_value=1, value=20, max_value=20, step=1,
#                           key="audio_top_k")

#             st.checkbox(label=tr("Use random voice"), key="use_random_voice")

#     if st.session_state.get("audio_type") == "local_enhance":
#         selected_local_audio_tts_provider = my_config['audio'].get('local_tts', {}).get('provider', '')
#         if not selected_local_audio_tts_provider:
#             selected_local_audio_tts_provider = 'ChatTTS_Enhanced'
#         if selected_local_audio_tts_provider == 'ChatTTS_Enhanced':
#             llm_columns = st.columns(7)
#             with llm_columns[0]:
#                 st.checkbox(label=tr("Refine text"), key="refine_text")
#                 st.text_input(label=tr("Refine text Prompt"), placeholder=tr("[oral_2][laugh_0][break_6]"),
#                               key="refine_text_prompt")
#             with llm_columns[1]:
#                 st.selectbox(
#                     label=tr("Choose style"), 
#                     options=list(chattts_enhanced_style_options.keys()), 
#                     format_func=lambda x: chattts_enhanced_style_options.get(x),
#                     key="audio_style"  
#                 )
#             with llm_columns[2]:
#                 st.slider(label=tr("Audio Temperature"), min_value=0.01, value=0.03, max_value=1.0, step=0.01,
#                           key="audio_temperature")
#             with llm_columns[3]:
#                 st.slider(label=tr("top_P"), min_value=0.1, value=0.7, max_value=0.9, step=0.1,
#                           key="audio_top_p")
#             with llm_columns[4]:
#                 st.slider(label=tr("top_K"), min_value=1, value=20, max_value=20, step=1,
#                           key="audio_top_k")
#             with llm_columns[5]:
#                 st.checkbox(label=tr("开启SSML增强"), key="use_ssml_voice")
#                 ###写死语速故弃用enable_audio_cut
#             with llm_columns[6]:
#                 st.checkbox(label=tr("剪气口"), key="enable_audio_cut")
                

#             st.checkbox(label=tr("Use random voice"), key="use_random_voice")

#             if st.session_state.get("use_random_voice"):
#                 llm_columns = st.columns(4)
#                 with llm_columns[0]:
#                     st.slider(label=tr("Audio Seed"), min_value=1, value=20, max_value=4294967295, step=1,
#                               key="audio_seed")
#             else:
#                 llm_columns = st.columns(4)
#                 with llm_columns[0]:
#                     #chattts_list = get_file_map_from_dir(st.session_state["default_chattts_dir"], ".pt,.txt")
#                     st.selectbox(label=tr("Audio voice"), key="audio_voice",
#                                  options=list(chattts_enhanced_name_options.keys()), format_func=lambda x: chattts_enhanced_name_options.get(x))
#         if selected_local_audio_tts_provider == 'GPTSoVITS':
#             use_reference_audio = st.checkbox(label=tr("Use reference audio"), key="use_reference_audio")
#             if use_reference_audio:
#                 llm_columns = st.columns(4)
#                 with llm_columns[0]:
#                     st.file_uploader(label=tr("Reference Audio"), type=["wav", "mp3"], accept_multiple_files=False,
#                                      key="reference_audio")
#                 with llm_columns[1]:
#                     st.text_area(label=tr("Reference Audio Text"), placeholder=tr("Input Reference Audio Text"),
#                                  key="reference_audio_text")
#                 with llm_columns[2]:
#                     st.selectbox(label=tr("Reference Audio language"), options=GPT_soVITS_languages,
#                                  format_func=lambda x: GPT_soVITS_languages.get(x),
#                                  key="reference_audio_language")
#             llm_columns = st.columns(6)
#             with llm_columns[0]:
#                 st.slider(label=tr("Audio Temperature"), min_value=0.01, value=0.3, max_value=1.0, step=0.01,
#                           key="audio_temperature")
#             with llm_columns[1]:
#                 st.slider(label=tr("top_P"), min_value=0.1, value=0.7, max_value=0.9, step=0.1,
#                           key="audio_top_p")
#             with llm_columns[2]:
#                 st.slider(label=tr("top_K"), min_value=1, value=20, max_value=20, step=1,
#                           key="audio_top_k")
#             with llm_columns[3]:
#                 st.selectbox(label=tr("Audio speed"),
#                              options=["normal", "fast", "faster", "fastest", "slow", "slower", "slowest"],
#                              key="audio_speed")
#             with llm_columns[4]:
#                 st.selectbox(label=tr("Inference Audio language"),
#                              options=GPT_soVITS_languages, format_func=lambda x: GPT_soVITS_languages.get(x),
#                              key="inference_audio_language")
#             with llm_columns[5]:
#                 st.button(label=tr("Testing Audio"), type="primary", on_click=try_test_local_audio)

#     if st.session_state.get("audio_type") == "fish_audio":
#         llm_columns = st.columns(4)
#         with llm_columns[0]:
#             st.text_input(label=tr("Reference ID"), 
#                          value="50d3336eb06943dfa7c7c6bd245413e2",
#                          key="reference_id")
#         with llm_columns[1]:
#             st.selectbox(label=tr("MP3 Bitrate"),
#                         options=[64, 128, 192],
#                         key="mp3_bitrate")
#         with llm_columns[2]:
#             st.checkbox(label=tr("Enable audio cut"), 
#                        key="enable_audio_cut")

# recognition_container = st.container(border=True)
# with recognition_container:
#     # 配音
#     st.subheader(tr("Audio recognition"))
#     llm_columns = st.columns(4)
#     with llm_columns[0]:
#         st.selectbox(label=tr("Choose recognition type"), options=audio_types, format_func=lambda x: audio_types.get(x),
#                      key="recognition_audio_type")

# # 素材处理
# slice_container = st.container(border=True)
# with slice_container:
#     st.subheader(tr("混剪素材配置"))
#     llm_columns = st.columns(4)
#     with llm_columns[0]:
#         slice_options = {"portrait": "竖屏", "landscape": "横屏","any":"都行"}
#         st.selectbox(label=tr("素材类型"), key="slice_option_type", options=slice_options,
#                      format_func=lambda x: slice_options[x])
#     with llm_columns[1]:
#         st.text_input(label=tr("知识库资源配置"),
#                                   placeholder=tr("使用的知识库ID"),
#                                   key="knowledgebase_id" )


# # 背景音乐
# bg_music_container = st.container(border=True)
# with bg_music_container:
#     # 背景音乐
#     st.subheader(tr("Video Background Music"))
#     llm_columns = st.columns(2)
#     with llm_columns[0]:
#         st.text_input(label=tr("Background Music Dir"), placeholder=tr("Input Background Music Dir"),
#                       value=default_bg_music_dir,
#                       key="background_music_dir")
        

#     with llm_columns[1]:
#         nest_columns = st.columns(3)
#         with nest_columns[0]:
#             st.checkbox(label=tr("Enable background music"), key="enable_background_music", value=True)
#         with nest_columns[1]:
#             bg_music_list = get_file_map_from_dir(st.session_state["background_music_dir"], ".mp3,.wav,.MP3")
#             st.selectbox(label=tr("Background music"), key="background_music",
#                          options=bg_music_list, format_func=lambda x: bg_music_list[x])
#         with nest_columns[2]:
#             st.slider(label=tr("Background music volume"), min_value=0.0, value=0.3, max_value=1.0, step=0.1,
#                       key="background_music_volume")

# # 视频配置
# video_container = st.container(border=True)
# with video_container:
#     st.subheader(tr("Video Config"))
#     llm_columns = st.columns(3)
#     with llm_columns[0]:
#         layout_options = {"portrait": "竖屏", "landscape": "横屏", "square": "方形"}
#         st.selectbox(label=tr("video layout"), key="video_layout", options=layout_options,
#                      format_func=lambda x: layout_options[x])
#     with llm_columns[1]:
#         st.selectbox(label=tr("video fps"), key="video_fps", options=[20, 25, 30])
#     with llm_columns[2]:
#         if st.session_state.get("video_layout") == "portrait":
#             video_size_options = {"1080x1920": "1080p", "720x1280": "720p", "480x960": "480p", "360x720": "360p",
#                                   "240x480": "240p"}
#         elif st.session_state.get("video_layout") == "landscape":
#             video_size_options = {"1920x1080": "1080p", "1280x720": "720p", "960x480": "480p", "720x360": "360p",
#                                   "480x240": "240p"}
#         else:
#             video_size_options = {"1080x1080": "1080p", "720x720": "720p", "480x480": "480p", "360x360": "360p",
#                                   "240x240": "240p"}
#         st.selectbox(label=tr("video size"), key="video_size", options=video_size_options,
#                      format_func=lambda x: video_size_options[x])
#     llm_columns = st.columns(2)
#     with llm_columns[0]:
#         st.slider(label=tr("video segment min length"), min_value=0, value=1, max_value=10, step=1,
#                   key="video_segment_min_length")
#     with llm_columns[1]:
#         st.slider(label=tr("video segment max length"), min_value=5, value=10, max_value=30, step=1,
#                   key="video_segment_max_length")
#     llm_columns = st.columns(4)
#     with llm_columns[0]:
#         st.checkbox(label=tr("Enable video Transition effect"), key="enable_video_transition_effect", value=True)
#     with llm_columns[1]:
#         st.selectbox(label=tr("video Transition effect"), key="video_transition_effect_type", options=transition_types)
#     with llm_columns[2]:
#         st.selectbox(label=tr("video Transition effect types"), key="video_transition_effect_value", options=fade_list)
#     with llm_columns[3]:
#         st.selectbox(label=tr("video Transition effect duration"), key="video_transition_effect_duration",
#                      options=["1", "2"])

# # 字幕
# subtitle_container = st.container(border=True)
# with subtitle_container:
#     st.subheader(tr("Video Subtitles"))
#     llm_columns = st.columns(4)
#     with llm_columns[0]:
#         st.checkbox(label=tr("Enable subtitles"), key="enable_subtitles", value=True)
#     with llm_columns[1]:
#         st.selectbox(label=tr("subtitle font"), key="subtitle_font",
#                      options=["Songti SC Bold",
#                               "Songti SC Black",
#                               "Songti SC Light",
#                               "STSong",
#                               "Songti SC Regular",
#                               "PingFang SC Regular",
#                               "PingFang SC Medium",
#                               "PingFang SC Semibold",
#                               "PingFang SC Light",
#                               "PingFang SC Thin",
#                               "PingFang SC Ultralight",
#                               "SourceHanSansSC-Heavy.otf",
#                               "WenYue_HouXianDaiTi_J-W4_75.otf",
#                               "WenYue_XinQingNianTi_J-W8.otf"], )
#     with llm_columns[2]:
#         st.selectbox(label=tr("subtitle font size"), key="subtitle_font_size", index=1,
#                      options=[4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24])
#     with llm_columns[3]:
#         st.selectbox(label=tr("subtitle lines"), key="captioning_lines", index=1,
#                      options=[1, 2,3,4,5])

#     llm_columns = st.columns(4)
#     with llm_columns[0]:
#         subtitle_position_options = {5: "top left",
#                                      6: "top center",
#                                      7: "top right",
#                                      9: "center left",
#                                      10: "center",
#                                      11: "center right",
#                                      1: "bottom left",
#                                      2: "bottom center",
#                                      3: "bottom right"}
#         st.selectbox(label=tr("subtitle position"), key="subtitle_position", index=7,
#                      options=subtitle_position_options, format_func=lambda x: subtitle_position_options[x])
#     with llm_columns[1]:
#         st.color_picker(label=tr("subtitle color"), key="subtitle_color", value="#FFFFFF")
#     with llm_columns[2]:
#         st.color_picker(label=tr("subtitle border color"), key="subtitle_border_color", value="#000000")
#     with llm_columns[3]:
#         st.slider(label=tr("subtitle border width"), min_value=0, value=0, max_value=4, step=1,
#                   key="subtitle_border_width")

# # 生成视频


# 在display_tasks_status()函数调用之前添加生成视频按钮
# video_generator = st.container(border=True)
# with video_generator:
#     col1, col2 = st.columns([3, 1])
#     with col1:
#         videos_count = st.number_input("生成视频数量", min_value=1, max_value=10, value=1, step=1, key="videos_count")
#     with col2:
#         if st.button(label=tr("生成视频"), type="primary", on_click=generate_video_for_mix):
#             st.success("正在生成视频...")

# 然后显示任务状态
display_tasks_status()

# st.sidebar.subheader("批量下载")
# download_all_videos()

if st.session_state.get('tasks'):
    st.markdown(
        """
        <script>
            function checkAndReload() {
                // 获取所有进度条元素
                const progressBars = document.querySelectorAll('[data-testid="stProgress"]');
                const needsReload = Array.from(progressBars).some(bar => 
                    parseFloat(bar.getAttribute('aria-valuenow')) < 100
                );
                
                if (needsReload) {
                    window.location.reload();
                }
            }
            
            // 每5秒检查一次
            setInterval(checkAndReload, 5000);
        </script>
        """,
        unsafe_allow_html=True
    )
