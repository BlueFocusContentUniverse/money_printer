import datetime
import lzma
import os
import zipfile
from io import BytesIO
import io
import base64
import struct
from openai import OpenAI
import yaml
from pydub import AudioSegment
from pathlib import Path
import datetime

import numpy as np
import requests
import torch
from pydub import AudioSegment
from pydub.playback import play

from common.config.config import my_config
from tools.file_utils import read_file, convert_mp3_to_wav
from tools.utils import must_have_value, random_with_system_time
from .tts_audio_editor import AudioCutConfig,TTSAudioCutter
import streamlit as st
import pybase16384 as b14

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)


# 读取配置文件
with open('common/config/config.yml', 'r') as file:
    config = yaml.safe_load(file)
# 从环境变量中读取 API Key 和 Base URL
os.environ['OPENAI_API_KEY'] = config['llm']['OpenAI']['api_key']
os.environ['OPENAI_API_BASE_URL'] = config['llm']['OpenAI']['base_url']

api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_API_BASE_URL")


def encode_spk_emb(spk_emb: torch.Tensor) -> str:
    arr: np.ndarray = spk_emb.to(dtype=torch.float16, device="cpu").detach().numpy()
    s = b14.encode_to_string(
        lzma.compress(
            arr.tobytes(),
            format=lzma.FORMAT_RAW,
            filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME}],
        ),
    )
    del arr
    return s

def complete_wav(audio_data):
    WAV_HEADER_LENGTH = 44
    
    # 获取音频数据总长度
    total_audio_length = len(audio_data)
    
    # 提取 WAV 头部
    wav_header = audio_data[:WAV_HEADER_LENGTH]
    
    # PCM 数据长度 (总长度减去头部长度)
    pcm_length = total_audio_length - WAV_HEADER_LENGTH
    
    # 文件长度 (总长度 - 8)
    file_length = pcm_length + WAV_HEADER_LENGTH - 8
    
    # 创建新的头部
    new_header = bytearray(wav_header)
    
    # 修改文件长度（第 4-8 字节）- 小端序
    struct.pack_into('<I', new_header, 4, file_length)
    
    # 修改数据长度（第 40-44 字节）- 小端序
    struct.pack_into('<I', new_header, 40, pcm_length)
    
    return bytes(new_header) + audio_data[WAV_HEADER_LENGTH:]

