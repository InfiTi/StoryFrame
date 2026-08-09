"""分镜脚本生成核心逻辑

面向「图生视频」优化：提示词重点描述产品的物理质感和动态趋势，
让图生视频模型能理解"这个东西怎么动"。
"""

import json
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from .templates import StyleTemplate
from .prompt_loader import get_system_prompt, get_user_prompt, get_plan_prompt, get_frame_prompt, detect_texture_category, get_preset_sequence, get_preset_dimensions_str, get_preset_transition, SHOT_PRESETS
from .llm_client import LLMClient
from .product_parser import ProductInfo, build_texture_description


@dataclass
class StoryboardFrame:
    """单帧分镜"""
    frame: int                        # 帧序号（从1开始）
    duration: float                   # 该帧时长（秒）
    image_prompt: str                 # 图片提示词（英文，用于 AI 生图）
    camera_motion: str                # 镜头运动描述（英文，用于图生视频）
    motion_hint: str                  # 画面内动态提示（英文，描述产品怎么动）
    image_prompt_cn: str = ""         # 图片提示词中文对照
    camera_motion_cn: str = ""        # 镜头运动中文对照
    motion_hint_cn: str = ""          # 画面动态中文对照
    video_prompt: str = ""            # 视频生成指令（英文，动作剧本：初始状态+运动轨迹+镜头+速度+结束状态）
    video_prompt_cn: str = ""         # 视频生成指令中文对照
    description: str = ""             # 画面内容中文描述
    transition: str = ""             # 帧间过渡方式（hard cut / whip pan / speed ramp / fade）
    motion_phase: str = ""            # 动作相位（pre-action / mid-action / post-action / static）
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
3. 必须包含产品的视觉特征（颜色、形状、截面、层次等），让生图模型能还原产品外观
4. 光线和构图要服务于「让产品看起来高级」
5. 每帧画面主体是产品本身，不要加人物
6. motion_hint 字段描述这一帧在视频中应该有什么动态（如碎裂、拉丝、掉落、飘散等）

