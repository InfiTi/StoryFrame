"""提示词模板加载器

从 prompts/ 目录加载 Markdown 格式的提示词模板，支持变量替换。
"""

import re
from pathlib import Path
from typing import Optional

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# 默认负向词
DEFAULT_NEGATIVE_WORDS = "no text, no words, no letters, no logo, no watermark, no label, no hands, no people"

# 默认安全区描述
DEFAULT_SAFE_ZONE = "主体居中80%，上下各10%留白"

# 默认画面比例
DEFAULT_ASPECT_RATIO = "9:16 竖屏"


def compute_duration_plan(frame_count: int, total_duration: int, strategy: str) -> str:
    """根据节奏策略计算每帧时长分配方案

    返回格式化的多行文本，如：
    - 第1帧: 1.2s
    - 第2帧: 2.0s
    ...
    """
    if frame_count <= 0 or total_duration <= 0:
        return ""

    durations = [total_duration / frame_count] * frame_count

    if strategy == "前紧后松":
        # 前面帧短（快切），后面帧长（稳定展示）
        # 前半部分占 35% 时长，后半部分占 65%
        half = frame_count // 2
        if half > 0 and frame_count - half > 0:
            front_total = total_duration * 0.35
            back_total = total_duration * 0.65
            front_each = front_total / half
            back_each = back_total / (frame_count - half)
            for i in range(half):
                durations[i] = front_each
            for i in range(half, frame_count):
                durations[i] = back_each

    elif strategy == "慢开场快结尾":
        # 第一帧长（建立氛围），中间短，最后一帧长（定格）
        # 首尾各占 30%，中间占 40%
        if frame_count <= 2:
            durations = [total_duration / frame_count] * frame_count
        else:
            first_portion = total_duration * 0.30
            last_portion = total_duration * 0.30
            mid_portion = total_duration * 0.40
            mid_count = frame_count - 2
            durations[0] = first_portion
            durations[-1] = last_portion
            mid_each = mid_portion / mid_count
            for i in range(1, frame_count - 1):
                durations[i] = mid_each

    # 均匀分配不需要调整

    # 格式化输出
    lines = []
    for i in range(frame_count):
        lines.append(f"  - 第{i+1}帧: {durations[i]:.1f}s")
    return "\n".join(lines)


def _load_template(name: str) -> str:
    """加载 prompts/ 目录下的 Markdown 模板文件"""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _replace_vars(template: str, variables: dict) -> str:
    """替换模板中的 {变量名} 占位符"""
    if not template:
        return ""
    result = template
    for key, val in variables.items():
        result = result.replace(f"{{{key}}}", str(val))
    return result


# ========== 分镜生成提示词 ==========

def get_system_prompt() -> str:
    """获取 LLM 系统提示词"""
    return _load_template("system_prompt")


def get_user_prompt(
    product_name: str,
    product_desc: str,
    selling_points: str,
    template_name: str,
    template_desc: str,
    style_words: str,
    camera_words: str,
    pacing: str,
    frame_count: int,
    total_duration: int,
    # 新增变量
    product_texture: str = "",
    impact_level: str = "中",
    pacing_strategy: str = "均匀分配",
    bgm_style: str = "",
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    safe_zone: str = DEFAULT_SAFE_ZONE,
    negative_words: str = DEFAULT_NEGATIVE_WORDS,
    mid_frame: int = 0,
    duration_plan: str = "",
    flavor_tags: str = "",
    # 原有变量（保留兼容）
    texture_cn: str = "",
    texture_desc: str = "",
    spec_info: str = "",
    review_tags: str = "",
    copy_hints: str = "",
    direction: str = "",
) -> str:
    """构建用户提示词"""
    template = _load_template("user_prompt")
    if not template:
        return ""

    if mid_frame <= 0:
        mid_frame = max(2, frame_count - 1)

    variables = {
        "product_name": product_name,
        "product_desc": product_desc,
        "product_texture": product_texture or "未知",
        "selling_points": selling_points,
        "flavor_tags": flavor_tags or "未标注",
        "template_name": template_name,
        "template_desc": template_desc,
        "style_words": style_words,
        "camera_words": camera_words,
        "pacing": pacing,
        "frame_count": frame_count,
        "total_duration": total_duration,
        "per_frame_duration": f"{total_duration / frame_count:.1f}" if frame_count else "0",
        "impact_level": impact_level,
        "pacing_strategy": pacing_strategy,
        "bgm_style": bgm_style,
        "aspect_ratio": aspect_ratio,
        "safe_zone": safe_zone,
        "negative_words": negative_words,
        "mid_frame": mid_frame,
        "duration_plan": duration_plan,
        # 兼容旧变量
        "texture_cn": texture_cn,
        "texture_desc": texture_desc,
        "spec_info": spec_info,
        "review_tags": review_tags,
        "copy_hints": copy_hints,
        "direction": direction,
    }
    return _replace_vars(template, variables)


