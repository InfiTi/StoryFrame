"""分镜脚本生成核心逻辑

面向「图生视频」优化：提示词重点描述产品的物理质感和动态趋势，
让图生视频模型能理解"这个东西怎么动"。
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from .templates import StyleTemplate
from .llm_client import LLMClient
from .product_parser import ProductInfo, build_texture_description


@dataclass
class StoryboardFrame:
    """单帧分镜"""
    frame: int                    # 帧序号（从1开始）
    duration: float               # 该帧时长（秒）
    image_prompt: str             # 图片提示词（英文，用于 AI 生图）
    camera_motion: str            # 镜头运动描述（英文，用于图生视频）
    motion_hint: str              # 画面内动态提示（英文，描述产品怎么动）
    description: str              # 画面内容中文描述
    image_path: Optional[str] = None  # 生成的图片路径


@dataclass
class Storyboard:
    """完整分镜脚本"""
    product_name: str
    product_desc: str
    style_name: str
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


# LLM System Prompt —— 面向图生视频
SYSTEM_PROMPT = """你是一个专业的零食产品分镜设计师，专门为「图生视频」工作流设计分镜。

你的核心任务：为每一帧生成一张产品图片的提示词，这张图片后续会被 AI 变成视频。
所以提示词必须描述清楚：产品长什么样、什么材质、什么质感、画面里正在发生什么物理动作。

关键原则：
1. 图片提示词必须是英文，描述的是「一帧静态画面」，但要让图生视频模型能看出动态趋势
2. 必须包含产品的物理质感描述（crispy/crunchy/soft/chewy 等），这决定了视频里产品怎么动
3. 必须包含产品的视觉特征（颜色、形状、截面、层次等）
4. 光线和构图要服务于「让产品看起来高级」
5. 每帧画面主体是产品本身，不要加人物
6. motion_hint 字段描述这一帧在视频中应该有什么动态（如碎裂、拉丝、掉落、飘散等）

⚠️ 重要约束：
- 直接输出 JSON 数组，不要输出任何思考过程、分析、解释
- 不要输出 ```json``` 代码块标记，直接输出 [ 开头的 JSON
- image_prompt 控制在 60-100 词，不要写太长
- motion_hint 控制在 20-40 词
- description 控制在 15-25 字

每帧输出字段：
- frame: 帧序号（从1开始）
- duration: 该帧持续秒数
- image_prompt: 英文，用于 AI 生图的完整提示词（产品外观+质感+光线+构图+风格）
- camera_motion: 英文，镜头运动（如 slow dolly in, macro push-in, gentle orbit）
- motion_hint: 英文，画面内产品的动态趋势
- description: 中文，简短说明这一帧展示什么

输出格式示例：
[
  {
    "frame": 1,
    "duration": 3.0,
    "image_prompt": "...",
    "camera_motion": "...",
    "motion_hint": "...",
    "description": "..."
  }
]
"""


def build_user_prompt(
    product_name: str,
    product_desc: str,
    selling_points: str,
    template: StyleTemplate,
    frame_count: int,
    total_duration: int,
    product_info: Optional[ProductInfo] = None,
) -> str:
    """构建发送给 LLM 的用户提示词"""

    style_words = ", ".join(template.image_style_words)
    camera_words = ", ".join(template.camera_style_words)

    # 如果有解析过的商品信息，用更丰富的上下文
    if product_info:
        texture_desc = build_texture_description(product_info)
        texture_cn = "、".join(product_info.texture_keywords[:10]) if product_info.texture_keywords else "未知"

        # 提取高转化文案中的卖点表述
        copy_hints = ""
        if product_info.top_copies:
            top3 = product_info.top_copies[:3]
            copy_hints = "\n".join(f"  - {c}" for c in top3)

        # 提取评价关键词
        review_tags = "、".join(product_info.review_keywords[:8]) if product_info.review_keywords else ""

        # 规格信息
        spec_info = ""
        if product_info.specs:
            spec_info = f"\n产品规格：{product_info.specs[0]}"

        prompt = f"""请为以下零食产品设计 {frame_count} 帧分镜脚本，用于图生视频。

【产品信息】
产品名称：{product_name}
产品描述：{product_desc}
质感特征（中文）：{texture_cn}
质感视觉描述（英文）：{texture_desc}
卖点：{selling_points}{spec_info}
"""

        if review_tags:
            prompt += f"用户评价关键词：{review_tags}\n"

        if copy_hints:
            prompt += f"\n高转化文案参考（提炼卖点方向）：\n{copy_hints}\n"

        prompt += f"""
【风格模板】
风格名称：{template.name}
风格描述：{template.description}
图片风格关键词：{style_words}
镜头风格关键词：{camera_words}
节奏：{template.pacing}

【分镜要求】
- 分镜数：{frame_count} 帧
- 总时长：{total_duration} 秒
- 每帧时长建议：{total_duration / frame_count:.1f} 秒
- 图片提示词中必须融入风格关键词
- 镜头运动描述中必须融入镜头风格关键词
- motion_hint 必须基于产品质感特征来设计动态（如酥脆→碎裂掉渣、柔软→轻压回弹、Q弹→拉扯回弹）
- 第1帧：产品全景/氛围建立，展示包装和整体外观
- 中间帧：聚焦产品质感细节，展示截面/层次/质地
- 最后一帧：产品定格特写，展示最诱人的状态

请输出 JSON 数组。"""
        return prompt

    # 没有商品信息时的基础 prompt
    prompt = f"""请为以下零食产品设计 {frame_count} 帧分镜脚本，用于图生视频。

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

【分镜要求】
- 分镜数：{frame_count} 帧
- 总时长：{total_duration} 秒
- 每帧时长建议：{total_duration / frame_count:.1f} 秒
- 图片提示词中必须融入风格关键词
- 镜头运动描述中必须融入镜头风格关键词
- motion_hint 必须基于产品质感特征来设计动态
- 第1帧：产品全景/氛围建立
- 中间帧：聚焦产品质感细节
- 最后一帧：产品定格特写

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
    product_info: Optional[ProductInfo] = None,
    on_chunk=None,
) -> Storyboard:
    """调用 LLM 生成分镜脚本，支持流式回调"""

    user_prompt = build_user_prompt(
        product_name, product_desc, selling_points,
        template, frame_count, total_duration,
        product_info=product_info,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    result = llm.chat_json(messages, temperature=0.8, on_chunk=on_chunk)

    # 保存调试文件
    debug_dir = Path("outputs") / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    debug_file = debug_dir / f"llm_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2))

    frames = []
    for item in result:
        frame = StoryboardFrame(
            frame=item.get("frame", len(frames) + 1),
            duration=item.get("duration", total_duration / frame_count),
            image_prompt=item.get("image_prompt", ""),
            camera_motion=item.get("camera_motion", ""),
            motion_hint=item.get("motion_hint", ""),
            description=item.get("description", ""),
        )
        frames.append(frame)

    return Storyboard(
        product_name=product_name,
        product_desc=product_desc,
        style_name=template.name,
        frames=frames,
    )
