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

import streamlit as st

from common.config.config import my_config, audio_voices_azure, audio_voices_ali, audio_voices_tencent
#from services.audio.alitts_service import AliAudioService
##from services.audio.azure_service import AzureAudioService
from services.audio.chattts_service import ChatTTSAudioService
from services.audio.gptsovits_service import GPTSoVITSAudioService
#from services.audio.tencent_tts_service import TencentAudioService
from services.audio.chattts_enhanced_service import ChatTTSEnhancedAudioService
from services.captioning.captioning_service import generate_caption, add_subtitles
from services.hunjian.hunjian_service import concat_audio_list, get_audio_and_video_list_local,get_video_content_text,get_format_video_scene_text_list
from services.llm.azure_service import MyAzureService
from services.llm.baichuan_service import MyBaichuanService
from services.llm.baidu_qianfan_service import BaiduQianfanService
from services.llm.deepseek_service import MyDeepSeekService
from services.llm.kimi_service import MyKimiService
from services.llm.llm_provider import get_llm_provider
from services.llm.ollama_service import OllamaService
from services.llm.openai_service import MyOpenAIService
from services.llm.tongyi_service import MyTongyiService
from services.resource.pexels_service import PexelsService
from services.resource.pixabay_service import PixabayService
#from services.sd.sd_service import SDService
from services.video.merge_service import merge_get_video_list, VideoMergeService, merge_generate_subtitle
from services.video.video_service import get_audio_duration, VideoService, VideoMixService
from services.material_process.screenshot import ScreenshotHandler
from services.material_process.overlay_processor import OverlayProcessor
from services.material_process.overlay_analyzer import OverlayAnalyzer,OverlayAnalysisResult
from services.material_process.sound_effect_analyzer import SoundEffectAnalyzer,SoundEffectResult
from services.material_process.sound_effect_process import SoundEffectProcessor
from services.captioning.caption_from_text_audio import CaptioningService
from tools.tr_utils import tr
from tools.utils import random_with_system_time, get_must_session_option, extent_audio
from itertools import zip_longest
from typing import List

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)
# 音频输出目录
audio_output_dir = os.path.join(script_dir, "./work")
audio_output_dir = os.path.abspath(audio_output_dir)


def get_audio_voices():
    selected_audio_provider = my_config['audio']['provider']
    if selected_audio_provider == 'Azure':
        return audio_voices_azure
    if selected_audio_provider == 'Ali':
        return audio_voices_ali
    if selected_audio_provider == 'Tencent':
        return audio_voices_tencent


def get_resource_provider():
    resource_provider = my_config['resource']['provider']
    print("resource_provider:", resource_provider)
    if resource_provider == "pexels":
        return PexelsService()
    if resource_provider == "pixabay":
        return PixabayService()
    if resource_provider == "stableDiffusion":
        return SDService()



def get_audio_service():
    selected_audio_provider = my_config['audio']['provider']
    if selected_audio_provider == "Azure":
        return AzureAudioService()
    if selected_audio_provider == "Ali":
        return AliAudioService()
    if selected_audio_provider == "Tencent":
        return TencentAudioService()


def main_generate_video_content():
    print("main_generate_video_content begin")
    topic = get_must_session_option('video_subject', "请输入要生成的主题")
    if topic is None:
        return
    video_language = st.session_state.get('video_language')
    video_length = st.session_state.get('video_length')

    llm_provider = my_config['llm']['provider']
    print("llm_provider:", llm_provider)
    llm_service = get_llm_provider(llm_provider)
    st.session_state["video_content"] = llm_service.generate_content(topic,
                                                                     llm_service.topic_prompt_template,
                                                                     video_language,
                                                                     video_length)
    st.session_state["video_keyword"] = llm_service.generate_content(st.session_state["video_content"],
                                                                     prompt_template=llm_service.keyword_prompt_template)
    print("keyword:", st.session_state.get("video_keyword"))
    print("main_generate_video_content end")


