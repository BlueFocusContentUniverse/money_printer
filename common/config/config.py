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
import shutil
import streamlit as st
import yaml

from tools.file_utils import read_yaml, save_yaml

app_title = "AI MCN" 

local_audio_tts_providers = ['chatTTS', 'GPTSoVITS','ChatTTS_Enhanced']
local_audio_recognition_providers = ['fasterwhisper', ]
local_audio_recognition_fasterwhisper_module_names = ['large-v3', 'large-v2', 'large-v1', 'distil-large-v3',
                                                      'distil-large-v2', 'medium', 'base', 'small', 'tiny']
local_audio_recognition_fasterwhisper_device_types = ['cuda', 'cpu', 'auto']
local_audio_recognition_fasterwhisper_compute_types = ['int8', 'int8_float16', 'float16']

GPT_soVITS_languages = {
    "auto": "多语种混合",
    "all_zh": "中文",
    "all_yue": "粤语",
    "en": "英文",
    "all_ja": "日文",
    "all_ko": "韩文",
    "zh": "中英混合",
    "yue": "粤英混合",
    "ja": "日英混合",
    "ko": "韩英混合",
    "auto_yue": "多语种混合(粤语)",
}

audio_types = {'remote': "云服务", 'local': "本地模型",'local_enhance':"ChatTTS_Enhance"}
languages = {'zh-CN': "简体中文", 'en': "english", 'zh-TW': "繁體中文"}
audio_languages = {'zh-CN': "中文", 'en-US': "english"}
audio_voices_tencent = {
    "zh-CN": {
        "1001": "智瑜(女)",
        "1002": "智聆(女)",
        "1003": "智美(女)",
        "1004": "智云(男)",
        "1005": "智莉(女)",
        "1007": "智娜(女)",
        "1008": "智琪(女)",
        "1009": "智芸(女)",
        "1010": "智华(男)",
        "1017": "智蓉(女)",
        "1018": "智靖(男)",
        "100510000": "智逍遥(男)",
        "101001": "智瑜(女)",
        "101002": "智聆(女)",
        "101003": "智美(女)",
        "101004": "智云(男)",
        "101005": "智莉(女)",
        "101006": "智言(女)",
        "101007": "智娜(女)",
        "101008": "智琪(女)",
        "101009": "智芸(女)",
        "1010010": "智华(男)",
        "1010011": "智燕(女)",
        "1010012": "智丹(女)",
        "1010013": "智辉(男)",
        "1010014": "智宁(男)",
        "1010015": "智萌(男童)",
        "1010016": "智甜(女童)",
        "1010017": "智蓉(女)",
        "1010018": "智靖(男)",
        "1010019": "智彤(粤语)",
        "1010020": "智刚(男)",
        "1010021": "智瑞(男)",
        "1010022": "智虹(女)",
        "1010023": "智萱(女)",
        "1010024": "智皓(男)",
        "1010025": "智薇(女)",
        "1010026": "智希(女)",
        "1010027": "智梅(女)",
        "1010028": "智洁(女)",
        "1010029": "智凯(男)",
        "1010030": "智柯(男)"
    },
    "en-US": {
        "1050": "WeJack(男)",
        "1051": "WeRose(女)",
        "101050": "WeJack(男)精品",
        "101051": "WeRose(女)精品"
    }
}

