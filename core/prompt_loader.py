"""提示词模板加载器

从 prompts/ 目录加载 Markdown 格式的提示词模板，支持变量替换。
系统提示词采用模块化组装：
- core.md (始终加载) + texture_*.md (按质感选一) + camera_motion.md (始终加载)
- 旧的单文件 system_prompt.md 保留为回退
"""

import re
from pathlib import Path
from typing import Optional

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MODULES_DIR = PROMPTS_DIR / "modules"

# 质感关键词到模块文件的映射
TEXTURE_MODULE_MAP = {
    "crispy": "texture_crispy.md",
    "crunchy": "texture_crispy.md",
    "flaky": "texture_crispy.md",
    "soft": "texture_soft_chewy.md",
    "chewy": "texture_soft_chewy.md",
    "mochi": "texture_soft_chewy.md",
    "gooey": "texture_liquid_creamy.md",
    "creamy": "texture_liquid_creamy.md",
    "saucy": "texture_liquid_creamy.md",
    "frozen": "texture_frozen_icy.md",
    "icy": "texture_frozen_icy.md",
}

# 质感中文关键词到模块的映射
TEXTURE_CN_MAP = {
    "脆": "texture_crispy.md",
    "酥": "texture_crispy.md",
    "软": "texture_soft_chewy.md",
    "糯": "texture_soft_chewy.md",
    "Q弹": "texture_soft_chewy.md",
    "液": "texture_liquid_creamy.md",
    "浆": "texture_liquid_creamy.md",
    "夹心": "texture_liquid_creamy.md",
    "流心": "texture_liquid_creamy.md",
    "冰": "texture_frozen_icy.md",
    "冷": "texture_frozen_icy.md",
    "冻": "texture_frozen_icy.md",
}

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


def _load_template_from(directory: Path, filename: str) -> str:
    """从指定目录加载模板文件"""
    path = directory / filename
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

def _detect_texture_module(product_texture: str = "") -> Optional[str]:
    """从质感描述字符串中检测应该加载哪个质感模块"""
    if not product_texture:
        return None
    text = product_texture.lower()
    # 先匹配英文关键词
    for kw, module in TEXTURE_MODULE_MAP.items():
        if kw in text:
            return module
    # 再匹配中文关键词
    for kw, module in TEXTURE_CN_MAP.items():
        if kw in product_texture:
            return module
    return None


# ========== 商业镜头预设库 ========== 