def main_try_test_local_audio():
    print("main_try_test_local_audio begin")
    selected_local_audio_tts_provider = my_config['audio'].get('local_tts', {}).get('provider', '')
    video_content = ""
    if selected_local_audio_tts_provider == "chatTTS":
        audio_service = ChatTTSAudioService()
    if selected_local_audio_tts_provider == "GPTSoVITS":
        audio_service = GPTSoVITSAudioService()
    if selected_local_audio_tts_provider == "ChatTTS_Enhanced":
        audio_service = ChatTTSEnhancedAudioService()
    audio_service.read_with_content(video_content)
    


def main_try_test_audio():
    print("main_try_test_audio begin")
    audio_service = get_audio_service()
    audio_rate = get_audio_rate()
    audio_language = st.session_state.get("audio_language")
    if audio_language == "en-US":
        video_content = "hello,this is flydean"
    else:
        video_content = "你好，我是程序那些事"
    audio_voice = get_must_session_option("audio_voice", "请先设置配音语音")
    if audio_voice is None:
        return
    audio_service.read_with_ssml(video_content,
                                 audio_voice,
                                 audio_rate)


def main_generate_video_dubbing():
    print("main_generate_video_dubbing begin")
    video_content = get_must_session_option("video_content", "请先设置视频主题")
    if video_content is None:
        return

    temp_file_name = random_with_system_time()
    audio_output_file = os.path.join(audio_output_dir, str(temp_file_name) + ".wav")
    st.session_state["audio_output_file"] = audio_output_file

    if st.session_state.get("audio_type") == "remote":
        print("use remote audio")
        audio_service = get_audio_service()
        audio_rate = get_audio_rate()
        audio_voice = get_must_session_option("audio_voice", "请先设置配音语音")
        if audio_voice is None:
            return
        audio_service.save_with_ssml(video_content,
                                     audio_output_file,
                                     audio_voice,
                                     audio_rate)
    else:
        print("use local audio")
        selected_local_audio_tts_provider = my_config['audio'].get('local_tts', {}).get('provider', '')
        audio_service = None
        if selected_local_audio_tts_provider == "chatTTS":
            audio_service = ChatTTSAudioService()
        if selected_local_audio_tts_provider == "GPTSoVITS":
            audio_service = GPTSoVITSAudioService()
        audio_service.chat_with_content(video_content, audio_output_file)
    # 语音扩展2秒钟,防止突然结束很突兀
    extent_audio(audio_output_file, 2)
    print("main_generate_video_dubbing end")


def main_generate_video_dubbing_for_mix():
    print("main_generate_video_dubbing_for_mix begin")
    print("use local audio")
    selected_local_audio_tts_provider = my_config['audio'].get('local_tts', {}).get('provider', '')
    audio_service = None
    if selected_local_audio_tts_provider == "chatTTS":
        audio_service = ChatTTSAudioService()
    if selected_local_audio_tts_provider == "GPTSoVITS":
        audio_service = GPTSoVITSAudioService()
    if selected_local_audio_tts_provider == "ChatTTS_Enhanced":
        audio_service = ChatTTSEnhancedAudioService()
    audio_output_file_list, video_dir_list = get_audio_and_video_list_local(audio_service)
        
    st.session_state["audio_output_file_list"] = audio_output_file_list
    st.session_state["video_dir_list"] = video_dir_list
    print("main_generate_video_dubbing_for_mix end")