audio_voices_azure = {
    "zh-CN": {
        "zh-CN-XiaoxiaoNeural": "晓晓(女)",
        "zh-CN-YunxiNeural": "云希(男)",
        "zh-CN-YunjianNeural": "云健(男)",
        "zh-CN-XiaoyiNeural": "晓伊(女)",
        "zh-CN-YunyangNeural": "云扬(男)",
        "zh-CN-XiaochenNeural": "晓晨(女)",
        "zh-CN-XiaohanNeural": "晓涵(女)",
        "zh-CN-XiaomengNeural": "晓萌(女)",
        "zh-CN-XiaomoNeural": "晓墨(女)",
        "zh-CN-XiaoqiuNeural": "晓秋(女)",
        "zh-CN-XiaoruiNeural": "晓睿(女)",
        "zh-CN-XiaoshuangNeural": "晓双(女,儿童)",
        "zh-CN-XiaoyanNeural": "晓颜(女)",
        "zh-CN-XiaoyouNeural": "晓悠(女,儿童)",
        "zh-CN-XiaozhenNeura": "晓珍(女)",
        "zh-CN-YunfengNeural": "云峰(男)",
        "zh-CN-YunhaoNeural": "云浩(男)",
        "zh-CN-YunxiaNeural": "云夏(男)",
        "zh-CN-YunyeNeural": "云野(男)",
        "zh-CN-YunzeNeural": "云泽(男)",
        "zh-CN-XiaochenMultilingualNeural": "晓晨(女),多语言",
        "zh-CN-XiaorouNeural": "晓蓉(女)",
        "zh-CN-XiaoxiaoDialectsNeural": "晓晓(女),方言",
        "zh-CN-XiaoxiaoMultilingualNeural": "晓晓(女),多语言",
        "zh-CN-XiaoyuMultilingualNeural": "晓雨(女),多语言",
        "zh-CN-YunjieNeural": "云杰(男)",
        "zh-CN-YunyiMultilingualNeural": "云逸(男),多语言"
    },
    "en-US": {
        "en-US-AvaMultilingualNeural": "Ava(female)",
        "en-US-AndrewNeural": "Andrew(male)",
        "en-US-EmmaNeural": "Emma(female)",
        "en-US-BrianNeural": "Brian(male)",
        "en-US-JennyNeural": "Jenny(female)",
        "en-US-GuyNeural": "Guy(male)",
        "en-US-AriaNeural": "Aria(female)",
        "en-US-DavisNeural": "Davis(male)",
        "en-US-JaneNeural": "Jane(female)",
        "en-US-JasonNeural": "Jason(male)",
        "en-US-SaraNeural": "Sara(female)",
        "en-US-TonyNeural": "Tony(male)",
        "en-US-NancyNeural": "Nancy(female)",
        "en-US-AmberNeural": "Amber(female)",
        "en-US-AnaNeural": "Ana(female),child",
        "en-US-AshleyNeural": "Ashley(female)",
        "en-US-BrandonNeural": "Brandon(male)",
        "en-US-ChristopherNeural": "Christopher(male)",
        "en-US-CoraNeural": "Cora(female)",
        "en-US-ElizabethNeural": "Elizabeth(female)",
        "en-US-EricNeural": "Eric(male)",
        "en-US-JacobNeural": "Jacob(male)",
        "en-US-JennyMultilingualNeural": "Jenny(female),multilingual",
        "en-US-MichelleNeural": "Michelle(female)",
        "en-US-MonicaNeural": "Monica(female)",
        "en-US-RogerNeural": "Roger(male)",
        "en-US-RyanMultilingualNeural": "Ryan(male),multilingual",
        "en-US-SteffanNeural": "Steffan(male)",
        "en-US-AndrewMultilingualNeura": "Andrew(male),multilingual",
        "en-US-BlueNeural": "Blue(neural)",
        "en-US-BrianMultilingualNeural": "Brian(male),multilingual",
        "en-US-EmmaMultilingualNeural": "Emma(female),multilingual",
        "en-US-AlloyMultilingualNeural": "Alloy(male),multilingual",
        "en-US-EchoMultilingualNeural": "Echo(male),multilingual",
        "en-US-FableMultilingualNeural": "Fable(neural),multilingual",
        "en-US-OnyxMultilingualNeural": "Onyx(male),multilingual",
        "en-US-NovaMultilingualNeural": "Nova(female),multilingual",
        "en-US-ShimmerMultilingualNeural": "Shimmer(female),multilingual",
    }
}

