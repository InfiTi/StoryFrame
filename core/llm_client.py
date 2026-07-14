"""LLM 客户端 - 兼容 OpenAI API 格式（LMStudio / 远程 API）"""

import json
import httpx
from typing import Optional


class LLMClient:
    """LLM 客户端，兼容 OpenAI API 格式"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=120.0)

    def chat(self, messages: list, temperature: float = 0.8) -> str:
        """发送聊天请求，返回文本响应"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }

        resp = self.client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def chat_json(self, messages: list, temperature: float = 0.8) -> list | dict:
        """发送聊天请求，尝试解析 JSON 响应"""
        raw = self.chat(messages, temperature)
        # 尝试提取 JSON
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> list | dict:
        """从文本中提取 JSON"""
        # 先尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 块
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return json.loads(text[start:end].strip())

        # 尝试提取 [ ... ] 或 { ... }
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            if start_char in text and end_char in text:
                start = text.index(start_char)
                end = text.rindex(end_char) + 1
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"无法从 LLM 响应中提取 JSON:\n{text[:500]}")

    def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            url = f"{self.base_url}/models"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = self.client.get(url, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("id", "unknown") for m in data.get("data", [])]
            if models:
                return True, f"可用模型: {', '.join(models[:5])}"
            return True, "连接成功（未返回模型列表）"
        except Exception as e:
            return False, str(e)

    def close(self):
        self.client.close()
