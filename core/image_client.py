"""图片生成客户端"""

import base64
import httpx
import os
from pathlib import Path
from typing import Optional


class ImageClient:
    """图片生成客户端，支持多种 provider"""

    def __init__(self, provider: str, base_url: str, api_key: str,
                 model: str, size: str, quality: str):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.size = size
        self.quality = quality
        self.client = httpx.Client(timeout=120.0)

    def generate(self, prompt: str, output_path: str) -> tuple[bool, str]:
        """生成图片，保存到 output_path，返回 (成功, 信息)"""
        if self.provider == "dalle":
            return self._generate_dalle(prompt, output_path)
        elif self.provider == "flux":
            return self._generate_flux(prompt, output_path)
        elif self.provider == "sd":
            return self._generate_sd(prompt, output_path)
        else:
            return False, f"不支持的 provider: {self.provider}"

    def _generate_dalle(self, prompt: str, output_path: str) -> tuple[bool, str]:
        """通过 OpenAI DALL-E API 生成图片"""
        url = f"{self.base_url}/images/generations"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": self.size,
            "quality": self.quality,
            "response_format": "b64_json",
        }

        try:
            resp = self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            image_b64 = data["data"][0]["b64_json"]
            image_bytes = base64.b64decode(image_b64)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            return True, "生成成功"
        except Exception as e:
            return False, str(e)

    def _generate_flux(self, prompt: str, output_path: str) -> tuple[bool, str]:
        """通过 Flux API 生成图片（兼容 OpenAI 格式）"""
        return self._generate_dalle(prompt, output_path)

    def _generate_sd(self, prompt: str, output_path: str) -> tuple[bool, str]:
        """通过 Stable Diffusion WebUI API 生成图片"""
        url = f"{self.base_url}/sdapi/v1/txt2img"
        payload = {
            "prompt": prompt,
            "negative_prompt": "low quality, blurry, distorted, ugly, text, watermark",
            "steps": 30,
            "width": 1024,
            "height": 1024,
            "cfg_scale": 7,
            "sampler_name": "DPM++ 2M Karras",
        }

        try:
            resp = self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            image_b64 = data["images"][0]
            image_bytes = base64.b64decode(image_b64)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            return True, "生成成功"
        except Exception as e:
            return False, str(e)

    def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            if self.provider == "sd":
                url = f"{self.base_url}/sdapi/v1/options"
                resp = self.client.get(url, timeout=10.0)
                resp.raise_for_status()
                return True, "SD WebUI 连接成功"
            elif self.provider in ("dalle", "flux"):
                # 尝试列模型
                url = f"{self.base_url}/models"
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                resp = self.client.get(url, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    return True, "连接成功"
                return False, f"HTTP {resp.status_code}"
            return False, "未知 provider"
        except Exception as e:
            return False, str(e)

    def close(self):
        self.client.close()