audio_voices_ali = {
    "zh-CN": {
        "zhixiaobai": "知小白(普通话女声)",
        "zhixiaoxia": "知小夏(普通话女声)",
        "zhixiaomei": "知小妹(普通话女声)",
        "zhigui": "知柜(普通话女声)",
        "zhishuo": "知硕(普通话男声)",
        "aixia": "艾夏(普通话女声)",
        "xiaoyun": "小云(标准女声)",
        "xiaogang": "小刚(标准男声)",
        "ruoxi": "若兮(温柔女声)",
        "siqi": "思琪(温柔女声)",
        "sijia": "思佳(标准女声)",
        "sicheng": "思诚(标准男声)",
        "aiqi": "艾琪(温柔女声)",
        "aijia": "艾佳(标准女声)",
        "aicheng": "艾诚(标准男声)",
        "aida": "艾达(标准男声)",
        "ninger": "宁儿(标准女声)",
        "ruilin": "瑞琳(标准女声)",
        "siyue": "思悦(温柔女声)",
        "aiya": "艾雅(严厉女声)",
        "aimei": "艾美(甜美女声)",
        "aiyu": "艾雨(自然女声)",
        "aiyue": "艾悦(温柔女声)",
        "aijing": "艾静(严厉女声)",
        "xiaomei": "小美(甜美女声)",
        "aina": "艾娜(浙普女声)",
        "yina": "依娜(浙普女声)",
        "sijing": "思婧(严厉女声)",
        "sitong": "思彤(儿童音)",
        "xiaobei": "小北(萝莉女声)",
        "aitong": "艾彤(儿童音)",
        "aiwei": "艾薇(萝莉女声)",
        "aibao": "艾宝(萝莉女声)"

    },
    "en-US": {
        "zhixiaobai": "知小白(普通话女声)",
        "zhixiaoxia": "知小夏(普通话女声)",
        "zhixiaomei": "知小妹(普通话女声)",
        "zhigui": "知柜(普通话女声)",
        "zhishuo": "知硕(普通话男声)",
        "aixia": "艾夏(普通话女声)",
        "cally": "Cally(美式英文女声)",
        "xiaoyun": "小云(标准女声)",
        "xiaogang": "小刚(标准男声)",
        "ruoxi": "若兮(温柔女声)",
        "siqi": "思琪(温柔女声)",
        "sijia": "思佳(标准女声)",
        "sicheng": "思诚(标准男声)",
        "aiqi": "艾琪(温柔女声)",
        "aijia": "艾佳(标准女声)",
        "aicheng": "艾诚(标准男声)",
        "aida": "艾达(标准男声)",
        "siyue": "思悦(温柔女声)",
        "aiya": "艾雅(严厉女声)",
        "aimei": "艾美(甜美女声)",
        "aiyu": "艾雨(自然女声)",
        "aiyue": "艾悦(温柔女声)",
        "aijing": "艾静(严厉女声)",
        "xiaomei": "小美(甜美女声)",
        "harry": "Harry(英音男声)",
        "abby": "Abby(美音女声)",
        "andy": "Andy(美音男声)",
        "eric": "Eric(英音男声)",
        "emily": "Emily(英音女声)",
        "luna": "Luna(英音女声)",
        "luca": "Luca(英音男声)",
        "wendy": "Wendy(英音女声)",
        "william": "William(英音男声)",
        "olivia": "Olivia(英音女声)"
    }
}

transition_types = ['xfade']
fade_list = ['fade', 'smoothleft', 'smoothright', 'smoothup', 'smoothdown', 'circlecrop', 'rectcrop', 'circleclose',
             'circleopen', 'horzclose', 'horzopen', 'vertclose',
             'vertopen', 'diagbl', 'diagbr', 'diagtl', 'diagtr', 'hlslice', 'hrslice', 'vuslice', 'vdslice', 'dissolve',
             'pixelize', 'radial', 'hblur',
             'wipetl', 'wipetr', 'wipebl', 'wipebr', 'zoomin', 'hlwind', 'hrwind', 'vuwind', 'vdwind', 'coverleft',
             'coverright', 'covertop', 'coverbottom', 'revealleft', 'revealright', 'revealup', 'revealdown']

driver_types = {
    "chrome": 'chrome',
    "firefox": 'firefox'}

