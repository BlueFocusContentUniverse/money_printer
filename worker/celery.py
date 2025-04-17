import os
import traceback
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
from celery import Celery, Task
from celery.contrib import rdb
from typing import List, Dict, Any
from datetime import datetime
#from services.audio.alitts_service import AliAudioService
#from services.audio.azure_service import AzureAudioService
from services.audio.chattts_service import ChatTTSAudioService
from services.audio.gptsovits_service import GPTSoVITSAudioService
#from services.audio.tencent_tts_service import TencentAudioService
from services.audio.chattts_enhanced_service import ChatTTSEnhancedAudioService
from services.audio.fish_audio_service import FishAudioService
from services.captioning.captioning_service import generate_caption, add_subtitles, format_time
from services.hunjian.hunjian_service import concat_audio_list, get_audio_and_video_list_local
from services.video.video_service import VideoService, VideoMixService
from services.material_process.screenshot import ScreenshotHandler
from services.material_process.overlay_processor import OverlayProcessor
from services.material_process.overlay_analyzer import OverlayAnalyzer
from services.material_process.sound_effect_analyzer import SoundEffectAnalyzer
from services.material_process.sound_effect_process import SoundEffectProcessor
from services.captioning.caption_from_text_audio import CaptioningService
from services.hunjian.hunjian_service import get_video_content_text, get_format_video_scene_text_list
from data.data_base_manager import DatabaseManager
from worker.task_record_manager import TaskRecordManager
from celery import shared_task
from filelock import FileLock
import tempfile
import shutil
import json
from data.minio_handler import MinIOHandler
from types import SimpleNamespace
from tools.utils import random_with_system_time
from itertools import zip_longest
from common.config.config import my_config
from services.audio.whisper import SpeechRecognizer
from services.audio.fish_whisper import FishSpeechRecognizer  # 导入新的识别器
from openai import OpenAI
import httpx

app = Celery('moneyprinter3')

# 从配置文件加载所有配置（包括broker和backend的URL）
app.config_from_object('worker.celeryconfig')


@shared_task(name='worker.celery.update_task_record')
def update_task_record(task_manager, task_id=None, state=None, meta=None) -> None:
    """
    异步更新任务记录
    """
    task_manager.update_task_status(task_id, state, meta)

