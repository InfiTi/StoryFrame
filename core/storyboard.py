"""分镜脚本生成核心逻辑"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from .templates import StyleTemplate
from .llm_client import LLMClient


@dataclass
class StoryboardFrame:
    """单帧分镜"""
    frame: int                    # 帧序号（从1开始）
    duration: float               # 该帧时长（秒）
    image_prompt: str             # 图片提示词（英文，用于 AI 生图）
    camera_motion: str            # 镜头运动描述（英文，用于图生视频）
    description: str              # 画面内容中文描述
    image_path: Optional[str] = None  # 生成的图片路径


@dataclass
class Storyboard:
    """完整分镜脚本"""
    product_name: str             # 产品名称
    product_desc: str             # 产品描述
    style_name: str               # 风格名称
    frames: List[StoryboardFrame] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "product_name": self.product_name,
            "product_desc": self.product_desc,
            "style_name": self.style_name,
            "frames": [asdict(f) for f in self.frames],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# LLM System Prompt
SYSTEM_PROMPT = """你是一个专业的零食带货短视频分镜设计师。

你的任务：根据产品信息和风格模板，设计 10-15 秒短视频的分镜脚本。

每个分镜帧需要包含：
1. image_prompt: 用于 AI 生图的英文提示词，需要包含产品外观、场景、光线、构图、风格关键词等细节
2. camera_motion: 用于图生视频的英文镜头运动描述，描述镜头如何移动（如 slow dolly in, gentle pan 等）
3. description: 画面内容的中文描述（简短说明这一帧展示什么）
4. duration: 该帧持续时间（秒），所有帧时长之和应为 10-15 秒

要求：
- 图片提示词必须用英文，要具体、有画面感
- 镜头运动描述必须用英文，描述镜头的运动方向和速度
- 每帧的图片提示词应能独立生成一张完整的图片
- 分镜之间要有视觉连贯性，但要保持每帧独立可生成
- 突出零食的卖点：外观、质感、包装、食用场景等
- 注意：生成的图片后续会用于图生视频，所以画面主体要清晰、构图要稳定

输出格式：严格的 JSON 数组，不要添加任何其他文字。
```json
[
  {
    "frame": 1,
    "duration": 2.5,
    "image_prompt": "...",
    "camera_motion": "...",
    "description": "..."
  }
]
```"""


def build_user_prompt(
    product_name: str,
    product_desc: str,
    selling_points: str,
    template: StyleTemplate,
    frame_count: int,
    total_duration: int,
) -> str:
    """构建发送给 LLM 的用户提示词"""
    style_words = ", ".join(template.image_style_words)
    camera_words = ", ".join(template.camera_style_words)

    prompt = f"""请为以下零食产品设计 {frame_count} 帧分镜脚本。

【产品信息】
产品名称：{product_name}
产品描述：{product_desc}
卖点：{selling_points}

【风格模板】
风格名称：{template.name}
风格描述：{template.description}
图片风格关键词：{style_words}
镜头风格关键词：{camera_words}
节奏：{template.pacing}

【要求】
- 分镜数：{frame_count} 帧
- 总时长：{total_duration} 秒
- 每帧时长建议：{total_duration / frame_count:.1f} 秒
- 图片提示词中必须融入风格关键词
- 镜头运动描述中必须融入镜头风格关键词
- 第1帧通常是产品全景/氛围建立，最后一帧通常是品牌/产品定格

请输出 JSON 数组。"""

    return prompt


def generate_storyboard(
    llm: LLMClient,
    product_name: str,
    product_desc: str,
    selling_points: str,
    template: StyleTemplate,
    frame_count: int,
    total_duration: int,
) -> Storyboard:
    """调用 LLM 生成分镜脚本"""

    user_prompt = build_user_prompt(
        product_name, product_desc, selling_points,
        template, frame_count, total_duration,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    result = llm.chat_json(messages, temperature=0.8)

    frames = []
    for item in result:
        frame = StoryboardFrame(
            frame=item.get("frame", len(frames) + 1),
            duration=item.get("duration", total_duration / frame_count),
            image_prompt=item.get("image_prompt", ""),
            camera_motion=item.get("camera_motion", ""),
            description=item.get("description", ""),
        )
        frames.append(frame)

    return Storyboard(
        product_name=product_name,
        product_desc=product_desc,
        style_name=template.name,
        frames=frames,
    )