# 预设定义（与 prompts/modules/shot_presets.md 同步）
SHOT_PRESETS = {
    "PRESET-O1": {
        "name": "微距碎裂冲击",
        "position": "开场",
        "dimensions": {
            "景别": "medium shot → extreme close-up",
            "运镜": "fast push-in + hard stop",
            "速度": "burst to freeze",
            "角度": "45° overhead",
            "光线": "single hard side-light from left + rim light",
            "背景": "solid dark color, subtle radial gradient",
            "主体动作": "产品碎裂/崩解/飞溅，碎片向外放射",
            "过渡到下一帧": "whip pan",
        },
    },
    "PRESET-O2": {
        "name": "慢推质感揭示",
        "position": "开场",
        "dimensions": {
            "景别": "medium close-up → close-up",
            "运镜": "slow push-in + hold",
            "速度": "ease-in-out",
            "角度": "eye-level slight three-quarter",
            "光线": "soft diffused key from upper right + warm side-backlight",
            "背景": "solid warm light color, subtle gradient",
            "主体动作": "产品缓慢形变（拉丝延展/酱汁缓流/轻压回弹）",
            "过渡到下一帧": "speed ramp",
        },
    },
    "PRESET-O3": {
        "name": "俯拍全貌定格",
        "position": "开场",
        "dimensions": {
            "景别": "wide overhead → medium overhead",
            "运镜": "pull back + hold",
            "速度": "decelerate",
            "角度": "90° overhead",
            "光线": "top soft diffused + side fill",
            "背景": "textured surface (marble/slate/wood)",
            "主体动作": "产品静止，周围有冷凝水珠/雾气/气泡等氛围元素",
            "过渡到下一帧": "fade",
        },
    },
    "PRESET-M1": {
        "name": "甩镜滑入揭示",
        "position": "中间",
        "dimensions": {
            "景别": "off-center close-up → centered medium shot",
            "运镜": "whip pan + freeze",
            "速度": "burst to freeze",
            "角度": "eye-level three-quarter",
            "光线": "soft diffused + crisp rim light on leading edge",
            "背景": "solid color or gradient",
            "主体动作": "产品从画面一侧滑入定格，或配料飞入画面",
            "过渡到下一帧": "whip pan",
        },
    },
    "PRESET-M2": {
        "name": "微距焦点转移",
        "position": "中间",
        "dimensions": {
            "景别": "macro close-up → macro close-up（焦点变换）",
            "运镜": "rack focus",
            "速度": "decelerate",
            "角度": "macro three-quarter",
            "光线": "focused hard light on subject + soft ambient fill",
            "背景": "solid color with heavy bokeh",
            "主体动作": "焦点从产品的一个细节转移到产品的另一个细节（两个焦点都必须是产品本身，禁止引入包装/道具/背景元素）",
            "过渡到下一帧": "hard cut",
        },
    },
    "PRESET-M3": {
        "name": "弧线环绕展示",
        "position": "中间",
        "dimensions": {
            "景别": "medium shot → medium shot（角度变化）",
            "运镜": "arc shot 90° + hold",
            "速度": "constant to decelerate",
            "角度": "eye-level, 0° → 90°",
            "光线": "three-point lighting + rim light",
            "背景": "solid color with gentle gradient",
            "主体动作": "产品静止或微小动态（蒸汽/光泽变化）",
            "过渡到下一帧": "speed ramp",
        },
    },
    "PRESET-M4": {
        "name": "急速拉远揭示",
        "position": "中间",
        "dimensions": {
            "景别": "extreme close-up → wide shot",
            "运镜": "snap zoom out + hold",
            "速度": "burst to decelerate",
            "角度": "slight overhead",
            "光线": "volumetric light from upper left",
            "背景": "dark gradient with radial glow",
            "主体动作": "粉末/碎片/配料扩散后定格全貌",
            "过渡到下一帧": "hard cut",
        },
    },
    "PRESET-M5": {
        "name": "俯拍旋转",
        "position": "中间",
        "dimensions": {
            "景别": "overhead full shot → overhead full shot（旋转）",
            "运镜": "overhead rotation 180° + hold",
            "速度": "constant to decelerate",
            "角度": "90° overhead",
            "光线": "top soft diffused + side fill",
            "背景": "textured surface (wood/marble/slate)",
            "主体动作": "产品静止，背景纹理随旋转移动",
            "过渡到下一帧": "fade",
        },
    },
    "PRESET-M6": {
        "name": "慢推形变特写",
        "position": "中间",
        "dimensions": {
            "景别": "close-up → extreme close-up",
            "运镜": "slow push-in + hold",
            "速度": "ease-in-out",
            "角度": "eye-level slight three-quarter",
            "光线": "soft diffused key + warm rim light",
            "背景": "solid warm color, subtle gradient",
            "主体动作": "产品形变进行中（拉丝/流心/滴落/压缩回弹）",
            "过渡到下一帧": "speed ramp",
        },
    },
    "PRESET-E1": {
        "name": "拉远全景定格",
        "position": "结尾",
        "dimensions": {
            "景别": "close-up → wide shot",
            "运镜": "slow pull back + hold",
            "速度": "ease-in-out",
            "角度": "eye-level slight overhead",
            "光线": "warm soft key light + gentle rim light",
            "背景": "solid color with warm gradient",
            "主体动作": "产品静止，最佳状态展示",
            "过渡到下一帧": "none",
        },
    },
    "PRESET-E2": {
        "name": "俯拍排列全景",
        "position": "结尾",
        "dimensions": {
            "景别": "overhead wide shot → hold",
            "运镜": "static hold",
            "速度": "constant",
            "角度": "90° overhead",
            "光线": "top soft diffused + side fill",
            "背景": "textured surface",
            "主体动作": "产品静止，整齐排列展示",
            "过渡到下一帧": "none",
        },
    },
    "PRESET-E3": {
        "name": "慢推极致特写",
        "position": "结尾",
        "dimensions": {
            "景别": "close-up → extreme close-up",
            "运镜": "slow push-in + hold",
            "速度": "decelerate",
            "角度": "eye-level three-quarter",
            "光线": "soft diffused key + dramatic rim light",
            "背景": "dark solid color with subtle gradient",
            "主体动作": "产品静止，表面质感极致展示",
            "过渡到下一帧": "none",
        },
    },
}