⚠️ 重要约束：
- 提示词中禁止出现任何关于文字、logo、包装文字、标签、水印的描述
- 提示词末尾必须加上: no text, no words, no letters, no logo, no watermark, no label
- 产品外观描述要基于真实商品特征（颜色、形状、纹理、截面层次），不要虚构不存在的元素
- 如果产品有包装，只描述包装的颜色和形状，不要描述包装上的文字内容
- 直接输出 JSON 数组，不要输出任何思考过程、分析、解释
- 不要输出 ```json``` 代码块标记，直接输出 [ 开头的 JSON
- image_prompt 控制在 60-100 词，不要写太长
- motion_hint 控制在 20-40 词
- description 控制在 15-25 字

每帧输出字段（中英文对照）：
- frame: 帧序号（从1开始）
- duration: 该帧持续秒数
- image_prompt: 英文，用于 AI 生图的完整提示词（产品外观+质感+光线+构图+风格）
- image_prompt_cn: 中文，image_prompt 的中文翻译
- camera_motion: 英文，镜头运动（如 slow dolly in, macro push-in, gentle orbit）
- camera_motion_cn: 中文，镜头运动中文描述
- motion_hint: 英文，画面内产品的动态趋势
- motion_hint_cn: 中文，画面动态中文描述
- description: 中文，简短说明这一帧展示什么

输出格式示例：
[
  {
    "frame": 1,
    "duration": 3.0,
    "image_prompt": "...",
    "image_prompt_cn": "...",
    "camera_motion": "...",
    "camera_motion_cn": "...",
    "motion_hint": "...",
    "motion_hint_cn": "...",
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
    direction: str = "",
) -> str:
    """构建发送给 LLM 的用户提示词"""

    style_words = ", ".join(template.image_style_words)
    camera_words = ", ".join(template.camera_style_words)

    # 准备变量
    texture_cn = ""
    texture_desc = ""
    spec_info = ""
    review_tags = ""
    copy_hints = ""
    product_texture = ""
    flavor_tags = ""

    if product_info:
        texture_desc = build_texture_description(product_info)
        texture_cn = "、".join(product_info.texture_keywords[:10]) if product_info.texture_keywords else "未知"
        # 核心质感描述：中文质感词 + 英文视觉描述
        if product_info.texture_keywords:
            product_texture = f"{texture_cn}（{texture_desc}）"
        # 口味标签
        if product_info.flavor_tags:
            flavor_tags = "、".join(product_info.flavor_tags[:8])
        if product_info.top_copies:
            top3 = product_info.top_copies[:3]
            copy_hints = "\n".join(f"  - {c}" for c in top3)
        review_tags = "、".join(product_info.review_keywords[:8]) if product_info.review_keywords else ""
        if product_info.specs:
            spec_info = f"\n产品规格：{product_info.specs[0]}"

    # 计算帧时长分配方案
    from .prompt_loader import compute_duration_plan
    duration_plan = compute_duration_plan(frame_count, total_duration, template.pacing_strategy)

    # 尝试从外部模板加载
    prompt = get_user_prompt(
        product_name=product_name,
        product_desc=product_desc,
        selling_points=selling_points,
        template_name=template.name,
        template_desc=template.description,
        style_words=style_words,
        camera_words=camera_words,
        pacing=template.pacing,
        frame_count=frame_count,
        total_duration=total_duration,
        # 新变量
        product_texture=product_texture,
        impact_level=template.impact_level,
        pacing_strategy=template.pacing_strategy,
        bgm_style=template.bgm,
        mid_frame=max(2, frame_count - 1),
        negative_words=template.negative_words,
        duration_plan=duration_plan,
        flavor_tags=flavor_tags,
        # 兼容旧变量
        texture_cn=f"\n质感特征（中文）：{texture_cn}" if texture_cn else "",
        texture_desc=f"\n质感视觉描述（英文）：{texture_desc}" if texture_desc else "",
        spec_info=spec_info,
        review_tags=f"用户评价关键词：{review_tags}\n" if review_tags else "",
        copy_hints=f"\n高转化文案参考（提炼卖点方向）：\n{copy_hints}\n" if copy_hints else "",
        direction=f"\n【视频方向指引】\n{direction}\n" if direction else "",
    )
    if prompt:
        return prompt

    # 回退：内置提示词
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
    direction: str = "",
    on_chunk=None,
) -> Storyboard:
    """调用 LLM 生成分镜脚本，支持流式回调"""

    user_prompt = build_user_prompt(
        product_name, product_desc, selling_points,
        template, frame_count, total_duration,
        product_info=product_info,
        direction=direction,
    )

    # 构建质感描述用于系统提示词模块选择
    sys_texture = ""
    if product_info:
        if product_info.texture_keywords:
            texture_cn = "、".join(product_info.texture_keywords[:10])
            texture_desc = build_texture_description(product_info)
            sys_texture = f"{texture_cn}（{texture_desc}）"

    # 从外部加载提示词模板（模块化组装），找不到时回退到内置
    sys_prompt = get_system_prompt(product_texture=sys_texture)
    if not sys_prompt:
        sys_prompt = SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": sys_prompt},
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
            image_prompt_cn=item.get("image_prompt_cn", ""),
            camera_motion=item.get("camera_motion", ""),
            camera_motion_cn=item.get("camera_motion_cn", ""),
            motion_hint=item.get("motion_hint", ""),
            motion_hint_cn=item.get("motion_hint_cn", ""),
            video_prompt=item.get("video_prompt", ""),
            video_prompt_cn=item.get("video_prompt_cn", ""),
            description=item.get("description", ""),
            transition=item.get("transition", "none"),
            motion_phase=item.get("motion_phase", "static"),
        )
        frames.append(frame)

    return Storyboard(
        product_name=product_name,
        product_desc=product_desc,
        style_name=template.name,
        frames=frames,
    )


# ========== 两步生成：先定基调，再逐帧精生成 ==========


def _build_texture_str(product_info: Optional[ProductInfo]) -> str:
    """从 product_info 构建质感描述字符串"""
    if not product_info:
        return ""
    if product_info.texture_keywords:
        texture_cn = "、".join(product_info.texture_keywords[:10])
        texture_desc = build_texture_description(product_info)
        return f"{texture_cn}（{texture_desc}）"
    return ""