class VideoGenerationTask(Task):
    """视频生成基础任务类"""

    def __init__(self):
        self.user_tasks = {} # 用于跟踪用户任务
        self.locks = {}  


    def get_work_dir(self):
        """获取任务专属的工作目录"""
        work_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "work", 
            str(self.request.id)
        )
        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    def get_file_lock(self, file_path):
        """获取文件锁"""
        if file_path not in self.locks:
            self.locks[file_path] = FileLock(f"{file_path}.lock")
        return self.locks[file_path]

    def cleanup_work_dir(self):
        """清理工作目录"""
        work_dir = self.get_work_dir()
        try:
            shutil.rmtree(work_dir)
            print(f"已清理工作目录: {work_dir}")
        except Exception as e:
            print(f"清理工作目录失败: {e}")

    def track_user_task(self, user_id: str, task_id: str):
        """记录用户任务"""
        if user_id not in self.user_tasks:
            self.user_tasks[user_id] = []
        self.user_tasks[user_id].append({
            'task_id': task_id,
            'start_time': datetime.now(),
            'status': 'STARTED'
        })

    def _extract_tag_from_script(self, script_text: str) -> Dict[str, str]:
        """
        从口播稿中提取最合适的标签
        Args:
            script_text: 口播稿文本
        Returns:
            包含tag_name的字典
        """
        try:
            # 读取并解析tag_mappings.json文件

            tag_mappings_path = my_config['paths']['tag_mappings_path']
            with open(tag_mappings_path, 'r', encoding='utf-8') as f:
                tag_mappings = json.load(f)
            
            # 提取所有唯一的tag_name作为可选项
            unique_tags = set()
            for _, tag_info in tag_mappings.items():
                unique_tags.add(tag_info['tag_name'])
            
            # 将集合转换为列表并排序，以便获得稳定的结果
            available_tags = sorted(list(unique_tags))
            
            # 使用OpenAI API提取最合适的标签
            print(f"从口播稿中提取标签，可用标签数量: {len(available_tags)}")
            
            # 获取配置
            api_key = my_config["llm"]["OpenAI"]["api_key"]
            base_url = my_config["llm"]["OpenAI"]["base_url"]
            proxy_host = "172.22.93.27"
            proxy_port = "1081"
            
            client = OpenAI(
                api_key=api_key, 
                base_url=base_url,
                http_client=httpx.Client(
                    proxies={
                        "http://": f"http://{proxy_host}:{proxy_port}",
                        "https://": f"http://{proxy_host}:{proxy_port}"
                    })
            )
            
            # 构造提示
            system_prompt = f"""你是汽车标签匹配专家。根据口播稿内容，从以下可选标签中选择最合适的一个：
{', '.join(available_tags)}

请直接输出标签名称，不要添加任何其他文字或标点符号。确保输出的标签名称与可选列表中的完全一致。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": script_text}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            
            extracted_tag = response.choices[0].message.content.strip()
            print(f"提取的标签: {extracted_tag}")
            
            # 验证提取的标签是否在可用标签列表中
            if extracted_tag in available_tags:
                return {
                    'tag_name': extracted_tag,
                    'tag_id': ''  # 不再需要tag_id
                }
            
            # 如果没有找到匹配的标签，返回第一个可用的标签（默认值）
            if available_tags:
                first_tag = available_tags[0]
                print(f"未找到匹配的标签")
                return {
                    'tag_name': ' ',
                    'tag_id': ''  # 不再需要tag_id
                }
            
            # 兜底方案：如果没有任何标签可用，返回空结果
            return {'tag_name': '', 'tag_id': ''}
            
        except Exception as e:
            print(f"提取标签时出错: {str(e)}")
            return {'tag_name': '', 'tag_id': ''}

    def update_state(self, task_id=None, state=None, meta=None):
        """重写update_state方法来同步更新CSV记录"""
        task_manager = TaskRecordManager() 
        if task_id is None:
            task_id = self.request.id
        if meta is None:
            meta = {}
            
        # 首先调用父类的update_state
        super().update_state(state=state, meta=meta)
        
        # 然后更新任务记录
        status_data = {
            'task_id': task_id,
            'status': state,
            'updated_at': datetime.now().isoformat(),
            **meta
        }
        
        # 确保所有数据都是可JSON序列化的
        clean_data = {
            k: v for k, v in status_data.items()
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None
        }
        
        # 更新任务状态
        task_manager.update_task_status(task_id, clean_data)

    def get_user_tasks(self, user_id: str) -> List[Dict]:
        """获取用户所有任务"""
        return self.user_tasks.get(user_id, [])
    
    def get_audio_service(self,task_params,audio_output_dir):
        """获取音频服务实例"""
        selected_audio_provider = task_params.get('audio_service')
        print(f"Selected audio provider: {selected_audio_provider}")

        if selected_audio_provider == "chatTTS":
            return ChatTTSAudioService(audio_output_dir)
        if selected_audio_provider == "GPTSoVITS":
            return GPTSoVITSAudioService(audio_output_dir)
        if selected_audio_provider == "ChatTTS_Enhanced":
            return ChatTTSEnhancedAudioService(task_params,audio_output_dir)
        if selected_audio_provider == "fish_audio":  # 添加 Fish Audio 支持
            return FishAudioService(task_params,audio_output_dir)
        return None

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败回调"""
        print(f'Task {task_id} failed: {exc}')
        self.update_state(task_id, {
            'user_id': kwargs.get('task_params', {}).get('user_id', ''),
            'status': 'FAILURE',
            'progress': 0,
            'message': f'任务失败: {str(exc)}'
        })
        
        return super().on_failure(exc, task_id, args, kwargs, einfo)
    