# 质感→预设选择矩阵
TEXTURE_PRESET_MATRIX = {
    "酥脆": {
        "open": "PRESET-O1",
        "mid": ["PRESET-M1", "PRESET-M2", "PRESET-M4"],
        "end": "PRESET-E1",
    },
    "软糯": {
        "open": "PRESET-O2",
        "mid": ["PRESET-M6", "PRESET-M2", "PRESET-M3"],
        "end": "PRESET-E3",
    },
    "液态": {
        "open": "PRESET-O2",
        "mid": ["PRESET-M6", "PRESET-M2", "PRESET-M4"],
        "end": "PRESET-E1",
    },
    "冰爽": {
        "open": "PRESET-O3",
        "mid": ["PRESET-M3", "PRESET-M5", "PRESET-M2"],
        "end": "PRESET-E2",
    },
}


def detect_texture_category(product_texture: str = "") -> str:
    """从质感描述中检测质感分类（酥脆/软糯/液态/冰爽）"""
    if not product_texture:
        return "酥脆"  # 默认
    text = product_texture.lower()
    # 英文关键词
    for kw in ["crispy", "crunchy", "flaky"]:
        if kw in text:
            return "酥脆"
    for kw in ["soft", "chewy", "mochi"]:
        if kw in text:
            return "软糯"
    for kw in ["gooey", "creamy", "saucy", "liquid"]:
        if kw in text:
            return "液态"
    for kw in ["frozen", "icy"]:
        if kw in text:
            return "冰爽"
    # 中文关键词
    for kw in ["脆", "酥"]:
        if kw in product_texture:
            return "酥脆"
    for kw in ["软", "糯", "Q弹"]:
        if kw in product_texture:
            return "软糯"
    for kw in ["液", "浆", "夹心", "流心"]:
        if kw in product_texture:
            return "液态"
    for kw in ["冰", "冷", "冻"]:
        if kw in product_texture:
            return "冰爽"
    return "酥脆"  # 默认


def get_preset_sequence(texture_category: str, frame_count: int) -> list:
    """根据质感和帧数，生成完整的预设序列
    
    返回: ["PRESET-O1", "PRESET-M1", "PRESET-M2", ..., "PRESET-E1"]
    """
    matrix = TEXTURE_PRESET_MATRIX.get(texture_category, TEXTURE_PRESET_MATRIX["酥脆"])
    
    if frame_count <= 0:
        return []
    if frame_count == 1:
        return [matrix["end"]]
    
    sequence = [matrix["open"]]
    mid_presets = matrix["mid"]
    
    # 中间帧轮换
    mid_count = frame_count - 2
    for i in range(mid_count):
        sequence.append(mid_presets[i % len(mid_presets)])
    
    sequence.append(matrix["end"])
    return sequence


def get_preset_dimensions_str(preset_id: str) -> str:
    """获取预设的维度定义文本（用于注入 frame_prompt）"""
    preset = SHOT_PRESETS.get(preset_id)
    if not preset:
        return ""
    lines = []
    for k, v in preset["dimensions"].items():
        lines.append(f"  - {k}: {v}")
    return "\n".join(lines)


def get_preset_transition(preset_id: str) -> str:
    """获取预设的过渡方式"""
    preset = SHOT_PRESETS.get(preset_id)
    if not preset:
        return "hard cut"
    return preset["dimensions"].get("过渡到下一帧", "hard cut")


def _build_camera_templates_prompt() -> str:
    """构建镜头模板注入文本（保留兼容，但不再主要使用）"""
    return ""