def generate_plan(
    llm: LLMClient,
    product_name: str,
    product_desc: str,
    selling_points: str,
    template: StyleTemplate,
    frame_count: int,
    total_duration: int,
    product_info: Optional[ProductInfo] = None,
    direction: str = "",
    preset_sequence: list = None,
    on_chunk=None,
) -> list:
    """第一步：生成整体基调方案（每帧只含骨架信息，不含具体提示词）"""

    plan_template = get_plan_prompt(
        frame_count=frame_count,
        total_duration=total_duration,
    )

    # 用户消息：产品信息
    style_words = ", ".join(template.image_style_words)
    camera_words = ", ".join(template.camera_style_words)
    texture_str = _build_texture_str(product_info)
    direction_line = f"\n【视频方向指引】\n{direction}\n" if direction else ""
    
    # 注入预设序列信息
    preset_info = ""
    if preset_sequence:
        preset_lines = []
        for i, pid in enumerate(preset_sequence):
            preset_lines.append(f"  - 第{i+1}帧: {pid}")
        preset_info = f"\n【预设分配方案（必须遵守）】\n" + "\n".join(preset_lines) + "\n"

    user_msg = f"""请为以下产品设计 {frame_count} 帧分镜方案。

【产品信息】
产品名称：{product_name}
产品描述：{product_desc}
卖点：{selling_points or '美味零食'}
质感：{texture_str or '未知'}

【风格】
风格名称：{template.name}
风格描述：{template.description}
图片风格关键词：{style_words}
镜头风格关键词：{camera_words}
节奏：{template.pacing}
{direction_line}{preset_info}请输出 JSON 数组。"""

    messages = [
        {"role": "system", "content": plan_template},
        {"role": "user", "content": user_msg},
    ]

    result = llm.chat_json(messages, temperature=0.7, on_chunk=on_chunk)

    # 保存调试文件
    debug_dir = Path("outputs") / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    debug_file = debug_dir / f"plan_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2))

    return result if isinstance(result, list) else []


def _build_frame_state_summary(frame: StoryboardFrame, is_prev: bool = True) -> str:
    """构建帧的物理状态摘要，用于上下文衔接
    
    返回结构化信息：画面描述 + 运镜结束状态 + 动作相位 + 过渡方式 + 产品物理状态
    比原来的简单 description + camera_motion_cn 信息量大 3 倍
    """
    role = "上一帧" if is_prev else "下一帧"
    parts = [f"【{role}物理状态摘要】"]
    
    # 1. 画面功能描述
    parts.append(f"画面：{frame.description}")
    
    # 2. 动作相位 + 物理状态
    phase = frame.motion_phase or "static"
    phase_desc = {
        "pre-action": "产品处于动作前静止状态",
        "mid-action": "产品处于动作进行中（40-60%瞬间）",
        "post-action": "产品处于动作结束后状态",
        "static": "产品静止展示",
    }.get(phase, "产品静止")
    parts.append(f"动作相位：{phase}（{phase_desc}）")
    
    # 3. 运镜状态
    camera = frame.camera_motion_cn or frame.camera_motion or ""
    if camera:
        parts.append(f"运镜：{camera}")
    
    # 4. 动态趋势（关键物理信息）
    motion = frame.motion_hint_cn or frame.motion_hint or ""
    if motion:
        parts.append(f"产品动态：{motion}")
    
    # 5. 过渡方式
    transition = frame.transition or "none"
    if transition and transition.lower() != "none":
        transition_cn = {
            "hard cut": "硬切", "whip pan": "甩镜转场", 
            "speed ramp": "变速过渡", "fade": "渐变", "morph": "形变过渡"
        }.get(transition.lower(), transition)
        if is_prev:
            parts.append(f"过渡到本帧：{transition_cn}")
        else:
            parts.append(f"本帧过渡到它：{transition_cn}")
    
    # 6. video_prompt 的结束/起始状态（最关键的物理衔接信息）
    video_text = frame.video_prompt_cn or frame.video_prompt or ""
    if video_text:
        if is_prev:
            # 提取上一帧的结束状态（句号分隔的最后一句）
            sentences = [s.strip() for s in video_text.replace('，', ',').replace('。', '.').split('.') if s.strip()]
            if len(sentences) >= 2:
                ending = sentences[-1]
                parts.append(f"结束状态：{ending}")
            elif sentences:
                parts.append(f"结束状态：{sentences[-1]}")
        else:
            # 提取下一帧的起始状态（第一个逗号/句号前的内容）
            first_clause = re.split(r'[,，.。]', video_text)
            if first_clause and first_clause[0].strip():
                parts.append(f"起始状态：{first_clause[0].strip()}")
    
    return " | ".join(parts)


