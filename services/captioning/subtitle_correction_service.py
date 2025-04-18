import os
import json
from typing import List, Dict, Any
from openai import OpenAI
import httpx
from common.config.config import my_config

class SubtitleCorrectionService:
    """
    字幕校对服务，使用LLM对识别结果进行校对
    """
    def __init__(self):
        # 从配置中获取OpenAI API密钥和基础URL
        self.api_key = my_config["llm"]["OpenAI"]["api_key"]
        self.base_url = my_config["llm"]["OpenAI"]["base_url"]
        self.model = "us.amazon.nova-pro-v1:0"
        # 代理设置
        self.proxy_host = "172.22.93.27"
        self.proxy_port = "1081"
        
    def _create_client(self) -> OpenAI:
        """创建OpenAI客户端"""
        return OpenAI(
            api_key=self.api_key, 
            base_url=self.base_url,
            http_client=httpx.Client(
                proxies={
                    "http://": f"http://{self.proxy_host}:{self.proxy_port}",
                    "https://": f"http://{self.proxy_host}:{self.proxy_port}"
                })
        )
    
    def correct_subtitles(self, 
                          segments: List[Dict[str, Any]], 
                          original_script: str) -> List[Dict[str, Any]]:
        """
        使用LLM校对字幕内容
        
        Args:
            segments: 识别结果分段，格式为[{"start": float, "end": float, "text": str}, ...]
            original_script: 原始口播稿
            
        Returns:
            校对后的分段列表，保持原有的时间戳
        """
        # 提取所有文本段落
        all_texts = [segment["text"] for segment in segments if segment["text"].strip()]
        combined_text = " ".join(all_texts)
        
        # 如果没有文本内容，直接返回原始segments
        if not combined_text.strip():
            return segments
        
        # 构建提示
        system_prompt = """你是一个专业的字幕校对专家。你的任务是根据原始口播稿内容，校对语音识别生成的字幕文本。
请确保校对后的字幕内容与原始口播稿在语义上一致，但不需要完全相同的用词。
注意保留语音识别中可能存在的口语化表达，但纠正明显的错误识别。

请按照以下规则进行校对：
1. 保持原始分段不变，只修改文本内容中的错误
2. 如果识别结果缺少了原稿中的某些关键信息，请将其补充到适当位置
3. 如果识别结果中出现了原稿中没有的内容，但符合上下文，可以保留
4. 修正错别字、断句错误和明显的语法问题
5. 数字、专有名词等要特别注意校对准确性

你的输出必须是JSON格式，包含所有校对后的文本段落，格式如下：
{
  "corrected_segments": [
    {"index": 0, "text": "校对后的文本1"},
    {"index": 1, "text": "校对后的文本2"},
    ...
  ]
}

只需返回这个JSON对象，不要添加任何其他说明。"""
        
        user_prompt = f"""原始口播稿：
{original_script}

语音识别结果（分段）：
{json.dumps([{"index": i, "text": text} for i, text in enumerate(all_texts)], ensure_ascii=False, indent=2)}

请校对这些字幕文本，确保它们与原始口播稿在语义上一致。"""
        
        try:
            # 创建OpenAI客户端
            client = self._create_client()
            
            # 发送请求
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            correction_text = response.choices[0].message.content
            correction_data = json.loads(correction_text)
            
            # 获取校对后的分段
            corrected_segments = correction_data.get("corrected_segments", [])
            
            # 将校对结果合并回原始segments
            new_segments = []
            text_segment_index = 0
            
            for segment in segments:
                if not segment["text"].strip():
                    # 保留空文本段落（可能是静音部分）
                    new_segments.append(segment)
                else:
                    if text_segment_index < len(corrected_segments):
                        # 替换文本内容，保留时间戳
                        corrected_segment = corrected_segments[text_segment_index]
                        new_segment = segment.copy()
                        new_segment["text"] = corrected_segment["text"]
                        new_segments.append(new_segment)
                        text_segment_index += 1
                    else:
                        # 如果校对结果不足，保留原文本
                        new_segments.append(segment)
            
            return new_segments
            
        except Exception as e:
            print(f"字幕校对失败: {str(e)}")
            # 出错时返回原始segments
            return segments 