def get_system_prompt(product_texture: str = "", include_camera_templates: bool = True) -> str:
    """获取 LLM 系统提示词（模块化组装）
    
    组装顺序：core.md + texture_*.md (按质感选一) + camera_motion.md + camera_templates (可选)
    如果 modules/ 目录不存在，回退到旧的单文件 system_prompt.md
    
    Args:
        product_texture: 质感描述，用于选择质感模块
        include_camera_templates: 是否注入镜头模板选择规则
    """
    # 尝试模块化组装
    if MODULES_DIR.exists():
        parts = []
        
        # 1. 核心层（始终加载）
        core = _load_template_from(MODULES_DIR, "core.md")
        if not core:
            # modules 目录存在但 core.md 缺失，回退
            return _load_template("system_prompt")
        parts.append(core.strip())
        
        # 2. 质感层（按商品质感选一）
        texture_module = _detect_texture_module(product_texture)
        if texture_module:
            texture_content = _load_template_from(MODULES_DIR, texture_module)
            if texture_content:
                parts.append(texture_content.strip())
        
        # 3. 运镜层（始终加载）
        camera_content = _load_template_from(MODULES_DIR, "camera_motion.md")
        if camera_content:
            parts.append(camera_content.strip())
        
        # 4. 镜头预设库（始终加载，强制约束）
        presets_text = _load_template_from(MODULES_DIR, "shot_presets.md")
        if presets_text:
            parts.append(presets_text.strip())
        
        # 5. 旧镜头模板层（可选，保留兼容）
        if include_camera_templates:
            templates_text = _build_camera_templates_prompt()
            if templates_text:
                parts.append(templates_text)
        
        return "\n\n".join(parts)
    
    # 回退：旧的单文件
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
    lang: str = "cn",
) -> str:
    """获取豆包图片提示词

    lang: "cn" 用中文字段，"en" 用英文字段
    """
    template = _load_template("doubao_image_prompt")
    if not template:
        return ""

    frame_lines = []
    for i, f in enumerate(frames):
        frame_num = f.get("frame", i + 1)
        duration = f.get("duration", 0)
        block = f"### 第 {frame_num} 帧（{duration:.1f}s）\n"
        block += f"画面描述：{f.get('description', '—')}\n"
        if lang == "en":
            prompt = f.get("image_prompt", f.get("image_prompt_cn", "—"))
        else:
            prompt = f.get("image_prompt_cn", f.get("image_prompt", "—"))
        block += f"图片提示词：{prompt}"
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
    lang: str = "cn",
    style_name: str = "",
    style_words: str = "",
    camera_words: str = "",
) -> str:
    """获取豆包视频提示词

    lang: "cn" 用中文字段，"en" 用英文字段
    style_name/style_words/camera_words: 风格模板参数，注入到视频prompt头部
    """
    template = _load_template("doubao_video_prompt")
    if not template:
        return ""

    def _pick(cn_key: str, en_key: str, default="—"):
        """按 lang 选字段"""
        if lang == "en":
            return f.get(en_key, f.get(cn_key, default))
        else:
            return f.get(cn_key, f.get(en_key, default))

    frame_lines = []
    for i, f in enumerate(frames):
        frame_num = f.get("frame", i + 1)
        duration = f.get("duration", 0)
        motion_phase = f.get("motion_phase", "static")
        video_prompt_text = _pick("video_prompt_cn", "video_prompt", "")
        transition = f.get("transition", "")

        # 相位中文映射
        phase_cn = {
            "pre-action": "产品静止，从静止开始执行完整动作",
            "mid-action": "产品处于运动中间状态，从当前状态继续完成动作",
            "post-action": "产品处于动作结束状态，缓慢回归静止或轻微回弹",
            "static": "产品静止，仅镜头运动",
        }.get(motion_phase, "产品静止，仅镜头运动")

        block = f"### 第{frame_num}帧（{duration:.1f}s）\n"
        block += f"参考图状态：{phase_cn}\n"
        if video_prompt_text:
            block += video_prompt_text
        else:
            # fallback：用 motion_hint + camera_motion 拼凑
            motion = _pick("motion_hint_cn", "motion_hint", "")
            camera = _pick("camera_motion_cn", "camera_motion", "")
            block += f"{motion} 镜头{camera}"
        if transition and transition.lower() != "none":
            transition_cn = {"hard cut": "硬切", "whip pan": "甩镜转场", "speed ramp": "变速过渡", "fade": "渐变"}.get(transition.lower(), transition)
            block += f"\n转场：{transition_cn}"
        frame_lines.append(block)

    # 风格描述行
    style_line = f"风格：{style_name}" if style_name else ""
    if style_words:
        style_line += f"，{style_words}" if style_line else style_words
    if camera_words:
        style_line += f"，镜头特征：{camera_words}" if style_line else f"镜头特征：{camera_words}"

    variables = {
        "category": category,
        "frame_count": frame_count,
        "bgm_style": bgm_style,
        "frames_section": "\n\n".join(frame_lines),
        "negative_words": negative_words,
        "style_line": style_line,
    }
    return _replace_vars(template, variables)

# ========== H3 提示词加载 ==========