chattts_enhanced_style_options = {
    "advertisement_upbeat":"兴奋广告",
    "affectionate":"温情脉脉",
    "angry":"愤怒",
    "assistant":"助手",
    "calm":"冷静",
    "chat":"聊天",
    "cheerful":"愉快",
    "customerservice":"客服",
    "depressed":"沮丧",
    "disgruntled":"不满",
    "documentary-narration":"纪录片旁白",
    "embarrassed":"尴尬",
    "empathetic":"共情",
    "envious":"羡慕",
    "excited":"兴奋",
    "fearful":"恐惧",
    "friendly":"友好",
    "gentle":"温柔",
    "hopeful":"充满希望",
    "lyrical":"抒情",
    "narration-professional":"专业旁白",
    "narration-relaxed":"轻松旁白",
    "newscast":"新闻播报",
    "newscast-casual":"随意新闻播报",
    "newscast-formal":"正式新闻播报",
    "poetry-reading":"诗歌朗读",
    "sad":"悲伤",
    "serious":"严肃",
    "shouting":"喊叫",
    "sports_commentary":"体育解说",
    "sports_commentary_excited":"激情体育解说",
    "whispering":"耳语",
    "terrified":"惊恐",
    "unfriendly":"不友好",
    "advertisement_upbeat_p":"兴奋广告(中文提示)",
    "affectionate_p":"温情脉脉(中文提示)",
    "angry_p":"愤怒(中文提示)",
    "assistant_p":"助手(中文提示)",
    "calm_p":"冷静(中文提示)",
    "chat_p":"闲聊(中文提示)",
    "cheerful_p":"愉快(中文提示)",
    "customerservice_p":"客服(中文提示)",
    "depressed_p":"沮丧(中文提示)",
    "disgruntled_p":"不满(中文提示)",
    "documentary-narration_p":"纪录片旁白(中文提示)",
    "embarrassed_p":"尴尬(中文提示)",
    "empathetic_p":"共情(中文提示)",
    "envious_p":"羡慕(中文提示)",
    "excited_p":"兴奋(中文提示)",
    "fearful_p":"恐惧(中文提示)",
    "friendly_p":"友好(中文提示)",
    "gentle_p":"温柔(中文提示)",
    "hopeful_p":"充满希望(中文提示)",
    "lyrical_p":"抒情(中文提示)",
    "narration-professional_p":"专业旁白(中文提示)",
    "narration-relaxed_p":"轻松旁白(中文提示)",
    "newscast_p":"新闻播报(中文提示)",
    "newscast-casual_p":"随意新闻播报(中文提示)",
    "newscast-formal_p":"正式新闻播报(中文提示)",
    "poetry-reading_p":"诗歌朗读(中文提示)",
    "sad_p":"悲伤(中文提示)",
    "serious_p":"严肃(中文提示)",
    "shouting_p":"喊叫(中文提示)",
    "sports_commentary_p":"体育解说(中文提示)",
    "sports_commentary_excited_p":"激情体育解说(中文提示)",
    "whispering_p":"耳语(中文提示)",
    "terrified_p":"惊恐(中文提示)",
    "unfriendly_p":"不友好(中文提示)",
    "podcast":"播客",
    "podcast_p":"播客(中文提示)",
    "advertisement_upbeat_p_en":"兴奋广告(英文提示)",
    "affectionate_p_en":"温情脉脉(英文提示)",
    "angry_p_en":"愤怒(英文提示)",
    "assistant_p_en":"助手(英文提示)",
    "calm_p_en":"冷静(英文提示)",
    "chat_p_en":"闲聊(英文提示)",
    "cheerful_p_en":"愉快(英文提示)",
    "customerservice_p_en":"客服(英文提示)",
    "depressed_p_en":"沮丧(英文提示)",
    "disgruntled_p_en":"不满(英文提示)",
    "documentary-narration_p_en":"纪录片旁白(英文提示)",
    "embarrassed_p_en":"尴尬(英文提示)",
    "empathetic_p_en":"共情(英文提示)",
    "envious_p_en":"羡慕(英文提示)",
    "excited_p_en":"兴奋(英文提示)",
    "fearful_p_en":"恐惧(英文提示)",
    "friendly_p_en":"友好(英文提示)",
    "gentle_p_en":"温柔(英文提示)",
    "hopeful_p_en":"充满希望(英文提示)",
    "lyrical_p_en":"抒情(英文提示)",
    "narration-professional_p_en":"专业旁白(英文提示)",
    "narration-relaxed_p_en":"轻松旁白(英文提示)",
    "newscast_p_en":"新闻播报(英文提示)",
    "newscast-casual_p_en":"随意新闻播报(英文提示)",
    "newscast-formal_p_en":"正式新闻播报(英文提示)",
    "poetry-reading_p_en":"诗歌朗读(英文提示)",
    "sad_p_en":"悲伤(英文提示)",
    "serious_p_en":"严肃(英文提示)",
    "shouting_p_en":"喊叫(英文提示)",
    "sports_commentary_p_en":"体育解说(英文提示)",
    "sports_commentary_excited_p_en":"激情体育解说(英文提示)",
    "whispering_p_en":"耳语(英文提示)",
    "terrified_p_en":"惊恐(英文提示)",
    "unfriendly_p_en":"不友好(英文提示)",
    "podcast_p_en":"播客(英文提示)"
}

