import requests
import json
from typing import Optional, Dict, Any

# API 配置
API_BASE = "https://ai.blue-converse.com/api"
API_KEY = "converse-ywdzCxUH2OLL3VTB8e3L8OEIlVxMErGJCV871iAk3J4YSa2wCXkzuKMuc2xI9nOxY"

def chat_query(
    query: str,
    chat_id: str,
    app_id: str,
    tags: Optional[Dict] = None,
    files: list = None,
    c_time: str = "",
    data_id: str = "",
    stream: bool = False,
    detail: bool = False
) -> Dict[str, Any]:
    """
    发送查询请求到API
    Args:
    query: 查询内容
    chat_id: 对话ID
    app_id: 应用ID
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

    # 构建请求数据
    payload = {
        "messages": [{
            "dataId": data_id,
            "role": "user",
            "content": []
        }],
        "variables": {
            "query": query,
            "tags": json.dumps(tags) if tags else '{"tags":{"$or":[""]}}',
            "files": files or [],
            "cTime": c_time
        },
        "appId": app_id,
        "chatId": chat_id,
        "detail": detail,
        "stream": stream
    }

    try:
        response = requests.post(
            f"{API_BASE}/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # 输出详细的错误信息用于调试
        if response.status_code != 200:
            print(f"状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            try:
                print(f"响应内容: {response.json()}")
            except:
                print(f"响应文本: {response.text}")
                
        # 检查响应状态
        response.raise_for_status()
        
        # 返回并打印JSON响应
        result = response.json()
        print("API 响应:", json.dumps(result, ensure_ascii=False, indent=2))
        return result
        
    except requests.exceptions.RequestException as e:
        error_response = {"error": str(e)}
        print("请求错误:", json.dumps(error_response, ensure_ascii=False, indent=2))
        return error_response

# 使用示例
if __name__ == "__main__":
    result = chat_query(
        query="特斯拉",
        chat_id="tiGhBShVfII1",
        app_id="67b41906322c933b8d7fc5ee"
    )