def _load_few_shot(product_texture: str = "", max_items: int = 3) -> str:
    """从 few_shot_extracted.json 按质感读取 few-shot 示例，注入到 system prompt

    返回格式化的文本段落，如果没有匹配则返回空字符串。
    """
    few_shot_path = PROMPTS_DIR / "few_shot_extracted.json"
    if not few_shot_path.exists():
        return ""

    import json
    try:
        data = json.loads(few_shot_path.read_text(encoding="utf-8"))
    except Exception:
        return ""

    # 质感关键词到 few_shot key 的映射
    texture_lower = (product_texture or "").lower()
    key_map = {
        "crispy": ["crispy"],
        "soft_chewy": ["soft", "chewy", "mochi"],
        "liquid_creamy": ["liquid", "cream", "sauce"],
        "frozen_icy": ["frozen", "ice"],
    }

    matched_key = ""
    for fs_key, keywords in key_map.items():
        if any(kw in texture_lower for kw in keywords):
            matched_key = fs_key
            break

    if not matched_key or matched_key not in data:
        matched_key = "crispy" if "crispy" in data else (list(data.keys())[0] if data else "")

    if not matched_key:
        return ""

    items = data[matched_key][:max_items]
    if not items:
        return ""

    lines = ["\n---\n\n## 参考示例（Few-Shot）\n", "以下是一些高质量的产品描述提示词示例，请参考其描述风格、词汇选择和结构组织：\n"]
    for i, item in enumerate(items, 1):
        title = item.get("title", "示例 " + str(i))
        ct = item.get("content", "")
        if len(ct) > 800:
            ct = ct[:800] + "..."
        lines.append("### 示例 " + str(i) + "：" + title)
        lines.append("```")
        lines.append(ct)
        lines.append("```\n")

    return "\n".join(lines)


def get_h3_system_prompt(product_texture: str = "") -> str:
    """获取 H3 模式的系统提示词

    H3 模式沿用现有模块化机制（core.md + texture_*.md + camera_motion.md），
    但输出改为 H3 规范结构（[Shot N] + 切点时间戳 + 运镜三要素 + 多模态描述 + 全片音频）。
    如果 h3_system_prompt.md 存在则直接使用（已内置全部规范），
    否则回退到模块化组装 + H3 输出规范附录。
    """
    # 优先使用独立的 H3 系统提示词文件
    h3_prompt = _load_template("h3_system_prompt")
    if h3_prompt:
        # 追加 few-shot 示例
        few_shot = _load_few_shot(product_texture)
        if few_shot:
            h3_prompt += few_shot
        return h3_prompt

    # 回退：模块化组装 + 追加 H3 输出规范
    base = get_system_prompt(product_texture=product_texture)
    h3_suffix = """

---

## H3 输出规范（覆盖上述输出格式）

每个分镜必须包含以下 H3 规范字段：

### shot_label
格式：`[Shot N]`，N 从 1 开始递增

### cut_timestamp
- 第 1 帧：无时间戳（`[Shot 1]` 直接开始）
- 第 2+ 帧：`At MM:SS.mmm,` 格式，如 `At 00:03.500,`
- 时间戳必须严格递增且在总时长范围内

### camera_motion（运镜三要素）
运镜必须包含三个维度：运动类型 + 幅度 + 速度
- 运动类型：Zoom In / Zoom Out / Push In / Pull Out / Pan Left / Pan Right / Truck Left / Truck Right / Tilt Up / Tilt Down / Pedestal Up / Pedestal Down / Arc Shot / Tracking Shot / Static Shot / Shake Slightly / Shake Strongly / POV / Roll Clockwise / Roll Counterclockwise
- 幅度：with small amplitude / with large amplitude（中等可省略）
- 速度：at slow speed / at fast speed（正常可省略）
运镜写成自然英语动作，不要堆砌标签

### integrated_multimodal_description（多模态综合描述）
每个 Shot 的核心描述，包含：
- 整体风格（Cinematic / live-action / 3D CG 等）
- 初始构图和主体位置
- 产品外观和质感
- 动作描述（产品物理动作 + 微动态）
- 镜头运动
- 环境和光影
- 画面内声音（产品动作产生的物理音效）

### overall_soundscape（全片环境音）
1-4 句英语，总结全片的环境音和物理音效

### non_diegetic_music（背景音乐）
1-3 句英语描述 BGM，无 BGM 时填 N/A

## H3 输出字段
- frame: 帧序号（从1开始）
- shot_label: H3 分镜标签
- cut_timestamp: 切点时间戳
- duration: 该帧持续秒数
- motion_phase: 动作相位
- image_prompt: 英文生图提示词（60-100词）
- image_prompt_cn: 中文翻译
- camera_motion: 英文运镜描述（H3 三要素格式）
- camera_motion_cn: 中文运镜描述
- motion_hint: 英文产品动态（25-50词）
- motion_hint_cn: 中文产品动态
- integrated_multimodal_description: 英文多模态描述（80-150词）
- integrated_multimodal_description_cn: 中文多模态描述
- transition: 过渡方式
- video_prompt: 英文视频描述（40-70词）
- video_prompt_cn: 中文视频描述
- description: 中文简述（15-25字）

## 全片输出字段（附加在 JSON 数组末尾）
最后一个对象包含全局音频字段：
- overall_soundscape: 英文全片环境音
- non_diegetic_music: 英文背景音乐

## 输出格式
直接输出 JSON 数组，前 N 个对象是帧数据，最后 1 个对象是全局音频数据。
"""
    return base + h3_suffix