def get_task_params_from_db(task_id):
    """从数据库获取任务参数"""
    db_manager = DatabaseManager()
    task = db_manager.get_task_by_id(task_id)
    if task:
        return task
    return None

@app.task(bind=True, base=VideoGenerationTask)
def generate_video_task(self, task_id: str) -> Dict[str, Any]:
    """
    异步视频生成任务
    参数:
        task_params: 包含所有必要参数的字典
    返回:
        包含任务结果的字典
    """
    try:
        
        # 从数据库获取任务参数
        print("task_id:",task_id)
        task_params = get_task_params_from_db(task_id)
        print("task_params:",task_params)
        if not task_params:
            raise ValueError(f"Task {task_id} not found in database")

        # 更新任务状态
        db_manager = DatabaseManager()
        db_manager.update_task_status(task_id, 'processing')
        self.track_user_task(task_params.get('user_id'), self.request.id)

        # 更新任务状态 - 开始处理
        status_data = {
            'user_id': task_params.get('user_id'),
            'status': 'STARTED',
            'current': 0,
            'total': 100,
            'message': '任务已创建'
        }
        self.update_state(self.request.id, 'STARTED', status_data)

        # 检查tags是否为空，如果为空则从口播稿中提取
        if not task_params.get('tags'):
            print("未提供标签，尝试从口播稿中提取...")
            # 从video_scene_text_1中提取标签
            script_text = task_params.get('video_scene_text_1', '')
            if script_text:
                tag_result = self._extract_tag_from_script(script_text)
                if tag_result and tag_result['tag_name']:
                    print(f"成功从口播稿中提取标签: {tag_result['tag_name']}")
                    # 更新task_params，使用tag_name而不是tag_id
                    task_params['tags'] = tag_result['tag_name']
                    # task_params['tag_name'] = tag_result['tag_name']
                    # 同时更新数据库中的记录，只传入tag_name作为tags参数
                    db_manager.update_task_tags(task_id, tag_result['tag_name'], tag_result['tag_name'])
                else:
                    print("未能从口播稿中提取有效标签")
            else:
                print("口播稿为空，无法提取标签")

        # 提取参数
        video_dir_list = task_params.get('video_dir_list', [])
        audio_file_list = task_params.get('audio_file_list', [])
        enable_subtitles = task_params.get('enable_subtitles', False)
        scene_number = task_params.get('scene_number', 3)
        subtitle_params = task_params.get('subtitle_params', {})
        recognition_audio_type = task_params.get('recognition_audio_type')

        # 脚本所在的目录
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        audio_output_dir = os.path.join(script_dir, "work",str(self.request.id))
        
        os.makedirs(audio_output_dir, exist_ok=True)  # 确保目录存在
        audio_output_dir = os.path.abspath(audio_output_dir)

        task_params['task_resource'] = audio_output_dir

        video_content_list = task_params.get('video_scene_text_2', '').split('\n')
        video_format_script = task_params.get('video_scene_text_3', '').split('\n')

        # 获取音频服务实例
        audio_service = self.get_audio_service(task_params,audio_output_dir)
        

        # 1. 生成配音列表及srt
        # 2. 音频处理
        status_data = {
            'user_id': task_params.get('user_id'),
            'status': 'PROCESSING',
            'current': 10,
            'total': 100,
            'message': '生成音频...'
        }
        self.update_state(self.request.id, 'PROCESSING', status_data)

        audio_output_file_list, video_dir_list = get_audio_and_video_list_local(audio_service, task_params)
        print("audio_output_file_list:",audio_output_file_list)
        print("video_dir_list:",video_dir_list)
        # 初始化音效分析和处理器
        sound_analyzer = SoundEffectAnalyzer()
        sound_processor = SoundEffectProcessor()
        sound_analysis_results = []

        # 生成字幕时间轴
        formated_service = CaptioningService()
        tts_segments = formated_service.generate_caption(audio_output_file_list, video_format_script)

        # 处理每个场景的音效
        for format_video_scene, tts_segment in zip(video_format_script, tts_segments):
            sound_analysis_result = sound_analyzer.analyze(format_video_scene, tts_segment)
            sound_analysis_results.append(sound_analysis_result)

        # 3. 处理音频文件
        status_data = {
            'user_id': task_params.get('user_id'),
            'status': 'PROCESSING',
            'current': 30,
            'total': 100,
            'message': '添加音效...'
        }
        self.update_state(self.request.id, 'PROCESSING', status_data)
        # 同步更新到 task_record


        processed_audio_file_list = []
        for audio_file, sound_analysis in zip(audio_output_file_list, sound_analysis_results):
            processed_audio_file = sound_processor.process(audio_file, sound_analysis)
            processed_audio_file_list.append(processed_audio_file)
        print("processed_audio_file_list:",processed_audio_file_list)
        # 4. 视频处理
        status_data = {
            'user_id': task_params.get('user_id'),
            'status': 'PROCESSING',
            'current': 50,
            'total': 100,
            'message': '处理视频...'
        }
        self.update_state(self.request.id, 'PROCESSING', status_data)

        video_params = {
            'video_fps': task_params.get('video_fps', 30),
            'video_segment_min_length': task_params.get('video_segment_min_length', 5),
            'video_segment_max_length': task_params.get('video_segment_max_length', 15),
            'video_size': task_params.get('video_size', '1920x1080'),
            'enable_background_music': task_params.get('enable_background_music', False),
            'background_music': task_params.get('background_music', ''),
            'background_music_volume': task_params.get('background_music_volume', 0.5),
            'enable_video_transition_effect': task_params.get('enable_video_transition_effect', False),
            'video_transition_effect_duration': task_params.get('video_transition_effect_duration', 1),
            'video_transition_effect_type': task_params.get('video_transition_effect_type', ''),
            'video_transition_effect_value': task_params.get('video_transition_effect_value', ''),
            'slice_option_type': task_params.get('slice_option_type', 'portrait'),
            'knowledgebase_id': task_params.get('knowledgebase_id', ''),
            'task_resource' : audio_output_dir
        }

        # 初始化视频混合服务，传入参数
        video_mix_service = VideoMixService(task_params)
        create_session = video_mix_service.login_and_get_session("jin.peng@bluefocus.com", "dbe3f19da9003fb6d486b71fd177546e990e915f2639875111ef3cd3007a0564")
            

        # 5. 处理视频片段
        print("=== 匹配视频参数检查 ===")
        # print(f"video_dir_list 长度: {len(video_dir_list)}")
        # print(f"processed_audio_file_list 长度: {len(processed_audio_file_list)}")
        # print(f"video_content_list 长度: {len(video_content_list)}")
        final_video_file_list = []
        for i, (video_dir, audio_file, content_text) in enumerate(zip_longest(
            video_dir_list, 
            processed_audio_file_list,
            video_content_list, 
            fillvalue=video_dir_list[0] if video_dir_list else None
        )):
            print(f"\n--- 处理第 {i+1} 组数据 ---")
            print(f"video_dir: {video_dir}")
            # print(f"video_dir 是否存在: {os.path.exists(video_dir) if video_dir else False}")
            print(f"audio_file: {audio_file}")
            # print(f"audio_file 是否存在: {os.path.exists(audio_file) if audio_file else False}")
            # print(f"content_text 类型: {type(content_text)}")
            # print(f"content_text: {content_text[:200] if content_text else None}...")  # 只打印前200个字符
            
            try:
                matching_videos, total_length = video_mix_service.match_videos_from_dir(
                    video_dir,
                    audio_file,
                    content_text
                )
                print(f"匹配成功 - 获取到 {len(matching_videos)} 个视频片段，总时长: {total_length}")
                final_video_file_list.extend(matching_videos)
                
            except Exception as e:
                error_msg = f"视频匹配失败: {str(e)}\n"
                error_msg += f"参数详情:\n"
                error_msg += f"- video_dir: {video_dir}\n"
                error_msg += f"- audio_file: {audio_file}\n"
                error_msg += f"- content_text: {content_text[:100]}...\n"  # 只显示前100个字符
                print(error_msg)

        # 6. 合并音频
        status_data = {
            'user_id': task_params.get('user_id'),
            'status': 'PROCESSING',
            'current': 70,
            'total': 100,
            'message': '合并视频...'
        }
        self.update_state(self.request.id, 'PROCESSING', status_data)


        final_audio_output_file = concat_audio_list(audio_output_dir,processed_audio_file_list)


        # 8. 最终视频生成
        status_data = {
            'user_id': task_params.get('user_id'),
            'status': 'PROCESSING',
            'current': 80,
            'total': 100,
            'message': '生成最终视频...'
        }
        self.update_state(self.request.id, 'PROCESSING', status_data)


        video_service = VideoService(final_video_file_list, final_audio_output_file, video_params)
        normalize_video_list = video_service.normalize_video()

        # 初始化素材处理器
        screenshot_handler = ScreenshotHandler(
            screenshot_url="http://localhost:8187/screenshot",
            car_params_url="http://localhost:8187/car_params_pic",
            save_dir="screenshots"
        )

        analyzer = OverlayAnalyzer()
        analysis_result = None 
        analysis_results = []

        processor = OverlayProcessor(video_processor=video_service)

        #获取car参数：
        analyzer.init_with_full_text(str(video_format_script)) 
        # 3. 处理每一行文本和对应视频
        processed_video_path_list = []
        video_list_info = video_service.normalize_video_list(normalize_video_list)
        for format_video_scene, tts_segment,sound_analysis_result in zip(video_format_script, tts_segments,sound_analysis_results):
            
            analysis_result = analyzer.analyze(format_video_scene, tts_segment,sound_analysis_result)
            print("分析文本，获取贴图信息",analysis_result)
            
            if analysis_result:
                analysis_results.append(analysis_result)
            # 3.2 判断是否需要处理及时间范围
        
        for video_info in video_list_info:
            
            time_range = processor.should_process(
                analysis_results,
                video_info['start_time'],    # 使用视频实际的开始时间
                video_info['end_time'],
                video_info['duration']# 使用视频实际的结束时间
            )
            print("time_range:--------------",time_range)
            # time_range 包含:
            # - should_process: 是否需要处理
            # - start_time: 实际开始时间
            # - end_time: 实际结束时间
            
            if time_range.should_process:
                # 3.3 处理视频：归一化并添加贴图
                print("3.3 处理视频：归一化并添加贴图")
                processed_path = processor.process(
                    video_info['path'], 
                    time_range
                )
                # 处理流程：
                # 添加贴图(overlay_image_on_video)
                
                processed_video_path_list.append(os.path.abspath(processed_path))
            else :
                processed_video_path_list.append(video_info['path'])
        video_service.update_video_list(processed_video_path_list)

        # 7. 生成字幕
        

        # 合并视频
        video_file = video_service.generate_video_with_audio()
        print("final file without subtitle:", video_file)
        captioning_output = None
        if enable_subtitles:
            status_data = {
                'user_id': task_params.get('user_id'),
                'status': 'PROCESSING',
                'current': 90,
                'total': 100,
                'message': '生成字幕...'
            }
            self.update_state(self.request.id, 'PROCESSING', status_data)

            try:
                # 首先合并所有音频文件
                random_name = random_with_system_time()
                merged_audio_file = os.path.join(audio_output_dir, f"{random_name}_merged.wav")
                
                # 使用之前的concat_audio_list函数合并音频
                merged_audio_file = concat_audio_list(audio_output_dir, processed_audio_file_list)
                
                # 根据选择的服务初始化对应的识别器
                
                recognizer = FishSpeechRecognizer()
                
                
                # 使用 transcribe_video_audio 方法处理音频并获取分段结果
                simplified_segments = recognizer.transcribe_video_audio(merged_audio_file, audio_output_dir)
                
                # 生成SRT文件
                random_name = random_with_system_time()
                captioning_output = os.path.join(audio_output_dir, f"{random_name}.srt")
                
                # 将 segments 转换为字幕格式
                subtitle_entries = []
                subtitle_index = 1
                
                for segment in simplified_segments:
                    if not segment['text'] or segment['text'].isspace():
                        continue
                        
                    # 生成字幕条目
                    entry = {
                        'index': subtitle_index,
                        'start': format_time(float(segment['start'])),
                        'end': format_time(float(segment['end'])),
                        'text': segment['text']
                    }
                    subtitle_entries.append(entry)
                    subtitle_index += 1
                
                # 写入SRT文件
                with open(captioning_output, 'w', encoding='utf-8') as f:
                    for entry in subtitle_entries:
                        f.write(f"{entry['index']}\n")
                        f.write(f"{entry['start']} --> {entry['end']}\n")
                        f.write(f"{entry['text']}\n\n")

                # 添加字幕到视频
                add_subtitles(
                    video_file,
                    captioning_output,
                    font_name='文悦新青年体 (须授权)',
                    font_size=14,
                    primary_colour='#00F7FB',
                    outline_colour='#000000',
                    margin_v=120,
                    outline = 1,
                    spacing = 1
                )
                
            except Exception as e:
                print(f"生成字幕时出错: {str(e)}")
                traceback.print_exc()  # 添加这行来打印完整的错误堆栈
                # 继续处理，即使字幕生成失败

         # 检查视频文件是否成功生成
        if not video_file or not os.path.exists(video_file):
            failure_data = {
                'current': 100,
                'total': 100,
                'status': 'FAILURE',
                'message': '视频生成失败：未能生成有效的视频文件',
                'result': None
            }
            self.update_state(self.request.id, 'FAILURE', failure_data)
            db_manager.update_task_status(task_id, 'FAILURE')
            return {'status': 'FAILURE', 'error': '视频生成失败：未能生成有效的视频文件'}
        
        video_filename = os.path.basename(video_file)
       # 设置永久存储目录
        permanent_storage_dir = my_config['paths']['permanent_storage_dir']
        os.makedirs(permanent_storage_dir, exist_ok=True)
        
        
        
        # 构建新的文件名
        koc_name = task_params.get('koc_name', 'default')
        index_id = task_params.get('index_id', -1)
        batch_id = task_params.get('batch_id', -1)
        config_name = task_params.get('config_name', 'default')
        file_extension = os.path.splitext(video_filename)[1]  # 获取原文件扩展名
        new_filename = f"{batch_id}_{index_id}_{koc_name}_{config_name}_{file_extension}"
        permanent_video_path = os.path.join(permanent_storage_dir, new_filename)
        
        # 移动视频文件到永久存储位置
        shutil.move(video_file, permanent_video_path)

        # 上传视频到MinIO对象存储
        try:
            # 准备MinIO配置
            minio_config_dict = {
                "minio_config": {
                    "endpoint": my_config["minio_config"]["endpoint"],
                    "access_key": my_config["minio_config"]["access_key"],
                    "secret_key": my_config["minio_config"]["secret_key"],
                    "bucket": my_config["minio_config"]["bucket"],
                    "prefix": my_config["minio_config"]["prefix"]
                }
            }
            
            # 将字典转换为对象，以便通过点表示法访问
            minio_config = json.loads(json.dumps(minio_config_dict), object_hook=lambda d: SimpleNamespace(**d))
            
            # 初始化MinIO处理器
            minio_handler = MinIOHandler(minio_config)
            
            # 上传视频文件并获取URL
            minio_object_path = f"{new_filename}"
            success, result = minio_handler.upload_file(permanent_video_path, minio_object_path)
            
            if success:
                # 获取永久访问URL
                url_success, minio_url = minio_handler.get_public_url(minio_object_path)
                
                if url_success:
                    print(f"视频已上传到MinIO，访问URL: {minio_url}")
                    # 更新数据库中的minio_path字段
                    db_manager.update_task_status(task_id=task_id, status='SUCCESS', 
                                                result_path=permanent_video_path, 
                                                minio_path=minio_url)
                else:
                    print(f"获取MinIO URL失败: {minio_url}")
            else:
                print(f"上传视频到MinIO失败: {result}")
                
        except Exception as e:
            print(f"MinIO处理失败: {str(e)}")
            # 即使MinIO上传失败，任务仍然标记为成功，因为视频文件已经生成
 
        # 更新任务状态 - 处理完成
        success_data = {
            'current': 100,
            'total': 100,
            'status': 'SUCCESS',
            'message': '视频生成完成',
            'result': permanent_video_path
        }
        self.update_state(self.request.id, 'SUCCESS', success_data)
        
        # 注意：这里不再需要重复更新数据库，因为在上传MinIO成功后已经更新过了
        # 如果MinIO上传失败，则在这里更新数据库
        if 'minio_url' not in locals() or not url_success:
            db_manager.update_task_status(task_id=task_id, status='SUCCESS', result_path=permanent_video_path)

        return {'status': 'SUCCESS', 'result': permanent_video_path}

    except Exception as e:
        # 任务失败处理
        failure_data = {
            'status': 'FAILURE',
            'progress': 0,
            'message': str(e),
            'exc_type': type(e).__name__,
            'exc_message': str(e),
            'traceback': traceback.format_exc()
        }
        self.update_state(self.request.id, 'FAILURE', failure_data)
        db_manager.update_task_status(task_id, 'FAILURE',error_message=str(failure_data))

        return {'status': 'FAILURE', 'error': str(e)}
    
    
