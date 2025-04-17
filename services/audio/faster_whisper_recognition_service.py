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
import openai
from typing import List

from common.config.config import my_config
from tools.utils import must_have_value
from faster_whisper import WhisperModel
from services.hunjian.hunjian_service import get_video_content_text_script


os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)
# module输出目录
module_output_dir = os.path.join(script_dir, "../../fasterwhisper")
module_output_dir = os.path.abspath(module_output_dir)


def convert_module_to_path(module_name):
    return_path = os.path.join(module_output_dir, module_name)
    print(return_path, os.path.isdir(return_path))
    return return_path


class FasterWhisperRecognitionResult:
    def __init__(self, text, begin_time, end_time):
        self.text = text
        self.begin_time = begin_time
        self.end_time = end_time

    def __str__(self):
        return f"{self.text} {self.begin_time} {self.end_time}"


class FasterWhisperRecognitionService:
    def __init__(self):
        super().__init__()
        self.model_name = my_config['audio'].get('local_recognition', {}).get('fasterwhisper', {}).get('model_name')
        must_have_value(self.model_name, "请设置语音识别model_name")
        self.device_type = my_config['audio'].get('local_recognition', {}).get('fasterwhisper', {}).get('device_type')
        self.compute_type = my_config['audio'].get('local_recognition', {}).get('fasterwhisper', {}).get('compute_type')
        must_have_value(self.device_type, "请设置语音识别device_type")
        must_have_value(self.compute_type, "请设置语音识别compute_type")
        self.OPENAI_API_KEY = my_config['llm']['OpenAI']['api_key']
        self.OPENAI_MODEL_NAME = my_config['llm']['OpenAI']['model_name'] 
        self.OPENAI_OPENAI_URL_BASE = my_config['llm']['OpenAI']['base_url'] # 替换为 open API 的model


    def process(self, audioFile, language) -> List[FasterWhisperRecognitionResult]:
        result_list = []

        # Run on GPU with FP16
        model = WhisperModel(convert_module_to_path(self.model_name), device=self.device_type, compute_type=self.compute_type,
                             local_files_only=True)

        # or run on GPU with INT8
        # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        # or run on CPU with INT8
        # model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments, info = model.transcribe(audioFile, beam_size=5)
        origin_contents = get_video_content_text_script()
        openai.api_key = self.OPENAI_API_KEY
        openai.base_url = self.OPENAI_OPENAI_URL_BASE


        print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
        buffer = ""
        for segment in segments:
            print(segment.text)
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一位专业的中文语音识别和校正助手。"
                            "你应该以原始信息为依据，将用户输入的语音识别有误的内容进行准确校正。\n"
                            f"原始信息：'{origin_contents}'"
                            "根据用户输入的上一句话定位原文位置，如果没有上一句内容，说明这是开头第一句话。"
                            "根据1.位置找到的下一句话就是你的参考原文。"
                            "输出的字数和用户输入的待修改文字字数一样。"
                            "禁止输出任何其他信息。直接输出修改后的文本内容。"
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"上一句：'{buffer}'"
                            f"待修改：'{segment.text}'"
                        )
                    },
                ]
            )
            # HTTP 请求的监控，例如在发送请求时：
            corrected_text = response.choices[0].message.content
            print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, corrected_text))
            result_list.append(
                FasterWhisperRecognitionResult(corrected_text, segment.start,
                                               segment.end))

        return result_list