def _build_plan_state_summary(plan_item: dict, is_next: bool = True) -> str:
    """构建 plan 阶段的帧状态摘要（用于尚未生成的帧）"""
    role = "下一帧" if is_next else "上一帧"
    parts = [f"【{role}方案摘要】"]
    parts.append(f"画面：{plan_item.get('description', '')}")
    parts.append(f"运镜：{plan_item.get('camera_motion_type', '')}")
    
    transition = plan_item.get('transition', 'none')
    if transition and transition.lower() != 'none':
        transition_cn = {
            "hard cut": "硬切", "whip pan": "甩镜转场",
            "speed ramp": "变速过渡", "fade": "渐变", "morph": "形变过渡"
        }.get(transition.lower(), transition)
        parts.append(f"过渡方式：{transition_cn}")
    
    parts.append(f"焦点：{plan_item.get('focus', '')}")
    
    return " | ".join(parts)


def generate_frame_detail(
    llm: LLMClient,
    frame_plan: dict,
    plan_summary: str,
    frame_count: int,
    product_name: str,
    product_desc: str,
    selling_points: str,
    template: StyleTemplate,
    product_info: Optional[ProductInfo] = None,
    prev_frame_ending: str = "",
    next_frame_starting: str = "",
    preset_id: str = "",
    preset_dimensions: str = "",
    on_chunk=None,
) -> StoryboardFrame:
    """第二步：为单帧生成完整提示词"""

    frame_num = frame_plan.get("frame", 1)
    duration = frame_plan.get("duration", 2.0)
    description = frame_plan.get("description", "")
    focus = frame_plan.get("focus", "")
    camera_type = frame_plan.get("camera_motion_type", "static hold")
    transition = frame_plan.get("transition", "none")

    texture_str = _build_texture_str(product_info)
    style_words = ", ".join(template.image_style_words)
    camera_words = ", ".join(template.camera_style_words)

    # 系统提示词：用模块化组装（核心+质感+运镜）
    sys_prompt = get_system_prompt(product_texture=texture_str)

    # 帧提示词模板
    frame_sys = get_frame_prompt(
        frame_num=frame_num,
        frame_count=frame_count,
        product_info=f"名称：{product_name}\n描述：{product_desc}\n卖点：{selling_points or '美味零食'}\n质感：{texture_str or '未知'}",
        style_name=template.name,
        style_words=style_words,
        camera_words=camera_words,
        plan_summary=plan_summary,
        duration=duration,
        frame_description=description,
        frame_focus=focus,
        frame_camera_type=camera_type,
        frame_transition=transition,
        texture_info=texture_str or '未知',
        prev_frame_ending=prev_frame_ending or '（第一帧，无上一帧）',
        next_frame_starting=next_frame_starting or '（最后一帧，无下一帧）',
        preset_id=preset_id,
        preset_dimensions=preset_dimensions,
    )

    # 组合系统提示词：模块化规则 + 帧生成指令
    full_sys = sys_prompt + "\n\n---\n\n" + frame_sys

    messages = [
        {"role": "system", "content": full_sys},
        {"role": "user", "content": f"请生成第 {frame_num} 帧的完整提示词。直接输出 JSON 对象。"},
    ]

    result = llm.chat_json(messages, temperature=0.8, on_chunk=on_chunk)

    # 兼容 list 和 dict
    if isinstance(result, list):
        result = result[0] if result else {}

    # 空结果检查：如果关键字段全部为空，记录警告
    if not result.get("image_prompt") and not result.get("motion_hint"):
        print(f"⚠️ 第 {frame_num} 帧 LLM 返回空结果，将使用空值占位")

    # 保存调试文件
    debug_dir = Path("outputs") / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    debug_file = debug_dir / f"frame_{frame_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2))

    return StoryboardFrame(
        frame=result.get("frame", frame_num),
        duration=result.get("duration", duration),
        image_prompt=result.get("image_prompt", ""),
        image_prompt_cn=result.get("image_prompt_cn", ""),
        camera_motion=result.get("camera_motion", ""),
        camera_motion_cn=result.get("camera_motion_cn", ""),
        motion_hint=result.get("motion_hint", ""),
        motion_hint_cn=result.get("motion_hint_cn", ""),
        video_prompt=result.get("video_prompt", ""),
        video_prompt_cn=result.get("video_prompt_cn", ""),
        description=result.get("description", description),
        transition=result.get("transition", transition),
        motion_phase=result.get("motion_phase", "static"),
    )