@app.task
def cleanup_task(task_id: str) -> bool:
    """
    清理任务产生的临时文件
    """
    try:
        # 实现清理逻辑
        return True
    except Exception as e:
        print(f"清理任务失败: {str(e)}")
        return False

# 定义任务错误处理器
@app.task
def error_handler(task_id: str, exc: Exception) -> None:
    """
    处理任务错误
    """
    print(f"Task {task_id} failed: {exc}")
    cleanup_task.delay(task_id)

@app.task(name='worker.celery.scan_and_process_ready_tasks')
def scan_and_process_ready_tasks():
    """
    扫描并处理准备就绪的任务
    """
    try:
        db_manager = DatabaseManager()
        ready_tasks = db_manager.get_ready_tasks()
        
        for task in ready_tasks:
            # 生成任务ID
            task_id = task['task_id']
            
            # 更新任务状态为处理中
            db_manager.update_task_status(task_id, 'processing')
            
            # 异步提交视频生成任务
            generate_video_task.apply_async(
                kwargs={'task_id': task_id},
                queue='high_priority'
            )
            
        return len(ready_tasks)  # 返回处理的任务数量
    except Exception as e:
        print(f"扫描任务失败: {str(e)}")
        return 0

@app.task(name='worker.celery.retry_failed_tasks')
def retry_failed_tasks(max_retry_count=3):
    """
    扫描并重试失败的任务，限制最大重试次数
    """
    try:
        db_manager = DatabaseManager()
        failed_tasks = db_manager.get_failed_tasks(max_retry_count)
        
        retried_count = 0
        for task in failed_tasks:
            # 获取任务ID
            task_id = task['task_id']
            
            # 增加重试计数
            db_manager.increment_retry_count(task_id)
            
            # 更新任务状态为准备重试
            db_manager.update_task_status(task_id, 'ready', 
                                         error_message=f"自动重试 (尝试 {task.get('retry_count', 0) + 1}/{max_retry_count})")
            
            print(f"已将失败任务 {task_id} 标记为重试状态")
            retried_count += 1
            
        return retried_count  # 返回重试的任务数量
    except Exception as e:
        print(f"重试失败任务时出错: {str(e)}")
        return 0

if __name__ == '__main__':
    app.start()