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
        self.client = httpx.Client(timeout=300.0)

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
            "max_tokens": 16384,
            "stream": False,
        }
        # 部分模型支持禁用 reasoning 以节省 token
        try:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        except Exception:
            pass

        try:
            resp = self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # 把响应体也带上，方便调试
            body = e.response.text[:500] if e.response else "(no body)"
            raise RuntimeError(f"HTTP {e.response.status_code}: {body}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"网络请求失败: {e}") from e

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def chat_stream(self, messages: list, temperature: float = 0.8):
        """流式聊天，yield 每个文本片段"""
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
            "max_tokens": 16384,
            "stream": True,
        }

        with self.client.stream("POST", url, json=payload, headers=headers, timeout=300.0) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    def chat_json(self, messages: list, temperature: float = 0.8, on_chunk=None) -> list | dict:
        """发送聊天请求，尝试解析 JSON 响应。支持流式回调。"""
        if on_chunk:
            # 流式模式：边收边回调
            raw = ""
            for chunk in self.chat_stream(messages, temperature):
                raw += chunk
                on_chunk(chunk)
        else:
            raw = self.chat(messages, temperature)

        # 保存原始响应到调试文件
        from pathlib import Path
        from datetime import datetime
        debug_dir = Path("outputs") / "_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_file = debug_dir / f"llm_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(raw)

        # 尝试提取 JSON
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> list | dict:
        """从文本中提取 JSON，高容错"""
        text = text.strip()

        # 1. 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 提取 ```json ... ``` 或 ``` ... ``` 块
        import re
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block:
            try:
                return json.loads(code_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. 截断修复优先：如果 [ 存在但 ] 不存在，说明 JSON 数组被截断
        first_bracket = text.find("[")
        last_bracket = text.rfind("]")
        if first_bracket != -1 and (last_bracket == -1 or last_bracket < first_bracket):
            # 数组被截断，找到最后一个完整的 } 补上 ]
            partial = text[first_bracket:]
            last_obj_end = partial.rfind('}')
            if last_obj_end != -1:
                candidate = partial[:last_obj_end + 1] + "]"
                # 去尾逗号
                candidate = re.sub(r',\s*\]', ']', candidate)
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

        # 4. 尝试提取 [ ... ] 或 { ... }（从外到内）
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            first = text.find(start_char)
            last = text.rfind(end_char)
            if first != -1 and last != -1 and last > first:
                candidate = text[first:last + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    try:
                        cleaned = re.sub(r'//.*?(?=[\n,}\]\'])', '', candidate)
                        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
                        return json.loads(cleaned)
                    except json.JSONDecodeError:
                        pass

        # 5. 逐步缩短尾部重试
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            first = text.find(start_char)
            if first == -1:
                continue
            for i in range(len(text) - 1, first, -1):
                if text[i] == end_char:
                    try:
                        return json.loads(text[first:i + 1])
                    except json.JSONDecodeError:
                        continue

        raise ValueError(
            f"无法从 LLM 响应中提取 JSON。\n"
            f"响应前 800 字符:\n{text[:800]}"
        )

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