def get_audio_rate():
    audio_provider = my_config['audio']['provider']
    if audio_provider == "Azure":
        audio_speed = st.session_state.get("audio_speed")
        if audio_speed == "normal":
            audio_rate = "0.00"
        if audio_speed == "fast":
            audio_rate = "10.00"
        if audio_speed == "slow":
            audio_rate = "-10.00"
        if audio_speed == "faster":
            audio_rate = "20.00"
        if audio_speed == "slower":
            audio_rate = "-20.00"
        if audio_speed == "fastest":
            audio_rate = "30.00"
        if audio_speed == "slowest":
            audio_rate = "-30.00"
        return audio_rate
    if audio_provider == "Ali":
        audio_speed = st.session_state.get("audio_speed")
        if audio_speed == "normal":
            audio_rate = "0"
        if audio_speed == "fast":
            audio_rate = "150"
        if audio_speed == "slow":
            audio_rate = "-150"
        if audio_speed == "faster":
            audio_rate = "250"
        if audio_speed == "slower":
            audio_rate = "-250"
        if audio_speed == "fastest":
            audio_rate = "400"
        if audio_speed == "slowest":
            audio_rate = "-400"
        return audio_rate
    if audio_provider == "Tencent":
        audio_speed = st.session_state.get("audio_speed")
        if audio_speed == "normal":
            audio_rate = "0"
        if audio_speed == "fast":
            audio_rate = "1"
        if audio_speed == "slow":
            audio_rate = "-1"
        if audio_speed == "faster":
            audio_rate = "1.5"
        if audio_speed == "slower":
            audio_rate = "-1.5"
        if audio_speed == "fastest":
            audio_rate = "2"
        if audio_speed == "slowest":
            audio_rate = "-2"
        return audio_rate


def main_get_video_resource():
    print("main_get_video_resource begin")
    resource_service = get_resource_provider()
    query = get_must_session_option("video_keyword", "请先设置视频关键字")
    if query is None:
        return
    audio_file = get_must_session_option("audio_output_file", "请先生成配音文件")
    if audio_file is None:
        return
    audio_length = get_audio_duration(audio_file)
    print("audio_length:", audio_length)
    return_videos, total_length = resource_service.handle_video_resource(query, audio_length, 50, False)
    st.session_state["return_videos"] = return_videos
    return return_videos, audio_file


def main_generate_subtitle():
    print("main_generate_subtitle begin:")
    enable_subtitles = st.session_state.get("enable_subtitles")
    if enable_subtitles:
        # 设置输出字幕
        random_name = random_with_system_time()
        captioning_output = os.path.join(audio_output_dir, f"{random_name}.srt")
        st.session_state["captioning_output"] = captioning_output
        audio_output_file = get_must_session_option("audio_output_file", "请先生成视频对应的语音文件")
        generate_caption(captioning_output)


def main_generate_ai_video(video_generator):
    print("main_generate_ai_video begin:")
    with video_generator:
        st_area = st.status(tr("Generate Video in process..."), expanded=True)
        with st_area as status:
            st.write(tr("Generate Video Dubbing..."))
            main_generate_video_dubbing()
            st.write(tr("Generate Video subtitles..."))
            main_generate_subtitle()
            st.write(tr("Get Video Resource..."))
            main_get_video_resource()
            st.write(tr("Video normalize..."))
            audio_file = get_must_session_option("audio_output_file", "请先生成配音文件")
            if audio_file is None:
                return
            video_list = get_must_session_option("return_videos", "请先生成视频资源文件")
            if video_list is None:
                return

            video_service = VideoService(video_list, audio_file)
            print("normalize video")
            video_service.normalize_video()
            st.write(tr("Generate Video..."))
            video_file = video_service.generate_video_with_audio()
            print("final file without subtitle:", video_file)

            enable_subtitles = st.session_state.get("enable_subtitles")
            if enable_subtitles:
                st.write(tr("Add Subtitles..."))
                subtitle_file = get_must_session_option('captioning_output', "请先生成字幕文件")
                if subtitle_file is None:
                    return

                font_name = st.session_state.get('subtitle_font')
                font_size = st.session_state.get('subtitle_font_size')
                primary_colour = st.session_state.get('subtitle_color')
                outline_colour = st.session_state.get('subtitle_border_color')
                outline = st.session_state.get('subtitle_border_width')
                alignment = st.session_state.get('subtitle_position')
                add_subtitles(video_file, subtitle_file,
                              font_name=font_name,
                              font_size=font_size,
                              primary_colour=primary_colour,
                              outline_colour=outline_colour,
                              outline=outline,
                              alignment=alignment)
                print("final file with subtitle:", video_file)
            st.session_state["result_video_file"] = video_file
            status.update(label=tr("Generate Video completed!"), state="complete", expanded=False)