def generate_storyboard_v2(
    llm: LLMClient,
    product_name: str,
    product_desc: str,
    selling_points: str,
    template: StyleTemplate,
    frame_count: int,
    total_duration: int,
    product_info: Optional[ProductInfo] = None,
    direction: str = "",
    on_plan_chunk=None,
    on_frame_chunk=None,
    on_frame_done=None,
    on_stage=None,
) -> Storyboard:
    """两步生成分镜脚本：先定基调，再逐帧精生成
    
    回调：
    - on_plan_chunk: 基调生成流式回调
    - on_frame_chunk(frame_num, text): 逐帧生成流式回调
    - on_frame_done(frame_num, frame): 单帧完成回调
    - on_stage(stage: str): 阶段切换回调 ('plan' / 'frame:N/total')
    """
    # === 计算预设序列 ===
    texture_str = _build_texture_str(product_info)
    texture_cat = detect_texture_category(texture_str)
    preset_seq = get_preset_sequence(texture_cat, frame_count)
    
    # === 第一步：生成基调 ===
    if on_stage:
        on_stage("plan")
    plan = generate_plan(
        llm=llm,
        product_name=product_name,
        product_desc=product_desc,
        selling_points=selling_points,
        template=template,
        frame_count=frame_count,
        total_duration=total_duration,
        product_info=product_info,
        direction=direction,
        preset_sequence=preset_seq,
        on_chunk=on_plan_chunk,
    )

    if not plan:
        raise RuntimeError("基调生成失败：LLM 未返回有效方案")

    # === 用预设的运镜和过渡覆盖 plan 结果（强制约束）===
    for i, p in enumerate(plan):
        if i < len(preset_seq):
            preset = SHOT_PRESETS.get(preset_seq[i])
            if preset:
                dims = preset["dimensions"]
                # 覆盖运镜类型为预设的运镜
                p["camera_motion_type"] = dims.get("运镜", p.get("camera_motion_type", ""))
                # 覆盖过渡方式为预设的过渡（第1帧保持 none）
                if i > 0:
                    # 当前帧的 transition = 上一帧预设的“过渡到下一帧”
                    prev_preset = SHOT_PRESETS.get(preset_seq[i-1])
                    if prev_preset:
                        prev_transition = prev_preset["dimensions"].get("过渡到下一帧", "hard cut")
                        p["transition"] = prev_transition
                else:
                    p["transition"] = "none"
                # 添加 preset_id 到 plan
                p["preset_id"] = preset_seq[i]

    # 构建方案摘要（供逐帧生成时参考）
    plan_summary_lines = []
    for p in plan:
        plan_summary_lines.append(
            f"第{p.get('frame', '?')}帧 ({p.get('duration', '?')}s): "
            f"{p.get('description', '?')} | 焦点: {p.get('focus', '?')} | "
            f"运镜: {p.get('camera_motion_type', '?')} | 过渡: {p.get('transition', '?')}"
        )
    plan_summary = "\n".join(plan_summary_lines)

    # === 第二步：逐帧精生成 ===
    total_frames = len(plan)
    frames = []
    for i, frame_plan in enumerate(plan):
        frame_num = frame_plan.get("frame", i + 1)
        if on_stage:
            on_stage(f"frame:{frame_num}/{total_frames}")

        # 上下文衔接（物理状态摘要，非简单描述）
        prev_ending = ""
        next_starting = ""
        if i > 0:
            prev_frame = frames[-1] if frames else None
            if prev_frame:
                prev_ending = _build_frame_state_summary(prev_frame, is_prev=True)
        if i < len(plan) - 1:
            next_plan = plan[i + 1]
            next_starting = _build_plan_state_summary(next_plan, is_next=True)

        frame = generate_frame_detail(
            llm=llm,
            frame_plan=frame_plan,
            plan_summary=plan_summary,
            frame_count=len(plan),
            product_name=product_name,
            product_desc=product_desc,
            selling_points=selling_points,
            template=template,
            product_info=product_info,
            prev_frame_ending=prev_ending,
            next_frame_starting=next_starting,
            preset_id=preset_seq[i] if i < len(preset_seq) else "",
            preset_dimensions=get_preset_dimensions_str(preset_seq[i]) if i < len(preset_seq) else "",
            on_chunk=on_frame_chunk,
        )
        frames.append(frame)

        if on_frame_done:
            on_frame_done(frame_num, frame)

    return Storyboard(
        product_name=product_name,
        product_desc=product_desc,
        style_name=template.name,
        frames=frames,
    )


# ========== 单帧重新生成 ==========