def get_h3_user_prompt(
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
    product_texture: str = "",
    impact_level: str = "中",
    pacing_strategy: str = "均匀分配",
    bgm_style: str = "",
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    safe_zone: str = DEFAULT_SAFE_ZONE,
    negative_words: str = DEFAULT_NEGATIVE_WORDS,
    duration_plan: str = "",
    flavor_tags: str = "",
) -> str:
    """构建 H3 模式的用户提示词"""
    template = _load_template("h3_user_prompt")
    if not template:
        return ""

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
        "impact_level": impact_level,
        "pacing_strategy": pacing_strategy,
        "bgm_style": bgm_style,
        "aspect_ratio": aspect_ratio,
        "safe_zone": safe_zone,
        "negative_words": negative_words,
        "duration_plan": duration_plan,
    }
    return _replace_vars(template, variables)


def get_h3_copy_prompt(
    frames: list,
    frame_count: int,
    lang: str = "cn",
) -> str:
    """从已生成的帧数据构建 H3 复制提示词文本

    lang: "cn" 用中文字段，"en" 用英文字段
    输出为纯文本格式，每帧一段，末尾附全片音频字段。
    """
    if not frames:
        return ""

    def _pick(cn_key: str, en_key: str, default=""):
        if lang == "en":
            return f.get(en_key, f.get(cn_key, default))
        return f.get(cn_key, f.get(en_key, default))

    lines = []
    for i, f in enumerate(frames):
        shot_label = f.get("shot_label", f"[Shot {i+1}]")
        cut_ts = f.get("cut_timestamp", "")
        duration = f.get("duration", 0)
        motion_phase = f.get("motion_phase", "static")

        # 头部：[Shot N] + 时间戳
        header = shot_label
        if cut_ts:
            header += f" {cut_ts}"
        header += f" ({duration:.1f}s)"
        lines.append(header)
        lines.append("")

        # 多模态描述（核心）
        imd = _pick("integrated_multimodal_description_cn", "integrated_multimodal_description")
        if imd:
            lines.append(f"多模态描述: {imd}")
            lines.append("")

        # 运镜
        camera = _pick("camera_motion_cn", "camera_motion")
        if camera:
            lines.append(f"运镜: {camera}")

        # 图片提示词
        img = _pick("image_prompt_cn", "image_prompt")
        if img:
            lines.append(f"画面: {img}")

        # 产品动态
        motion = _pick("motion_hint_cn", "motion_hint")
        if motion:
            lines.append(f"动态: {motion}")

        # 视频提示词
        video = _pick("video_prompt_cn", "video_prompt")
        if video:
            lines.append(f"视频: {video}")

        # 过渡
        transition = f.get("transition", "")
        if transition and transition.lower() != "none":
            trans_cn = {"hard cut": "硬切", "whip pan": "甩镜转场", "speed ramp": "变速过渡", "fade": "渐变"}.get(transition.lower(), transition)
            lines.append(f"转场: {trans_cn}")

        # 描述
        desc = f.get("description", "")
        if desc:
            lines.append(f"备注: {desc}")

        lines.append("")
        lines.append("---")
        lines.append("")

    # 全片音频字段
    last = frames[-1] if frames else {}
    soundscape = last.get("overall_soundscape", "")
    music = last.get("non_diegetic_music", "")

    if soundscape or music:
        lines.append("[全片音频]")
        lines.append("")
        if soundscape:
            lines.append(f"环境音: {soundscape}")
        if music:
            lines.append(f"背景音乐: {music}")
    else:
        # 如果帧数据中没有音频字段（非 H3 生成），提示
        lines.append("[全片音频]")
        lines.append("")
        lines.append("环境音: （需使用 H3 模式生成）")
        lines.append("背景音乐: （需使用 H3 模式生成）")

    return "\n".join(lines)