def main_generate_ai_video_for_mix(video_generator):
    print("main_generate_ai_video_for_mix begin:")
    with video_generator:
        st_area = st.status(tr("Generate Video in process..."), expanded=True)
        with st_area as status:
            st.write(tr("Generate Video Dubbing..."))

            #生成配音列表及srt
            main_generate_video_dubbing_for_mix()
            
            st.write(tr("Video normalize..."))
            video_dir_list = get_must_session_option("video_dir_list", "请选择视频目录路径")
            audio_file_list = get_must_session_option("audio_output_file_list", "请先生成配音文件列表")
            video_content_list = get_video_content_text()
            video_format_script = get_format_video_scene_text_list()
            print("video_dir_list:",video_dir_list)
            print("audio_file_list",audio_file_list)
            print("video_content_list",video_content_list)

            #在这里开始生成音效
            sound_analyzer = SoundEffectAnalyzer()
            sound_processor = SoundEffectProcessor()
            sound_analysis_result = None 
            sound_analysis_results: List[SoundEffectResult] = []

            formated_service = CaptioningService()
            tts_segments = formated_service.generate_caption(audio_file_list,video_format_script)
            tts_segment = None

            for format_video_scene, tts_segment in zip(video_format_script, tts_segments):
                print("开始按照标签体系处理音效----------------------- 当前处理的格式化口播稿：",format_video_scene)
                print("开始按照标签体系处理音效----------------------- 当前处理的tts：",tts_segment)

                # 获取音效信息
                sound_analysis_result = sound_analyzer.analyze(format_video_scene, tts_segment)
                sound_analysis_results.append(sound_analysis_result)
            
            processed_audio_file_list = []
            for audio_file, sound_analysis in zip(audio_file_list,sound_analysis_results):
                print("开始添加音效---------------------------------")
                processed_audio_file = sound_processor.process(audio_file,sound_analysis)
                print("处理后的音频文件：",processed_audio_file)
                processed_audio_file_list.append(processed_audio_file)
            
                audio_file_list = processed_audio_file_list


            video_mix_servie = VideoMixService()
            create_session = video_mix_servie.login_and_get_session("jin.peng@bluefocus.com", "dbe3f19da9003fb6d486b71fd177546e990e915f2639875111ef3cd3007a0564")
            # 使用 zip() 函数遍历两个列表并获得配对
            i = 0
            audio_output_file_list = []
            final_video_file_list = []
            fill_value = video_dir_list[0] if video_dir_list else None
            for video_dir, audio_file,content_text in zip_longest(video_dir_list, audio_file_list,video_content_list, fillvalue=fill_value):
                print(f"Video Directory: {video_dir}, Audio File: {audio_file}")
                if i == 0:
                    matching_videos, total_length = video_mix_servie.match_videos_from_dir(video_dir,
                                                                                           audio_file,content_text,True)
                else:
                    matching_videos, total_length = video_mix_servie.match_videos_from_dir(video_dir,
                                                                                           audio_file, content_text,False)
                i = i + 1
                audio_output_file_list.append(audio_file)
                final_video_file_list.extend(matching_videos)
            print("----------------------------------视频匹配列表",final_video_file_list)

            final_audio_output_file = concat_audio_list(audio_output_file_list)
            st.session_state['audio_output_file'] = final_audio_output_file
            st.write(tr("Generate Video subtitles..."))


        
            print("main_generate_subtitle begin:")
            enable_subtitles = st.session_state.get("enable_subtitles")
            
            
            if enable_subtitles:
                # 设置输出字幕
                random_name = random_with_system_time()
                captioning_output = os.path.join(audio_output_dir, f"{random_name}.srt")
                st.session_state["captioning_output"] = captioning_output
                audio_output_file = get_must_session_option("audio_output_file", "请先生成视频对应的语音文件")
                tts_segments = generate_caption(captioning_output)
            video_service = VideoService(final_video_file_list, final_audio_output_file)
            print("normalize video")

            normalize_video_list = video_service.normalize_video()
            st.write(tr("初始化素材处理器"))
            # 1. 初始化处理器
            screenshot_handler = ScreenshotHandler(
                screenshot_url="http://localhost:8082/screenshot",
                car_params_url="http://localhost:8082/car_params_pic",
                save_dir="screenshots"
            )
            analyzer = OverlayAnalyzer()
            analysis_result = None 
            analysis_results: List[OverlayAnalysisResult] = []

            

            processor = OverlayProcessor(video_processor=video_service)

            #获取car参数：
            analyzer.init_with_full_text(str(video_format_script)) 
            # 3. 处理每一行文本和对应视频
            processed_video_path_list = []
            video_list_info = video_service.normalize_video_list(normalize_video_list)
            for format_video_scene, tts_segment,sound_analysis_result in zip(video_format_script, tts_segments,sound_analysis_results):
                print("开始按照标签体系处理素材----------------------- 当前处理的格式化口播稿：",format_video_scene)
                print("开始按照标签体系处理素材----------------------- 当前处理的tts：",tts_segment)
                
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

            st.write(tr("Generate Video..."))
            video_file = video_service.generate_video_with_audio()
            print("final file without subtitle:", video_file)

            enable_subtitles = st.session_state.get("enable_subtitles")
            if enable_subtitles:
                st.write(tr("Add Subtitles..."))
                subtitle_file = get_must_session_option('captioning_output', "请先生成字幕文件")
                if subtitle_file is None:
                    return

                font_name = st.session_state.get('subtitle_font')
                font_size = st.session_state.get('subtitle_font_size')
                primary_colour = st.session_state.get('subtitle_color')
                outline_colour = st.session_state.get('subtitle_border_color')
                outline = st.session_state.get('subtitle_border_width')
                alignment = st.session_state.get('subtitle_position')
                add_subtitles(video_file, subtitle_file,
                              font_name=font_name,
                              font_size=font_size,
                              primary_colour=primary_colour,
                              outline_colour=outline_colour,
                              outline=outline,
                              alignment=alignment)
                print("final file with subtitle:", video_file)
            st.session_state["result_video_file"] = video_file
            status.update(label=tr("Generate Video completed!"), state="complete", expanded=False)


def main_generate_ai_video_from_img(video_generator):
    print("main_generate_ai_video_from_img begin:")
    with video_generator:
        st_area = st.status(tr("Generate Video in process..."), expanded=True)
        with st_area as status:
            sd_service = SDService()
            video_content = st.session_state.get('video_content')
            video_list, audio_list, text_list = sd_service.sd_get_video_list(video_content)
            pass

    pass


def main_generate_ai_video_for_merge(video_generator):
    print("main_generate_ai_video_for_merge begin:")
    with video_generator:
        st_area = st.status(tr("Generate Video in process..."), expanded=True)
        with st_area as status:
            video_scene_video_list, video_scene_text_list = merge_get_video_list()
            st.write(tr("Video normalize..."))
            video_service = VideoMergeService(video_scene_video_list)
            print("normalize video")
            video_scene_video_list = video_service.normalize_video()
            st.write(tr("Generate Video subtitles..."))
            merge_generate_subtitle(video_scene_video_list, video_scene_text_list)
            st.write(tr("Generate Video..."))
            video_file = video_service.generate_video_with_bg_music()
            print("final file:", video_file)

            st.session_state["result_video_file"] = video_file
            status.update(label=tr("Generate Video completed!"), state="complete", expanded=False)
