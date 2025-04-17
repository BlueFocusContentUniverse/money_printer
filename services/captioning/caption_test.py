
import json
import os
import platform
from typing import Optional
import time


import subprocess


import streamlit as st



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

def process_text(text: str, recursive=True) -> tuple[str, str | None, bool]:
    """
    处理文本并返回适当的格式
    返回值: (处理后的文本, 第二部分文本, 是否需要分段)
    """
    # 如果是空文本，直接返回 None
    if not text or text.isspace():
        return None, None, False
    
    # 清理文本中的多余空格
    text = ' '.join(text.split())
    
    # 短文本直接返回
    if len(text) <= 12:
        return text, None, False
    
    # 强停顿符号（优先分割）
    primary_splits = ['。', '！', '？', '；']
    # 弱停顿符号（次优先分割）
    secondary_splits = ['，', '、']
    
    def find_best_split(text: str, max_length: int = 6) -> int:
        if len(text) <= max_length:
            return -1
            
        # 优先查找强停顿
        for i, char in enumerate(text[:max_length]):
            if char in primary_splits:
                return i
                
        # 其次查找弱停顿
        for i, char in enumerate(text[:max_length]):
            if char in secondary_splits:
                return i
                
        # 找不到合适的分割点，在最大长度处分割
        return max_length - 1
    
    # 根据文本长度决定分行还是分段
    if len(text) <= 12:  # 适中长度文本
        return text, None, False
    elif len(text) <= 20:  # 较长文本分行显示
        split_point = find_best_split(text,10)
        if split_point == -1:
            return text, None, False
        return f"{text[:split_point+1]}\n{text[split_point+1:].strip()}", None, False
    else:  # 超长文本分段显示
        first_split = find_best_split(text, 15)
        if first_split == -1:
            first_split = 15
        
        first_part = text[:first_split+1].strip()
        second_part = text[first_split+1:].strip()
        
        # 递归处理两个部分
        if recursive:
            # 处理第一部分
            first_processed, first_second, first_needs_split = process_text(first_part, False)
            if first_needs_split:
                first_part = f"{first_processed}\n{first_second}" if first_second else first_processed
            else:
                first_part = first_processed
                
            # 处理第二部分
            second_processed, second_second, second_needs_split = process_text(second_part, False)
            if second_needs_split:
                second_part = f"{second_processed}\n{second_second}" if second_second else second_processed
            else:
                second_part = second_processed
        
        return first_part, second_part, True

def generate_srt(results, output_file):
    subtitle_entries = []
    subtitle_index = 1
    
    for result in results:
        # 跳过空文本
        if not result.text or result.text.isspace():
            continue
            
        processed_text, second_part, need_split = process_text(result.text)
        
        # 如果处理后的文本为空，跳过这个条目
        if processed_text is None:
            continue
            
        if not need_split:
            entry = {
                'index': subtitle_index,
                'start': format_time(result.begin_time),
                'end': format_time(result.end_time),
                'text': processed_text
            }
            subtitle_entries.append(entry)
            subtitle_index += 1
        else:
            mid_time = calculate_mid_time(result.begin_time, result.end_time, 
                                        processed_text, second_part)
            
            # 第一部分
            entry1 = {
                'index': subtitle_index,
                'start': format_time(result.begin_time),
                'end': format_time(mid_time),
                'text': processed_text
            }
            subtitle_entries.append(entry1)
            subtitle_index += 1
            
            # 第二部分
            entry2 = {
                'index': subtitle_index,
                'start': format_time(mid_time),
                'end': format_time(result.end_time),
                'text': second_part
            }
            subtitle_entries.append(entry2)
            subtitle_index += 1
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in subtitle_entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['text']}\n\n")

if __name__ == "__main__": 

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
    output_file = ""
    generate_srt(test_results, output_file)
    
    # 打印生成的文件内容
    print("生成的字幕文件内容：")
    with open(output_file, 'r', encoding='utf-8') as f:
        print(f.read())