# ========== 两步生成提示词加载 ==========


def get_plan_prompt(frame_count: int, total_duration: int) -> str:
    """加载基调生成系统提示词"""
    template = _load_template_from(MODULES_DIR, "plan_prompt.md")
    if not template:
        return f"""请设计 {frame_count} 帧分镜方案，总时长 {total_duration} 秒。
直接输出 JSON 数组，每帧含 frame, duration, description, focus, camera_motion_type, transition。"""
    return _replace_vars(template, {
        "frame_count": frame_count,
        "total_duration": total_duration,
    })


def get_frame_prompt(
    frame_num: int,
    frame_count: int,
    product_info: str,
    style_name: str,
    style_words: str,
    camera_words: str,
    plan_summary: str,
    duration: float,
    frame_description: str,
    frame_focus: str,
    frame_camera_type: str,
    frame_transition: str,
    texture_info: str,
    prev_frame_ending: str,
    next_frame_starting: str,
    preset_id: str = "",
    preset_dimensions: str = "",
) -> str:
    """加载单帧生成系统提示词"""
    template = _load_template_from(MODULES_DIR, "frame_prompt.md")
    if not template:
        return f"""请为第 {frame_num} 帧生成完整提示词。时长 {duration} 秒。
输出 JSON 对象，含 image_prompt, image_prompt_cn, camera_motion, camera_motion_cn,
motion_hint, motion_hint_cn, video_prompt, video_prompt_cn, description。"""
    return _replace_vars(template, {
        "frame_num": frame_num,
        "frame_count": frame_count,
        "product_info": product_info,
        "style_name": style_name,
        "style_words": style_words,
        "camera_words": camera_words,
        "plan_summary": plan_summary,
        "duration": duration,
        "frame_description": frame_description,
        "frame_focus": frame_focus,
        "frame_camera_type": frame_camera_type,
        "frame_transition": frame_transition,
        "texture_info": texture_info,
        "prev_frame_ending": prev_frame_ending,
        "next_frame_starting": next_frame_starting,
        "preset_id": preset_id or "未指定",
        "preset_dimensions": preset_dimensions or "未指定",
    })


def get_h3_plan_prompt(product_name: str, product_desc: str, selling_points: str,
                       template, frame_count: int, total_duration: float,
                       product_info: str = "", direction: str = "") -> str:
    """H3 模式 plan 阶段提示词

    H3 plan 不选镜头预设，而是规划叙事弧：
    1. 输入模式判断（T2VA/I2VA/Ref2VA 等）
    2. 每帧的叙事节拍（起承转合）
    3. 过渡方式
    4. 时长分配
    """
    prompt = f"""你是一个专业的产品短视频分镜导演，精通 H3 提示词写作规范。

## 任务
为产品「{product_name}」规划一个 {frame_count} 帧的短视频分镜方案。

## 产品信息
- 名称：{product_name}
- 描述：{product_desc}
- 卖点：{selling_points or "美味零食"}
"""
    if product_info:
        prompt += f"- 详细信息：{product_info}\n"
    if direction:
        prompt += f"- 视频方向：{direction}\n"

    prompt += f"""
## 规划要求

### 1. 输入模式判断
根据产品特征和可用素材，确定输入模式：
- T2VA（纯文本生成视频）
- I2VA（图片+文本生成视频）
- Ref2VA（参考图生成视频）

### 2. 叙事弧规划
为每帧分配叙事节拍：
- 第1帧：开场（建立产品视觉印象）
- 中间帧：发展（展示质感、动作、卖点）
- 末帧：收束（最终呈现 + 品牌定格感）

### 3. 时长分配
总时长 {total_duration} 秒，分配到 {frame_count} 帧。
短帧（0.5-1.0s）适合快切、碎裂、飞溅等瞬时动作。
长帧（1.5-2.5s）适合拉丝、流淌、渐显等持续动作。

### 4. 过渡方式
为每帧指定过渡到下一帧的方式：
- hard cut（硬切，适合快节奏）
- whip pan（甩镜，适合位置/角度切换）
- speed ramp（速度渐变，适合动静转换）
- fade（渐变，适合开场/结尾）

## 输出格式
输出 JSON 数组，每个元素代表一帧：
```json
[
  {{
    "frame": 1,
    "duration": 1.0,
    "shot_label": "[Shot 1]",
    "narrative_beat": "开场：产品全貌建立",
    "input_mode": "I2VA",
    "transition": "fade",
    "duration_rationale": "开场需要足够时间建立视觉印象"
  }}
]
```

直接输出 JSON 数组，不要输出其他内容。
"""
    return prompt


