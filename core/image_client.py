"""图片生成客户端"""

import base64
import httpx
import os
from pathlib import Path
from typing import Optional
from .comfyui_client import ComfyUIClient


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
        self.client = httpx.Client(timeout=300.0)

    def generate(self, prompt: str, output_path: str,
                 reference_image: str = None, denoise: float = 0.6) -> tuple[bool, str]:
        """生成图片，保存到 output_path，返回 (成功, 信息)"""
        if self.provider == "dalle":
            return self._generate_dalle(prompt, output_path)
        elif self.provider == "flux":
            return self._generate_dalle(prompt, output_path)
        elif self.provider == "sd":
            if reference_image:
                return self._generate_sd_img2img(prompt, reference_image, output_path, denoise)
            return self._generate_sd(prompt, output_path)
        elif self.provider == "comfyui":
            return self._generate_comfyui(prompt, output_path, reference_image, denoise)
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

    def _generate_sd_img2img(self, prompt: str, reference_image: str,
                            output_path: str, denoise: float) -> tuple[bool, str]:
        """通过 SD WebUI img2img API 生成图片"""
        url = f"{self.base_url}/sdapi/v1/img2img"

        # 读取参考图并转 base64
        with open(reference_image, "rb") as f:
            init_images = [base64.b64encode(f.read()).decode("utf-8")]

        payload = {
            "prompt": prompt,
            "negative_prompt": "text, watermark, logo, signature, words, letters, symbols, low quality, blurry, distorted",
            "init_images": init_images,
            "denoising_strength": denoise,
            "steps": 30,
            "width": 1024,
            "height": 1024,
            "cfg_scale": 7,
            "sampler_name": "DPM++ 2M Karras",
        }

        try:
            resp = self.client.post(url, json=payload, timeout=300.0)
            resp.raise_for_status()
            data = resp.json()
            image_b64 = data["images"][0]
            image_bytes = base64.b64decode(image_b64)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            return True, "生成成功"
        except Exception as e:
            return False, str(e)

    def _generate_comfyui(self, prompt: str, output_path: str,
                          reference_image: str = None,
                          denoise: float = 0.6) -> tuple[bool, str]:
        """通过 ComfyUI 工作流生成图片"""
        # 工作流路径：项目目录下 workflows/flux_img2img_api.json
        project_root = Path(__file__).parent.parent
        workflow_path = project_root / "workflows" / "flux_img2img_api.json"
        if not workflow_path.exists():
            return False, f"工作流文件不存在: {workflow_path}"

        comfy = ComfyUIClient(self.base_url)

        if reference_image:
            return comfy.generate_img2img(
                workflow_path=str(workflow_path),
                reference_image=reference_image,
                prompt=prompt,
                output_path=output_path,
                denoise=denoise,
            )
        else:
            # 无参考图时，denoise=1.0 等于 txt2img
            return comfy.generate_img2img(
                workflow_path=str(workflow_path),
                reference_image=reference_image or "",
                prompt=prompt,
                output_path=output_path,
                denoise=1.0,
            )

    def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            if self.provider == "comfyui":
                comfy = ComfyUIClient(self.base_url)
                return comfy.test_connection()
            elif self.provider == "sd":
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