# ========== 豆包提示词 ==========

def get_doubao_image_prompt(
    category: str,
    frames: list,
    frame_count: int,
    negative_words: str = DEFAULT_NEGATIVE_WORDS,
) -> str:
    """获取豆包图片提示词"""
    template = _load_template("doubao_image_prompt")
    if not template:
        return ""

    frame_lines = []
    for i, f in enumerate(frames):
        frame_num = f.get("frame", i + 1)
        duration = f.get("duration", 0)
        block = f"### 第 {frame_num} 帧（{duration:.1f}s）\n"
        block += f"画面描述：{f.get('description', '—')}\n"
        block += f"图片提示词：{f.get('image_prompt_cn', f.get('image_prompt', '—'))}\n"
        block += f"画面动态：{f.get('motion_hint_cn', f.get('motion_hint', '—'))}"
        frame_lines.append(block)

    variables = {
        "category": category,
        "frame_count": frame_count,
        "frames_section": "\n\n".join(frame_lines),
        "negative_words": negative_words,
    }
    return _replace_vars(template, variables)


def get_doubao_video_prompt(
    category: str,
    frames: list,
    frame_count: int,
    bgm_style: str,
    negative_words: str = DEFAULT_NEGATIVE_WORDS,
) -> str:
    """获取豆包视频提示词"""
    template = _load_template("doubao_video_prompt")
    if not template:
        return ""

    frame_lines = []
    for i, f in enumerate(frames):
        frame_num = f.get("frame", i + 1)
        duration = f.get("duration", 0)
        # 提取画面描述，去掉尾部的负向词和构图安全区描述
        img_desc = f.get("image_prompt_cn", f.get("image_prompt", ""))
        import re
        # 去掉安全区描述（如“主体居中80%安全区，上下10%纯留白”等）
        img_desc = re.sub(r"\s*[，,]?\s*主体居中.*?(安全区|留白).*?$", "", img_desc, flags=re.IGNORECASE).strip()
        img_desc = re.sub(r"\s*[，,]?\s*(上下|顶部底部).*?(留白|安全区|whitespace).*?$", "", img_desc, flags=re.IGNORECASE).strip()
        # 去掉常见的负向词尾部
        img_desc = re.sub(r"\s*[，,]?\s*(无文字|无水印|no text|no words|no letters|no logo|no watermark|no label|no hands|no people).*?$", "", img_desc, flags=re.IGNORECASE).strip()
        
        block = f"### 第 {frame_num} 帧（{duration:.1f}s）\n"
        if img_desc:
            block += f"画面描述：{img_desc}\n"
        block += f"镜头运动：{f.get('camera_motion_cn', f.get('camera_motion', '—'))}\n"
        block += f"画面动态：{f.get('motion_hint_cn', f.get('motion_hint', '—'))}\n"
        # 过渡方式
        transition = f.get("transition", "")
        if transition and transition.lower() != "none":
            transition_cn = {"hard cut": "硬切", "whip pan": "甩镜转场", "speed ramp": "变速过渡", "fade": "渐变"}.get(transition.lower(), transition)
            block += f"转场方式：{transition_cn}\n"
        block += f"时长：{duration:.1f} 秒"
        frame_lines.append(block)

    variables = {
        "category": category,
        "frame_count": frame_count,
        "bgm_style": bgm_style,
        "frames_section": "\n\n".join(frame_lines),
        "negative_words": negative_words,
    }
    return _replace_vars(template, variables)