def get_h3_frame_prompt(frame_num: int, total_frames: int, duration: float,
                         product_name: str, product_desc: str, selling_points: str,
                         template, product_info: str = "",
                         prev_frame_summary: str = "", direction: str = "") -> str:
    """H3 模式逐帧生成提示词

    H3 frame 的核心策略：先写 integrated_multimodal_description，再从中派生其他字段。
    """
    style_name = template.name if template else ""

    # 构建可选信息行（避免 f-string 中包含反斜杠）
    info_line = "- 详细：" + product_info if product_info else ""
    direction_line = "- 视频方向：" + direction if direction else ""
    style_line = "- 风格：" + style_name if style_name else ""
    prev_section = ""
    if prev_frame_summary:
        prev_section = "## 前帧摘要\n" + prev_frame_summary
    ts_hint = "（第1帧留空）" if frame_num == 1 else "At 00:XX.XXX,（根据总时长推算）"

    prompt = f"""你是 H3 提示词专家。请为第 {frame_num} 帧生成完整的提示词。

## 本帧参数
- 帧号：{frame_num} / {total_frames}
- 时长：{duration:.1f} 秒
- 产品：{product_name}

## 产品信息
- 描述：{product_desc}
- 卖点：{selling_points or "美味零食"}
{info_line}
{direction_line}
{style_line}

{prev_section}

## 生成策略（叙事优先）

### 第一步：写 integrated_multimodal_description
写一段 80-150 词的英文叙事，融合以下元素：
- 画面主体：产品在做什么物理动作
- 镜头运动：推/拉/摇/移/跟，幅度和速度
- 声音线索：产品动作产生的声音（碎裂声/流淌声/咀嚼声等）
- 环境氛围：光线/温度/空气感
- 时间感：动作是瞬时还是持续

这是本帧的灵魂字段——不是字段拼凑，是一体化叙事。

### 第二步：从中派生以下字段
- image_prompt：从叙事中提取画面描述（60-100 词），末尾加 no text, no words, no logo, no watermark
- camera_motion：从叙事中提取镜头运动（类型+幅度+速度，自然英语）
- motion_hint：从叙事中提取画面内动态
- video_prompt：从叙事中提取视频生成指令（40-70 词自然语言）
- transition：过渡到下一帧的方式（hard cut / whip pan / speed ramp / fade）

### 第三步：写中文对照
- image_prompt_cn：image_prompt 的中文翻译（纯中文，无残留英文）
- camera_motion_cn、motion_hint_cn、video_prompt_cn：对应中文

### 第四步：H3 格式字段
- shot_label：[Shot {frame_num}]
- cut_timestamp：{ts_hint}

## 输出格式
输出单个 JSON 对象：
```json
{{
  "frame": {frame_num},
  "duration": {duration},
  "shot_label": "[Shot {frame_num}]",
  "cut_timestamp": "",
  "integrated_multimodal_description": "...",
  "image_prompt": "...",
  "image_prompt_cn": "...",
  "camera_motion": "...",
  "camera_motion_cn": "...",
  "motion_hint": "...",
  "motion_hint_cn": "...",
  "video_prompt": "...",
  "video_prompt_cn": "...",
  "transition": "..."
}}
```

## 约束
- image_prompt 末尾必须加：no text, no words, no letters, no logo, no watermark, no label
- image_prompt_cn 纯中文，禁止残留英文单词
- video_prompt 40-70 词，禁止精确数值（如 0.6s, 270 degrees）
- 画面比例 9:16 竖屏，关键元素在中间 80%
- 直接输出 JSON，不要输出其他内容
"""
    return prompt
