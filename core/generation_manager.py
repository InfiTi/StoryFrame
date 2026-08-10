"""统一生成管理器

一个入口管图片和视频生成，底层 provider 可切换。
- 图片: comfyui / kontext / sd / dalle / agnes
- 视频: agnes

使用方式:
    mgr = GenerationManager(config)
    ok, path_or_url, msg = mgr.generate_image(prompt, output_path, ...)
    ok, path, msg = mgr.generate_video(prompt, output_path, ...)
"""

import os
import base64
import time
import httpx
from pathlib import Path
from typing import Optional, Callable


class GenerationManager:
    """统一生成管理器 — 图片和视频的单一入口"""

    def __init__(self, config: dict):
        self.config = config
        self._http_client = httpx.Client(timeout=300.0)

    @property
    def image_config(self) -> dict:
        return self.config.get("image", {})

    @property
    def video_config(self) -> dict:
        return self.config.get("video", {})

    # ========== 图片生成 ==========

    def generate_image(
        self,
        prompt: str,
        output_path: str,
        reference_image: Optional[str] = None,
        denoise: float = 0.6,
        reference_images: Optional[list] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> tuple[bool, str, str]:
        """生成图片，保存到 output_path

        Returns:
            (success, local_path_or_url, message)
            - local_path_or_url: 成功时为本地路径；如果 provider 返回公网URL也会在 message 中包含
        """
        provider = self.image_config.get("provider", "comfyui")
        base_url = self.image_config.get("base_url", "")
        api_key = self.image_config.get("api_key", "")
        model = self.image_config.get("model", "")
        size = self.image_config.get("size", "1024x1024")
        quality = self.image_config.get("quality", "standard")

        try:
            if provider in ("comfyui", "kontext"):
                return self._generate_comfyui_family(
                    provider, prompt, output_path,
                    reference_image, denoise, reference_images,
                )
            elif provider == "sd":
                return self._generate_sd(
                    prompt, output_path, reference_image, denoise,
                )
            elif provider in ("dalle", "flux", "agnes"):
                return self._generate_openai_compatible(
                    provider, prompt, output_path, size, quality, api_key, base_url, model,
                    reference_images=reference_images,
                )
            else:
                return False, "", f"不支持的图片 provider: {provider}"
        except Exception as e:
            return False, "", str(e)

    def _generate_comfyui_family(
        self, provider: str, prompt: str, output_path: str,
        reference_image: Optional[str], denoise: float,
        reference_images: Optional[list],
    ) -> tuple[bool, str, str]:
        """ComfyUI / Kontext 系列"""
        from .comfyui_client import ComfyUIClient
        base_url = self.image_config.get("base_url", "")
        comfy = ComfyUIClient(base_url)
        project_root = Path(__file__).parent.parent

        if provider == "kontext":
            workflow_path = project_root / "workflows" / "flux_kontext_api.json"
            refs = reference_images or ([reference_image] if reference_image else [])
            if not refs:
                return False, "", "Kontext 模式需要至少一张参考图"
            return comfy.generate_kontext(
                workflow_path=str(workflow_path),
                reference_images=refs,
                prompt=prompt,
                output_path=output_path,
                guidance=3.5,
                steps=20,
            ) + ("",)  # 补齐 3 元组
        else:
            workflow_path = project_root / "workflows" / "flux_img2img_api.json"
            if not workflow_path.exists():
                return False, "", f"工作流文件不存在: {workflow_path}"
            result = comfy.generate_img2img(
                workflow_path=str(workflow_path),
                reference_image=reference_image or "",
                prompt=prompt,
                output_path=output_path,
                denoise=denoise if reference_image else 1.0,
            )
            # comfy 返回 2 元组，补齐为 3 元组
            if len(result) == 2:
                ok, msg = result
                return ok, output_path if ok else "", msg
            return result

    def _generate_sd(
        self, prompt: str, output_path: str,
        reference_image: Optional[str], denoise: float,
    ) -> tuple[bool, str, str]:
        """Stable Diffusion WebUI"""
        base_url = self.image_config.get("base_url", "")
        if reference_image:
            url = f"{base_url}/sdapi/v1/img2img"
            with open(reference_image, "rb") as f:
                init_images = [base64.b64encode(f.read()).decode("utf-8")]
            payload = {
                "prompt": prompt,
                "negative_prompt": "text, watermark, logo, signature, words, letters, symbols, low quality, blurry, distorted",
                "init_images": init_images,
                "denoising_strength": denoise,
                "steps": 30, "width": 1024, "height": 1024,
                "cfg_scale": 7, "sampler_name": "DPM++ 2M Karras",
            }
        else:
            url = f"{base_url}/sdapi/v1/txt2img"
            payload = {
                "prompt": prompt,
                "negative_prompt": "low quality, blurry, distorted, ugly, text, watermark",
                "steps": 30, "width": 1024, "height": 1024,
                "cfg_scale": 7, "sampler_name": "DPM++ 2M Karras",
            }

        resp = self._http_client.post(url, json=payload, timeout=300.0)
        resp.raise_for_status()
        data = resp.json()
        image_b64 = data["images"][0]
        image_bytes = base64.b64decode(image_b64)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return True, output_path, "生成成功"

    def _generate_openai_compatible(
        self, provider: str, prompt: str, output_path: str,
        size: str, quality: str, api_key: str, base_url: str, model: str,
        reference_images: Optional[list] = None,
    ) -> tuple[bool, str, str]:
        """DALL-E / Flux / Agnes 等 OpenAI 兼容图片 API

        Agnes 返回公网 URL（下载到本地），DALL-E 返回 b64_json。
        Agnes 支持图生图：通过 extra_body.image 传参考图 data URI。
        """
        # 有参考图时，在 prompt 中加入引导语
        effective_prompt = prompt
        if reference_images:
            effective_prompt = prompt + " Keep the product appearance, color, shape and texture consistent with the reference image."

        url = f"{base_url.rstrip('/')}/images/generations"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "prompt": effective_prompt,
            "n": 1,
            "size": size,
        }
        if provider == "agnes":
            # Agnes 支持图生图：通过 extra_body.image 传参考图（data URI 列表）
            if reference_images:
                image_data_uris = []
                for ref_path in reference_images[:1]:  # 目前只传第一张
                    try:
                        with open(ref_path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("ascii")
                        ext = Path(ref_path).suffix.lower().lstrip(".")
                        if ext == "jpg":
                            ext = "jpeg"
                        data_uri = f"data:image/{ext};base64,{b64}"
                        image_data_uris.append(data_uri)
                    except Exception:
                        pass
                if image_data_uris:
                    payload["extra_body"] = {
                        "image": image_data_uris,
                        "response_format": "url",
                    }
        else:
            payload["response_format"] = "b64_json"
        if provider in ("dalle", "flux"):
            payload["quality"] = quality

        resp = self._http_client.post(url, json=payload, headers=headers, timeout=300.0)
        resp.raise_for_status()
        data = resp.json()
        item = data["data"][0]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if item.get("b64_json"):
            image_bytes = base64.b64decode(item["b64_json"])
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            return True, output_path, "生成成功"
        elif item.get("url"):
            image_url = item["url"]
            # 下载到本地
            img_resp = self._http_client.get(image_url)
            img_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
            return True, output_path, f"生成成功（公网URL: {image_url}）"
        else:
            return False, "", f"未获取到图片数据: {data}"

    # ========== 视频生成 ==========

    def generate_video(
        self,
        prompt: str,
        output_path: str,
        image_url: Optional[str] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> tuple[bool, str]:
        """生成视频，保存到 output_path

        Returns:
            (success, message_or_path)
        """
        provider = self.video_config.get("provider", "agnes")
        if provider != "agnes":
            return False, f"不支持的视频 provider: {provider}"

        return self._generate_agnes_video(prompt, output_path, image_url, on_progress)

    def _generate_agnes_video(
        self,
        prompt: str,
        output_path: str,
        image_url: Optional[str],
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> tuple[bool, str]:
        """Agnes AI 视频生成（异步任务）"""
        base_url = self.video_config.get("base_url", "").rstrip("/")
        api_key = self.video_config.get("api_key", "")
        model = self.video_config.get("model", "agnes-video-v2.0")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # 1. 创建任务
        payload = {
            "model": model,
            "prompt": prompt,
            "width": self.video_config.get("width", 1024),
            "height": self.video_config.get("height", 1024),
            "num_frames": self.video_config.get("num_frames", 121),
            "frame_rate": self.video_config.get("frame_rate", 24),
        }
        if image_url:
            payload["image"] = image_url
        neg = self.video_config.get("negative_prompt", "")
        if neg:
            payload["negative_prompt"] = neg

        resp = self._http_client.post(f"{base_url}/videos", json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
        task = resp.json()

        task_id = task.get("task_id") or task.get("id", "")
        if not task_id:
            return False, f"未获取到 task_id: {task}"

        if on_progress:
            on_progress(0, task.get("status", "queued"))

        # 2. 轮询
        poll_interval = float(self.video_config.get("poll_interval", 5))
        timeout = float(self.video_config.get("timeout", 600))
        elapsed = 0.0
        while elapsed < timeout:
            resp = self._http_client.get(f"{base_url}/videos/{task_id}", headers=headers, timeout=30.0)
            resp.raise_for_status()
            result = resp.json()
            status = result.get("status", "unknown")
            progress = result.get("progress", 0)

            if on_progress:
                on_progress(progress, status)

            if status in ("completed", "succeeded"):
                # 3. 获取视频 URL
                video_url = result.get("remixed_from_video_id") or result.get("video_url") or result.get("url", "")
                if not video_url:
                    metadata = result.get("metadata", {})
                    video_url = metadata.get("url", "")
                if not video_url:
                    return False, f"视频生成完成但未找到 URL: {result}"

                # 4. 下载
                vresp = self._http_client.get(video_url, timeout=120.0)
                vresp.raise_for_status()
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(vresp.content)
                return True, output_path

            if status in ("failed", "error"):
                return False, f"视频生成失败: {result}"

            time.sleep(poll_interval)
            elapsed += poll_interval

        return False, f"视频生成超时（{timeout}秒）"

    # ========== 公网图片 URL（供视频图生模式用）==========

    def generate_image_url(
        self,
        prompt: str,
        size: str = "1024x1024",
    ) -> tuple[bool, str, str]:
        """生成图片但只返回公网 URL（不下载），供视频图生模式使用

        仅适用于返回公网 URL 的 provider（如 Agnes）。
        对于本地 provider（ComfyUI/SD），需要先保存图片再上传图床（暂不支持）。

        Returns:
            (success, image_url, message)
        """
        provider = self.image_config.get("provider", "comfyui")
        base_url = self.image_config.get("base_url", "")
        api_key = self.image_config.get("api_key", "")
        model = self.image_config.get("model", "")

        if provider == "agnes":
            url = f"{base_url.rstrip('/')}/images/generations"
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            payload = {
                "model": model or "agnes-image-2.1-flash",
                "prompt": prompt,
                "size": size,
            }
            # 不传 response_format，Agnes 会自动返回 URL
            resp = self._http_client.post(url, json=payload, headers=headers, timeout=300.0)
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0].get("url", "")
            if image_url:
                return True, image_url, "图片生成成功"
            return False, "", f"未获取到图片URL: {data}"
        else:
            return False, "", f"当前 provider ({provider}) 不支持直接返回公网URL，请切换为 agnes 或手动提供图片URL"

    # ========== 测试连接 ==========

    def test_image_connection(self) -> tuple[bool, str]:
        """测试图片 provider 连接"""
        provider = self.image_config.get("provider", "comfyui")
        base_url = self.image_config.get("base_url", "")
        api_key = self.image_config.get("api_key", "")

        try:
            if provider in ("comfyui", "kontext"):
                from .comfyui_client import ComfyUIClient
                comfy = ComfyUIClient(base_url)
                return comfy.test_connection()
            elif provider == "sd":
                resp = self._http_client.get(f"{base_url}/sdapi/v1/options", timeout=10.0)
                resp.raise_for_status()
                return True, "SD WebUI 连接成功"
            elif provider in ("dalle", "flux", "agnes"):
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = self._http_client.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    return True, f"{provider} 连接成功"
                return False, f"HTTP {resp.status_code}"
            return False, f"未知 provider: {provider}"
        except Exception as e:
            return False, str(e)

    def test_video_connection(self) -> tuple[bool, str]:
        """测试视频 provider 连接"""
        provider = self.video_config.get("provider", "agnes")
        base_url = self.video_config.get("base_url", "")
        api_key = self.video_config.get("api_key", "")

        try:
            if provider == "agnes":
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = self._http_client.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    return True, "Agnes 视频 API 连接成功"
                return False, f"HTTP {resp.status_code}"
            return False, f"未知的视频 provider: {provider}"
        except Exception as e:
            return False, str(e)

    def close(self):
        self._http_client.close()
