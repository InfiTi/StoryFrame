"""ComfyUI 工作流客户端

通过 API 调用 ComfyUI 工作流，支持 img2img。
"""

import json
import time
import random
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional
import httpx


class ComfyUIClient:
    """ComfyUI API 客户端"""

    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip("/")

    def _post_json(self, path: str, data: dict) -> dict:
        """POST JSON 请求"""
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"连接失败: {e.reason}")

    def _get_json(self, path: str) -> dict:
        """GET JSON 请求"""
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"连接失败: {e.reason}")

    def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            data = self._get_json("/system_stats")
            return True, f"ComfyUI 已连接，设备: {data.get('devices', [{}])[0].get('name', 'unknown')}"
        except Exception as e:
            return False, str(e)

    def upload_image(self, image_path: str) -> str:
        """上传图片到 ComfyUI input 目录，返回文件名"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        with open(path, "rb") as f:
            resp = httpx.post(
                f"{self.base_url}/upload/image",
                files={"image": (path.name, f, "image/jpeg")},
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("name", path.name)

    def queue_prompt(self, workflow: dict) -> str:
        """提交工作流到队列，返回 prompt_id"""
        data = {"prompt": workflow}
        result = self._post_json("/prompt", data)
        if "error" in result:
            raise RuntimeError(f"工作流错误: {result['error']}")
        return result.get("prompt_id", "")

    def get_history(self, prompt_id: str, timeout: int = 300) -> Optional[dict]:
        """轮询获取任务结果"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                history = self._get_json(f"/history/{prompt_id}")
                if prompt_id in history:
                    return history[prompt_id]
            except Exception:
                pass
            time.sleep(2)
        return None

    def download_image(self, filename: str, subfolder: str, output_path: str):
        """下载生成的图片"""
        params = {"filename": filename}
        if subfolder:
            params["subfolder"] = subfolder
        resp = httpx.get(f"{self.base_url}/view", params=params, timeout=60)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)

    def _fill_workflow_common(self, workflow: dict, uploaded_name: str,
                              prompt: str, actual_seed: int,
                              denoise: float, width: int, height: int):
        """填充工作流参数（通用逻辑）"""
        for node_id, node in workflow.items():
            cls = node.get("class_type", "")
            inputs = node.get("inputs", {})

            if cls == "LoadImage":
                inputs["image"] = uploaded_name

            elif cls == "CheckpointLoaderSimple":
                pass

            elif cls == "CLIPTextEncode":
                old_text = inputs.get("text", "")
                if old_text == "":
                    full_prompt = f"{prompt}, no text, no words, no letters, no logo, no watermark, no label"
                    inputs["text"] = full_prompt

            elif cls == "KSampler":
                inputs["seed"] = actual_seed
                inputs["denoise"] = denoise

            elif cls == "EmptyLatentImage":
                inputs["width"] = width
                inputs["height"] = height

            elif cls == "EmptySD3LatentImage":
                inputs["width"] = width
                inputs["height"] = height

    def _wait_and_download(self, workflow: dict, actual_seed: int,
                           output_path: str) -> tuple[bool, str]:
        """提交工作流、等待完成、下载图片（通用逻辑）"""
        prompt_id = self.queue_prompt(workflow)
        history = self.get_history(prompt_id, timeout=600)
        if not history:
            return False, "生成超时（600秒）"

        status = history.get("status", {})
        if status.get("status_str") == "error":
            msgs = status.get("messages", [])
            return False, f"生成失败: {msgs}"

        outputs = history.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    filename = img.get("filename", "output.png")
                    subfolder = img.get("subfolder", "")
                    self.download_image(filename, subfolder, output_path)
                    return True, f"生成成功 (seed={actual_seed})"

        return False, "未找到输出图片"

    def generate_img2img(
        self,
        workflow_path: str,
        reference_image: str,
        prompt: str,
        output_path: str,
        denoise: float = 0.4,
        seed: int = -1,
        width: int = 1024,
        height: int = 1024,
    ) -> tuple[bool, str]:
        """
        图生图：用参考图 + 提示词生成图片（原 img2img 方式）
        """
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

            uploaded_name = self.upload_image(reference_image)
            actual_seed = seed if seed >= 0 else random.randint(0, 2**32 - 1)

            self._fill_workflow_common(workflow, uploaded_name, prompt,
                                       actual_seed, denoise, width, height)

            return self._wait_and_download(workflow, actual_seed, output_path)

        except Exception as e:
            return False, str(e)

    def generate_kontext(
        self,
        workflow_path: str,
        reference_images: list,
        prompt: str,
        output_path: str,
        guidance: float = 3.5,
        steps: int = 20,
        seed: int = -1,
        width: int = 1024,
        height: int = 1024,
    ) -> tuple[bool, str]:
        """
        使用 Flux Kontext 模型生成图片
        Kontext 专门做图像编辑，输入参考图 + 文字指令，保持主体一致性

        工作流结构（flux_kontext_api.json）:
            LoadImage → FluxKontextImageScale → VAEEncode → ReferenceLatent → FluxGuidance
            EmptySD3LatentImage → KSampler (denoise=1.0, 从空白 latent 生成)
            ConditioningZeroOut 作为负面提示词

        参数:
            workflow_path: Kontext 工作流 JSON 路径
            reference_images: 参考图路径列表（至少1张）
            prompt: 编辑指令/提示词（英文）
            output_path: 输出图片路径
            guidance: Flux 引导强度（推荐 2.5-4.0）
            steps: 采样步数（推荐 20）
            seed: 随机种子，-1 为随机
            width: 输出图片宽度
            height: 输出图片高度
        """
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

            actual_seed = seed if seed >= 0 else random.randint(0, 2**32 - 1)

            if not reference_images:
                return False, "Kontext 需要至少一张参考图"

            uploaded_name = self.upload_image(reference_images[0])

            for node_id, node in workflow.items():
                cls = node.get("class_type", "")
                inputs = node.get("inputs", {})

                if cls == "LoadImage":
                    inputs["image"] = uploaded_name

                elif cls == "CLIPTextEncode":
                    old_text = inputs.get("text", "")
                    if old_text == "":
                        full_prompt = f"{prompt}, no text, no words, no letters, no logo, no watermark, no label"
                        inputs["text"] = full_prompt

                elif cls == "FluxGuidance":
                    inputs["guidance"] = guidance

                elif cls == "KSampler":
                    inputs["seed"] = actual_seed
                    inputs["steps"] = steps
                    inputs["denoise"] = 1.0

                elif cls == "EmptySD3LatentImage":
                    inputs["width"] = width
                    inputs["height"] = height

            return self._wait_and_download(workflow, actual_seed, output_path)

        except Exception as e:
            return False, str(e)
