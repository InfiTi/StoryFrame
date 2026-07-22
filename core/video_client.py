"""Agnes AI 视频/图片生成客户端

视频异步任务模式：
1. POST /v1/videos 创建任务 → 拿 task_id
2. GET /v1/videos/{task_id} 轮询结果 → 拿到视频 URL
3. 下载视频到本地

图片生成（同步）：
POST /v1/images/generations → 直接返回图片 URL
"""

import time
import httpx
import os
import base64
from pathlib import Path
from typing import Optional, Callable


class VideoClient:
    """Agnes AI 视频生成客户端"""

    def __init__(self, base_url: str, api_key: str, model: str = "agnes-video-v2.0"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=300.0)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def create_task(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_frames: int = 121,
        frame_rate: int = 24,
        negative_prompt: str = "",
        seed: Optional[int] = None,
        extra_body: Optional[dict] = None,
    ) -> dict:
        """创建视频生成任务，返回任务信息

        Returns:
            {
                "task_id": "task_xxx",
                "video_id": "video_xxx",
                "status": "queued",
                "seconds": "10.0",
                "size": "1280x768",
                ...
            }
        """
        url = f"{self.base_url}/videos"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "frame_rate": frame_rate,
        }

        if image_url:
            payload["image"] = image_url

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        if seed is not None:
            payload["seed"] = seed

        if extra_body:
            payload["extra_body"] = extra_body

        resp = self.client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_result(self, task_id: str) -> dict:
        """查询视频生成结果（GET /v1/videos/{task_id}）

        Returns:
            {
                "status": "completed" | "in_progress" | "queued" | "failed" | ...,
                "progress": 0-100,
                "remixed_from_video_id": "https://...",  # 完成时的视频 URL
                ...
            }
        """
        url = f"{self.base_url}/videos/{task_id}"
        resp = self.client.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def wait_for_result(
        self,
        video_id: str,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> dict:
        """轮询等待视频生成完成

        Args:
            video_id: 视频ID
            poll_interval: 轮询间隔（秒）
            timeout: 最大等待时间（秒）
            on_progress: 进度回调 (progress, status)

        Returns:
            完成时的结果 dict

        Raises:
            TimeoutError: 超时
            RuntimeError: 生成失败
        """
        elapsed = 0.0
        while elapsed < timeout:
            result = self.get_result(video_id)
            status = result.get("status", "unknown")
            progress = result.get("progress", 0)

            if on_progress:
                on_progress(progress, status)

            if status == "completed" or status == "succeeded":
                return result
            if status == "failed" or status == "error":
                raise RuntimeError(f"视频生成失败: {result}")

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"视频生成超时（{timeout}秒）")

    def download_video(self, video_url: str, output_path: str) -> str:
        """下载视频到本地"""
        resp = self.client.get(video_url)
        resp.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)

        return output_path

    def generate(
        self,
        prompt: str,
        output_path: str,
        image_url: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_frames: int = 121,
        frame_rate: int = 24,
        negative_prompt: str = "",
        seed: Optional[int] = None,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> tuple[bool, str]:
        """一步到位：创建任务 → 等待完成 → 下载视频

        Returns:
            (success, message_or_path)
        """
        try:
            # 1. 创建任务
            task = self.create_task(
                prompt=prompt,
                image_url=image_url,
                width=width,
                height=height,
                num_frames=num_frames,
                frame_rate=frame_rate,
                negative_prompt=negative_prompt,
                seed=seed,
            )

            task_id = task.get("task_id") or task.get("id", "")
            if not task_id:
                return False, f"未获取到 task_id: {task}"

            if on_progress:
                on_progress(0, task.get("status", "queued"))

            # 2. 等待完成
            result = self.wait_for_result(
                video_id=task_id,
                poll_interval=poll_interval,
                timeout=timeout,
                on_progress=on_progress,
            )

            # 3. 获取视频 URL（文档字段为 remixed_from_video_id）
            video_url = result.get("remixed_from_video_id") or result.get("video_url") or result.get("url", "")
            if not video_url:
                # 尝试从 metadata 中获取
                metadata = result.get("metadata", {})
                video_url = metadata.get("url", "")

            if not video_url:
                return False, f"视频生成完成但未找到 URL: {result}"

            # 4. 下载
            self.download_video(video_url, output_path)
            return True, output_path

        except Exception as e:
            return False, str(e)

    def test_connection(self) -> tuple[bool, str]:
        """测试连接（创建一个最简任务验证 API Key）"""
        try:
            headers = self._headers()
            # 用 GET /v1/models 测试连接
            url = f"{self.base_url}/models"
            resp = self.client.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                return True, "Agnes AI 连接成功"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return False, str(e)

    def close(self):
        self.client.close()


class AgnesImageClient:
    """Agnes AI 图片生成客户端（同步）

    用于在图生视频流程中，先用 Agnes 生成图片拿到公网 URL，再传给视频生成。
    """

    def __init__(self, base_url: str, api_key: str, model: str = "agnes-image-2.1-flash"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=120.0)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        extra_body: Optional[dict] = None,
    ) -> tuple[bool, str, str]:
        """生成图片，返回 (成功, 图片URL, 信息)

        Args:
            prompt: 图片生成提示词
            size: 输出尺寸，如 1024x1024, 1024x768, 768x1024
            extra_body: 高级参数（如图生图时的 image 数组）

        Returns:
            (success, image_url, message)
        """
        url = f"{self.base_url}/images/generations"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "response_format": "url",
        }

        if extra_body:
            payload["extra_body"] = extra_body

        try:
            resp = self.client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0].get("url", "")
            if not image_url:
                return False, "", f"未获取到图片URL: {data}"
            return True, image_url, "生成成功"
        except Exception as e:
            return False, "", str(e)

    def download_image(self, image_url: str, output_path: str) -> str:
        """下载图片到本地"""
        resp = self.client.get(image_url)
        resp.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return output_path

    def generate_and_download(
        self,
        prompt: str,
        output_path: str,
        size: str = "1024x1024",
        extra_body: Optional[dict] = None,
    ) -> tuple[bool, str, str]:
        """生成图片并下载到本地，返回 (成功, 图片URL或本地路径, 信息)

        Returns:
            (success, image_url_or_path, message)
            如果成功，message 中包含公网 URL（供视频生成使用）
        """
        ok, image_url, msg = self.generate_image(prompt, size=size, extra_body=extra_body)
        if not ok:
            return False, "", msg

        try:
            self.download_image(image_url, output_path)
            # 返回公网 URL 供视频生成使用
            return True, image_url, f"图片已下载到 {output_path}，公网URL: {image_url}"
        except Exception as e:
            return False, image_url, f"图片生成成功但下载失败: {e}"

    def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            url = f"{self.base_url}/models"
            resp = self.client.get(url, headers=self._headers(), timeout=10.0)
            if resp.status_code == 200:
                return True, "Agnes AI 图片API连接成功"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return False, str(e)

    def close(self):
        self.client.close()