chattts_enhanced_speed_options = {
    "1" : "慢",
    "2" : "有点慢",
    "3" : "接近正常语速",
    "4" : "正常语速",
    "5" : "比正常语速快一点",
    "6" : "比正常语速快两点",
    "7": "快",
    "8" : "很快",
    "9" : "非常快"
    
}
chattts_enhanced_name_options = {
   "声音有点像陈一发": "声音有点像陈一发",
    "纯情男大学生": "纯情男大学生",
    "阳光开朗大男孩": "阳光开朗大男孩",
    "知心小姐姐": "知心小姐姐",
    "电台女主持":"电台女主持",
    "魅力大叔": "魅力大叔",
    "比较甜美": "比较甜美",
    "正式": "正式",
    "娘娘腔": "娘娘腔",
    "好哥们": "好哥们",
    "知书达理": "知书达理",
    "班级话痨": "班级话痨",
    "歪果仁讲中文": "歪果仁讲中文",
    "大虎妞": "大虎妞",
    "嗲嗲的很酥麻": "嗲嗲的很酥麻",
    "音色有韵味带磁性": "音色有韵味带磁性",
    "做事很着急的领导": "做事很着急的领导",
    "有磁性的男播音": "有磁性的男播音",
    "文弱书生": "文弱书生",
    "天生男低音": "天生男低音",
    "娘娘腔拉满了": "娘娘腔拉满了",
    "严肃女领导": "严肃女领导"
}

douyin_site = "https://creator.douyin.com/creator-micro/content/upload"
shipinhao_site = "https://channels.weixin.qq.com/platform/post/create"
kuaishou_site = "https://cp.kuaishou.com/article/publish/video"
xiaohongshu_site = "https://creator.xiaohongshu.com/publish/publish?source=official"

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)

config_example_file_name = "config.example.yml"
config_file_name = "config.yml"
session_file_name = "session.yml"

config_example_file = os.path.join(script_dir, config_example_file_name)
config_file = os.path.join(script_dir, config_file_name)
session_file = os.path.join(script_dir, session_file_name)
exclude_keys = ['01_first_visit', '02_first_visit', '03_first_visit', '04_first_visit','reference_audio','audio_temperature']


def save_session_state_to_yaml():
    # 创建一个字典副本，排除指定的键
    state_to_save = {key: value for key, value in st.session_state.items() if key not in exclude_keys}

    """将 Streamlit session_state 中的所有值保存到 YAML 文件"""
    with open(session_file, 'w') as file:
        yaml.dump(dict(state_to_save), file)


def delete_first_visit_session_state(first_visit):
    # 从session_state中删除其他first_vist标记
    for key in exclude_keys:
        if key != first_visit and key in st.session_state:
            del st.session_state[key]


def load_session_state_from_yaml(first_visit):
    delete_first_visit_session_state(first_visit)
    # 检查是否存在 "first_visit" 标志
    if first_visit not in st.session_state:
        # 第一次进入页面，设置标志为 True
        st.session_state[first_visit] = True
        """从 YAML 文件中读取数据并更新 session_state"""
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r') as file:
                    data = yaml.safe_load(file)
                    for key, value in data.items():
                        st.session_state[key] = value
            except FileNotFoundError:
                st.warning(f"File {session_file} not found.")
    else:
        # 后续访问页面，标志设置为 False
        st.session_state[first_visit] = False


def load_config():
    print("load_config")
    # 加载配置文件
    if not os.path.exists(config_file):
        shutil.copy(config_example_file, config_file)
    if os.path.exists(config_file):
        return read_yaml(config_file)


def test_config(todo_config, *args):
    temp_config = todo_config
    for arg in args:
        if arg not in temp_config:
            temp_config[arg] = {}
        temp_config = temp_config[arg]


def save_config():
    # 保存配置文件
    if os.path.exists(config_file):
        save_yaml(config_file, my_config)


my_config = load_config()