def regenerate_frame(
    llm: LLMClient,
    storyboard: Storyboard,
    frame_index: int,
    template: StyleTemplate,
    product_info: Optional[ProductInfo] = None,
    product_name: str = "",
    product_desc: str = "",
    selling_points: str = "",
    on_chunk=None,
) -> StoryboardFrame:
    """重新生成某一帧的提示词
    
    使用已有的帧上下文（前后帧描述、整体方案）来重新生成单帧，
    不需要重新走基调步骤。temperature 提高到 0.9 以获得不同创意。
    """
    frames = storyboard.frames
    if not (0 <= frame_index < len(frames)):
        raise ValueError(f"帧索引 {frame_index} 超出范围")
    
    old_frame = frames[frame_index]
    frame_num = old_frame.frame
    duration = old_frame.duration
    description = old_frame.description
    
    # 从现有帧构建 plan_summary（上下文）
    plan_summary_lines = []
    for f in frames:
        plan_summary_lines.append(
            f"第{f.frame}帧 ({f.duration}s): "
            f"{f.description} | 运镜: {f.camera_motion_cn or f.camera_motion}"
        )
    plan_summary = "\n".join(plan_summary_lines)
    
    # 上下文衔接（物理状态摘要）
    prev_ending = ""
    next_starting = ""
    if frame_index > 0:
        prev = frames[frame_index - 1]
        prev_ending = _build_frame_state_summary(prev, is_prev=True)
    if frame_index < len(frames) - 1:
        nxt = frames[frame_index + 1]
        next_starting = _build_frame_state_summary(nxt, is_next=True)
    
    # 构建帧方案（从现有帧提取）
    frame_plan = {
        "frame": frame_num,
        "duration": duration,
        "description": description,
        "focus": "",
        "camera_motion_type": old_frame.camera_motion or "static hold",
        "transition": old_frame.transition or "none",
    }
    
    texture_str = _build_texture_str(product_info)
    style_words = ", ".join(template.image_style_words)
    camera_words = ", ".join(template.camera_style_words)
    
    # 计算预设序列，获取当前帧的预设
    texture_cat = detect_texture_category(texture_str)
    preset_seq = get_preset_sequence(texture_cat, len(frames))
    current_preset_id = preset_seq[frame_index] if frame_index < len(preset_seq) else ""
    current_preset_dims = get_preset_dimensions_str(current_preset_id) if current_preset_id else ""
    
    # 系统提示词
    sys_prompt = get_system_prompt(product_texture=texture_str)
    
    frame_sys = get_frame_prompt(
        frame_num=frame_num,
        frame_count=len(frames),
        product_info=f"名称：{product_name or storyboard.product_name}\n描述：{product_desc or storyboard.product_desc}\n卖点：{selling_points or '美味零食'}\n质感：{texture_str or '未知'}",
        style_name=template.name,
        style_words=style_words,
        camera_words=camera_words,
        plan_summary=plan_summary,
        duration=duration,
        frame_description=description,
        frame_focus="",
        frame_camera_type=old_frame.camera_motion or "static hold",
        frame_transition=old_frame.transition or "none",
        texture_info=texture_str or '未知',
        prev_frame_ending=prev_ending or '（第一帧，无上一帧）',
        next_frame_starting=next_starting or '（最后一帧，无下一帧）',
        preset_id=current_preset_id,
        preset_dimensions=current_preset_dims,
    )
    
    full_sys = sys_prompt + "\n\n---\n\n" + frame_sys
    
    messages = [
        {"role": "system", "content": full_sys},
        {"role": "user", "content": f"请重新生成第 {frame_num} 帧的完整提示词。要求与之前不同的创意方向，但保持产品一致性。直接输出 JSON 对象。"},
    ]
    
    result = llm.chat_json(messages, temperature=0.9, on_chunk=on_chunk)
    
    if isinstance(result, list):
        result = result[0] if result else {}
    
    # 保存调试文件
    debug_dir = Path("outputs") / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    debug_file = debug_dir / f"regen_frame_{frame_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2))
    
    return StoryboardFrame(
        frame=result.get("frame", frame_num),
        duration=result.get("duration", duration),
        image_prompt=result.get("image_prompt", ""),
        image_prompt_cn=result.get("image_prompt_cn", ""),
        camera_motion=result.get("camera_motion", ""),
        camera_motion_cn=result.get("camera_motion_cn", ""),
        motion_hint=result.get("motion_hint", ""),
        motion_hint_cn=result.get("motion_hint_cn", ""),
        video_prompt=result.get("video_prompt", ""),
        video_prompt_cn=result.get("video_prompt_cn", ""),
        description=result.get("description", description),
        transition=result.get("transition", old_frame.transition or "none"),
        motion_phase=result.get("motion_phase", old_frame.motion_phase or "static"),
    )