class ChatTTSEnhancedAudioService:
    def __init__(self, task_params=None, audio_output_dir = None):
        """初始化ChatTTS增强服务
        :param task_params: 任务参数字典，包含所有配置参数
        """
        if task_params is None:
            task_params = {}
            
        # 从配置文件获取服务地址
        self.service_location = my_config['audio']['local_tts']['ChatTTS_Enhanced']['server_location']
        must_have_value(self.service_location, "请设置ChatTTS 增强版 server location")
        self.service_location = self.service_location + '/v1/text:synthesize'
        
        # 从task_params获取所有参数
        self.skip_refine_text = not task_params.get('refine_text', False)
        self.refine_text_prompt = task_params.get('refine_text_prompt', '')
        
        # 音频生成相关参数
        self.text_seed = task_params.get('text_seed',42)
        self.audio_temperature = task_params.get('audio_temperature')
        self.audio_top_p = task_params.get('audio_top_p',0.7)
        self.audio_top_k = task_params.get('audio_top_k',20)
        self.audio_style = task_params.get('audio_style')
        self.use_ssml = False
        self.audio_output_dir = audio_output_dir
        
        # 音频剪切相关参数
        self.enable_audio_cut = task_params.get('enable_audio_cut', True)
        if self.enable_audio_cut:
            self.audio_cut_config = AudioCutConfig(
                threshold=task_params.get('audio_cut_threshold', -50),
                min_silence_len=task_params.get('audio_cut_min_silence_len', 500),
                keep_silence=task_params.get('audio_cut_keep_silence', 0)
            )
            self.audio_cutter = TTSAudioCutter(self.audio_cut_config)
        
        # 音频速度设置
        # audio_speed_map = {
        #     "normal": 5,
        #     "fast": 6,
        #     "slow": 4,
        #     "faster": 7,
        #     "slower": 3,
        #     "fastest": 13,
        #     "slowest": 2
        # }
        # audio_speed = task_params.get('audio_speed', 'normal')
        # self.audio_speed = audio_speed_map.get(audio_speed, 5)
        
        # 随机语音设置
        use_random_voice = task_params.get('use_random_voice', False)
        if use_random_voice:
            self.audio_seed = task_params.get('audio_seed',42)
            if not self.audio_seed:
                self.audio_seed = random_with_system_time()
                print("不存在audio_seed 根据系统时间随机生成", self.audio_seed)
            print("当前audio_seed", self.audio_seed)
        else:
            self.audio_seed = None
            self.audio_voice = task_params.get('audio_voice')   


        self.chats_url = f"{self.service_location}v1/audio/speech"
    def _extract_ssml(self,ssml_str):
        start_tag = '<speak'
        end_tag = '</speak>'
        start_index = ssml_str.find(start_tag)
        end_index = ssml_str.find(end_tag) + len(end_tag)
        
        if start_index == -1 or end_index == -1:
            return None
        
        ssml_content = ssml_str[start_index:end_index]
        return ssml_content
    
    def _refine_text(self,text: str, spker: str) -> str:
        client = OpenAI(api_key=api_key, base_url=base_url)
        system_prompt = (
            "# 口播稿 SSML 转换助手"
            "你是一个专业的 SSML 转换助手,专门负责将口播稿转换为 ChatTTS-SSML 格式。你需要准确理解原文的语气、情感和节奏,并使用恰当的 SSML 标记来增强语音表现力。## 基本规范"
            "请遵循 ChatTTS-SSML v0.1 标准,支持以下标记："
            "1. `<speak version='0.1'>` 作为根元素"
            "2. `<voice>` 控制说话人和风格"
            "3. `<prosody>` 调整语速、音量和音调(语速倾向于 1.2 到 1.3)"
            "4. `<break>` 插入停顿"
            "5. 支持 [uv_break] 作为自然停顿标记"
            "## 核心限制"
            "1. spk 属性必须使用以下格式："
            "```xml"
            f"spk={spker}"
            "```"
            "2. style 属性仅可使用以下风格："
            "- advertisement_upbeat_p"
            "- chat_p"
            "- podcast_p"
            " - narration-professional_p"
            "- documentary-narration_p"
            "- narration-relaxed_p"
            "- cheerful_p"
            "- excited_p"
            "- empathetic_p"
            "- friendly_p"
            "- newscast_p"
            "- newscast-casual_p"
            "- newscast-formal_p"
            "## 语音风格参数说明"
            "每个风格都包含以下参数："
            "- speed(0-9): 语速,数值越大越快"
            "- oral(0-9): 口语化程度,数值越大越口语化"
                    "- laugh(0-2): 笑意程度,仅部分风格支持"
            "- break(1-5): 停顿程度,数值越大停顿越多"
            "## 场景匹配指南"
            "1. **产品介绍/评测**"
            "- 开场：advertisement_upbeat_p"
            "- 主体：narration-professional_p"
            "- 互动：chat_p"
            "- 结尾：friendly_p"
            "2. **知识分享/教程**"
            "- 开场：cheerful_p"
            "- 主体：documentary-narration_p"
            "- 重点：narration-professional_p"
            "- 结尾：empathetic_p"
            "3. **新闻/资讯**"
            "- 重要新闻：newscast-formal_p"
            "- 一般新闻：newscast_p"
            "- 轻松话题：newscast-casual_p"
            "4. **直播/互动**"
            "- 开场：advertisement_upbeat_p"
            "- 聊天：chat_p"
            "- 高潮：excited_p"
            "- 互动：friendly_p"
            "## 标记使用示例"
            "1. **voice 标记**"
            "```xml"
            f"<voice spk=\"{spker}\" style=\"narration-professional_p\">"
            "    专业内容讲解"
            "</voice>"
            "```"
            "2. **prosody 标记**"
            "```xml"
            "<prosody rate=\"1.2\" pitch=\"2\">"
            "    需要强调的内容"
            "</prosody>"
            "```"
            "3. **break 标记**"
            "```xml"
            "<break time=\"50\"/>  <!-- 短停顿 -->" 
            "<break time=\"100\"/>  <!-- 中停顿 -->"
            "<break time=\"150\"/>  <!-- 长停顿 -->"
            "```"
                    "## 完整示例"
            "```xml"
            "<speak version=\"0.1\">"
            f"    <voice spk=\"{spker}\" style=\"advertisement_upbeat_p\">"
            "        引人入胜的开场白"
            "    </voice>"
            f"    <voice spk=\"{spker}\" style=\"narration-professional_p\">"
            "        专业的内容讲解"
            "        <prosody rate=\"1.1\">"
            "            重点内容强调"
            "        </prosody>"
            "        <break time=\" 100\"/>"
            "        继续讲解"
            "    </voice>"
            f"    <voice spk=\"{spker}\" style=\"chat_p\">"
            "        与观众互动"
            "    </voice>"
            f"    <voice spk=\"{spker}\" style=\"friendly_p\">"
            "        温暖的结束语"
            "    </voice>"
            "</speak>"
            "```"
            "## 重要注意事项"
            "1. **标签使用规范**"
            "- speak 必须是最外层标签"
            "- voice 标签内可以包含 prosody 和 break"
            "- 确保标签正确闭合"
            "2. **禁止使用 XML 注释**"
            "- 不要使用 <!-- --> 格式的注释"
            "- 使用不同的 voice 标签来分隔不同部分"
            "3. **spk 属性规范**"
            f"- 必须使用 `{spker}` 格式"
            "- 不得使用其他格式的 spk 值"
            "4. **style 属性规范**"
            "- 仅使用推荐列表中的风格名称"
            "- 不得自行创造或修改风格名称"
            "5. **格式检查清单**"
            "- 版本号是否为 0.1"
            "- spk 格式是否正确,spk必须包含！！！"
            "- style 是否在允许列表中"
            "- 标签是否正确嵌套"
            "请在转换口播稿时严格遵循以上规范,确保生成的 SSML 代码符合所有要求。如有疑问,请参考完整示例进行对照,因为我要直接把你输出的代码作为ChatTTS的入参,所以直接输出ssml代码,禁止输出多余的任何信息或解释内容！。"
    
        ) 

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=messages
        )
        result_content = response.choices[0].message.content
        ssml_content = self._extract_ssml(result_content)
        if ssml_content:
            print(system_prompt)
            print(ssml_content)
            return ssml_content
        else:
            print("Invalid SSML string")
            return text


    def read_with_content(self, content):
        wav_file = os.path.join(self.audio_output_dir, str(random_with_system_time()) + ".wav")
        print("wav_file_path: ",wav_file)
        temp_file = self.chat_with_content(content, wav_file)
        # 读取音频文件
        audio = AudioSegment.from_file(temp_file)
        play(audio)

    def chat_with_content(self, content, audio_output_file):

        if self.use_ssml:
            # 使用 LLMChain 优化文本
            refined_text = self._refine_text(text=content, spker=self.audio_voice)
            body = {
                "input": {
                    "ssml": refined_text
                },
                "voice": {
                    "languageCode": "ZH-CN",  # 新增默认值
                    "name": self.audio_voice,
                    "style": self.audio_style,
                    "temperature": float(self.audio_temperature),
                    "topP": float(self.audio_top_p),
                    "topK": min(max(1, int(self.audio_top_k)), 20),
                    "seed": int(self.audio_seed) if self.audio_seed else 42,
                    "eos": "[uv_break]"
                },
                "audioConfig": {
                    "audioEncoding": "mp3",  # 从 response_format 映射
                    "speakingRate": 1.6,  # 从 speed 映射
                    "pitch": 0,  # 新增默认值
                    "volumeGainDb": 0,  # 新增默认值
                    "sampleRateHertz": 16000,  # 新增默认值
                    "batchSize": 4,
                    "spliterThreshold": 100
                },
                "enhancerConfig": {
                    "enhance": True,
                    "denoise": True
                }
            }
        else:

            body = {
                "input": {
                    "text": content
                },
                "voice": {
                    "languageCode": "ZH-CN",  # 新增默认值
                    "name": self.audio_voice,
                    "style": self.audio_style,
                    "temperature": float(self.audio_temperature),
                    "topP": float(self.audio_top_p),
                    "topK": min(max(1, int(self.audio_top_k)), 20),
                    "seed": int(self.audio_seed) if self.audio_seed else 42,
                    "eos": "[uv_break]"
                },
                "audioConfig": {
                    "audioEncoding": "mp3",  # 从 response_format 映射
                    "speakingRate": 1.6,  # 从 speed 映射
                    "pitch": 0,  # 新增默认值
                    "volumeGainDb": 0,  # 新增默认值
                    "sampleRateHertz": 16000,  # 新增默认值
                    "batchSize": 4,
                    "spliterThreshold": 100
                },
                "enhancerConfig": {
                    "enhance": True,
                    "denoise": True
                }  
            }
        

        print(body)

        try:
            response = requests.post(self.service_location, json=body)
            response.raise_for_status()

            # 获取 base64 编码的音频内容
            audio_base64 = response.json()['audioContent']
            print(audio_base64[:50])
            
            # 如果是 data:audio/mpeg;base64 开头的
            if audio_base64.startswith('data:'):
                audio_base64 = audio_base64.split('base64,')[1]

            # 清理和补齐
            audio_base64 = ''.join(audio_base64.split())
            while len(audio_base64) % 4:
                audio_base64 += '='

            # 解码
            audio_data = base64.b64decode(audio_base64)

            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            audio.export(audio_output_file, format="wav")

            print("Saved audio file to", audio_output_file)
            # 打印文件大小以供验证
            print(f"File size: {os.path.getsize(audio_output_file)} bytes")

            

            try:
                audio = AudioSegment.from_file(audio_output_file)
                print("Audio file is valid and can be played.")
            except Exception as e:
                print(f"Error opening audio file: {e}")

            if self.enable_audio_cut:
                output_path = Path(audio_output_file)
                # 创建临时文件名：原文件名_时间戳.temp.wav
                temp_output = output_path.parent / f"{output_path.stem}_{int(datetime.datetime.now().timestamp())}.temp{output_path.suffix}"
                
                try:
                    os.rename(audio_output_file, str(temp_output))
                    original_duration, cut_duration = self.audio_cutter.cut_audio(
                        str(temp_output),
                        audio_output_file
                    )
                    print(f"Audio cut: original duration={original_duration:.2f}s, "
                        f"cut duration={cut_duration:.2f}s")
                    # if temp_output.exists():
                    #     temp_output.unlink()
                except Exception as e:
                    print(f"Audio cutting failed: {e}")
                    # 如果处理失败，恢复原文件
                    if temp_output.exists():
                        if Path(audio_output_file).exists():
                            Path(audio_output_file).unlink()
                        os.rename(str(temp_output), audio_output_file)


            print("Saved audio file to", audio_output_file)

            return audio_output_file

        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
        except KeyError as e:
            print(f"Response format error: missing audioContent field: {e}")
        except base64.binascii.Error as e:
            print(f"Base64 decoding error: {e}")
        except IOError as e:
            print(f"File writing error: {e}")