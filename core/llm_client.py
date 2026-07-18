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
        # 禁用 reasoning 以节省 token
        try:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        except Exception:
            pass

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
        # 保存请求 prompt 到调试文件
        from pathlib import Path
        from datetime import datetime
        debug_dir = Path("outputs") / "_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        req_file = debug_dir / f"llm_request_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(req_file, "w", encoding="utf-8") as f:
            for i, msg in enumerate(messages):
                f.write(f"=== {msg.get('role', '?')} (msg {i+1}) ===\n")
                f.write(msg.get("content", ""))
                f.write("\n\n")

        if on_chunk:
            # 流式模式：边收边回调
            raw = ""
            for chunk in self.chat_stream(messages, temperature):
                raw += chunk
                on_chunk(chunk)
        else:
            raw = self.chat(messages, temperature)

        # 保存原始响应到调试文件
        debug_file = debug_dir / f"llm_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(raw)

        # 尝试提取 JSON
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> list | dict:
        """从文本中提取 JSON，高容错

        处理以下异常情况：
        1. LLM 输出前后有额外文字/解释
        2. ```json 代码块包裹
        3. JSON 被截断（缺少结尾 ] 或 }）
        4. 单引号代替双引号
        5. 键名缺少引号
        6. 尾逗号
        7. 缺少开头的 [ 或 {
        """
        import re

        text = text.strip()

        # 1. 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 提取 ```json ... ``` 或 ``` ... ``` 块
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block:
            try:
                return json.loads(code_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. 预处理：修复常见格式问题
        def _fix_json_string(s: str) -> str:
            """修复常见 JSON 格式问题"""
            # 单引号转双引号（只处理键和值的引号，不处理字符串内部的）
            s = re.sub(r"'([\w_]+)'", r'"\1"', s)  # 单引号包裹的键名/简单值
            s = re.sub("'([^']*?)'", r'"\1"', s)  # 其他单引号字符串（简化：只排除单引号）
            # 单个单引号在键名前: 'image_prompt" → "image_prompt"
            s = re.sub(r"'(\w+)\"", r'"\1"', s)
            # 单个单引号在值前: : 'value → : "value"
            s = re.sub(r":\s*'(.*?)['\n,}]", r': "\1"', s)
            # 键名缺少引号: frame: → "frame":
            s = re.sub(r'([{,]\s*)(\w+)\s*:', r'\1"\2":', s)
            # 键名缺少左引号但有右引号: frame" → "frame"
            s = re.sub(r'([{,]\s*)(\w+)"\s*:', r'\1"\2":', s)
            # 去尾逗号
            s = re.sub(r',\s*([}\]])', r'\1', s)
            # 去注释
            s = re.sub(r'//.*?(?=[\n,}\]\'])', '', s)
            return s

        # 4. 尝试找到 JSON 主体并修复
        # 先找到第一个 [ 或 {
        first_bracket = -1
        first_close = -1
        for i, c in enumerate(text):
            if c in '[{':
                first_bracket = i
                break
            if c in '}]' and first_close == -1:
                first_close = i

        # 如果闭合括号在开括号之前（或没有开括号），说明开头被截断
        if first_bracket == -1 or (first_close != -1 and first_close < first_bracket):
            # 开头被截断，尝试补全 [{
            has_close_brace = '}' in text
            has_close_bracket = ']' in text
            if has_close_brace or has_close_bracket:
                # 尝试在开头补 [{
                patched = '[{' + text
                fixed = _fix_json_string(patched)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
                # 尝试只补 {
                patched2 = '{' + text
                fixed2 = _fix_json_string(patched2)
                try:
                    return json.loads(fixed2)
                except json.JSONDecodeError:
                    pass
                # 如果有 }]，尝试补 [{ 并截断到最后一个 }
                if has_close_brace:
                    last_brace = text.rfind('}')
                    if last_brace > 0:
                        patched3 = '[{' + text[:last_brace + 1] + ']'
                        patched3 = re.sub(r',\s*\]', ']', patched3)
                        fixed3 = _fix_json_string(patched3)
                        try:
                            return json.loads(fixed3)
                        except json.JSONDecodeError:
                            pass
            else:
                # 完全没有闭合括号，内容被严重截断
                # 策略1：补全 [{...}] 并尝试解析
                patched = '[{' + text + '}]'
                fixed = _fix_json_string(patched)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
                # 策略2：从后往前逐个逗号截断，找到最后一个完整的键值对
                # 收集所有逗号位置
                comma_positions = [i for i, c in enumerate(text) if c == ',']
                for comma_pos in reversed(comma_positions):
                    partial = text[:comma_pos]
                    # 补全为 [{...}]
                    patched2 = '[{' + partial + '}]'
                    patched2 = re.sub(r',\s*\]', ']', patched2)
                    fixed2 = _fix_json_string(patched2)
                    try:
                        return json.loads(fixed2)
                    except json.JSONDecodeError:
                        # 可能是值字符串没有结束引号，补一个
                        # 检查 partial 最后一个 " 后面是否有完整值
                        last_quote = partial.rfind('"')
                        if last_quote >= 0:
                            # 在最后一个 " 前面找冒号
                            before_quote = partial[:last_quote]
                            colon_pos = before_quote.rfind(':')
                            if colon_pos >= 0:
                                # 值可能是被截断的字符串，补结束引号
                                patched3 = '[{' + partial + '"}]'
                                patched3 = re.sub(r',\s*\]', ']', patched3)
                                patched3 = re.sub(r'"\s*"', '"', patched3)  # 避免双引号
                                fixed3 = _fix_json_string(patched3)
                                try:
                                    return json.loads(fixed3)
                                except json.JSONDecodeError:
                                    pass
            # 尝试预处理后整体解析
            fixed = _fix_json_string(text)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                if first_bracket == -1:
                    raise ValueError(
                        f"无法从 LLM 响应中提取 JSON。\n"
                        f"响应前 800 字符:\n{text[:800]}"
                    )
                # first_bracket 存在但 first_close 更靠前，继续后续逻辑
                pass

        # 5. 从第一个 [ 或 { 开始，尝试各种修复
        candidate = text[first_bracket:]

        # 5a. 直接修复后解析
        fixed = _fix_json_string(candidate)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 5b. 截断修复：如果 [ 存在但 ] 不存在
        last_bracket = candidate.rfind(']')
        last_brace = candidate.rfind('}')
        first_char = candidate[0]

        if first_char == '[' and (last_bracket == -1 or last_bracket < last_brace):
            # 数组被截断，找到最后一个完整的 } 补上 ]
            partial = candidate
            last_obj_end = partial.rfind('}')
            if last_obj_end != -1:
                truncated = partial[:last_obj_end + 1] + "]"
                truncated = re.sub(r',\s*\]', ']', truncated)
                fixed = _fix_json_string(truncated)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        if first_char == '{' and last_brace != -1:
            # 单个对象
            obj_candidate = candidate[:last_brace + 1]
            fixed = _fix_json_string(obj_candidate)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        # 5c. 提取 [ ... ] 或 { ... }（包含修复）
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            first = candidate.find(start_char)
            last = candidate.rfind(end_char)
            if first != -1 and last != -1 and last > first:
                sub = candidate[first:last + 1]
                fixed = _fix_json_string(sub)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        # 6. 逐对象提取（终极兜底）
        # 从文本中逐个提取 {...} 对象，拼成数组
        objects = []
        depth = 0
        obj_start = -1
        in_string = False
        escape = False
        quote_char = None

        for i, c in enumerate(text):
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            # 处理字符串（支持单双引号）
            if c in '"\'' and not in_string:
                in_string = True
                quote_char = c
            elif c == quote_char and in_string:
                in_string = False
                quote_char = None
            elif not in_string:
                if c == '{':
                    if depth == 0:
                        obj_start = i
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0 and obj_start != -1:
                        obj_text = text[obj_start:i + 1]
                        fixed = _fix_json_string(obj_text)
                        try:
                            obj = json.loads(fixed)
                            objects.append(obj)
                        except json.JSONDecodeError:
                            pass
                        obj_start = -1

        if objects:
            return objects if len(objects) > 1 else objects[0]

        # 7. 逐步缩短尾部重试（最后手段）
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            first = candidate.find(start_char)
            if first == -1:
                continue
            for i in range(len(candidate) - 1, first, -1):
                if candidate[i] == end_char:
                    sub = candidate[first:i + 1]
                    fixed = _fix_json_string(sub)
                    try:
                        return json.loads(fixed)
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
