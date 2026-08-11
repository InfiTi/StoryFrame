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

def _pick_imd(f: dict, lang: str = "cn") -> str:
    """从帧数据中取 H3 多模态描述"""
    if lang == "en":
        return f.get("integrated_multimodal_description", "")
    return f.get("integrated_multimodal_description_cn", f.get("integrated_multimodal_description", ""))


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
            prompt = f.get("image_prompt", f.get("image_prompt_cn", ""))
        else:
            prompt = f.get("image_prompt_cn", f.get("image_prompt", ""))
        # H3 模式 fallback：用多模态描述
        if not prompt:
            prompt = _pick_imd(f, lang)
        if not prompt:
            prompt = "—"
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
            # fallback：H3 多模态描述优先，其次用 motion_hint + camera_motion 拼凑
            imd = _pick("integrated_multimodal_description_cn", "integrated_multimodal_description", "")
            if imd:
                block += imd
            else:
                motion = _pick("motion_hint_cn", "motion_hint", "")
                camera = _pick("camera_motion_cn", "camera_motion", "")
                block += f"{motion} 镜头{camera}" if motion or camera else "—"
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

    lines = [
        "\n---\n\n## 参考示例（Few-Shot）\n",
        "以下是一些高质量的产品描述提示词示例，仅供词汇选择和描述风格参考。\n",
        "⚠️ 注意：这些示例的输出格式各不相同（有的是 JSON、有的是纯文本），**不要模仿其格式**。\n",
        "你必须严格遵循上述 H3 规范的输出字段和 JSON 数组格式。\n",
    ]
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

    优先使用 h3_system_prompt.md，并注入 references/h3-base-en.txt 官方规范。
    """
    h3_prompt = _load_template("h3_system_prompt")
    if h3_prompt:
        # 注入官方 H3 提示词编写规范
        base_ref = (PROMPTS_DIR / "references" / "h3-base-en.txt")
        if base_ref.exists():
            base_content = base_ref.read_text(encoding="utf-8")
            # 截取关键章节，避免 token 过多
            # 保留：运镜三要素表、shot 格式、声音写法、案例
            import re
            # 提取 §4.3 到 §4.7 + §5 Cases
            sections = []
            # 运镜表和写法
            cam_match = re.search(r'### 4\.3.*?(?=### 4\.[4567])', base_content, re.DOTALL)
            if cam_match:
                sections.append("### 运镜规范（来自 H3 官方指南）\n" + cam_match.group())
            # shot 格式
            shot_match = re.search(r'### 4\.2.*?(?=### 4\.3)', base_content, re.DOTALL)
            if shot_match:
                sections.append("### 镜头切换规范（来自 H3 官方指南）\n" + shot_match.group())
            # 声音写法
            sound_match = re.search(r'### 4\.[67].*?(?=## 5\.)', base_content, re.DOTALL)
            if sound_match:
                sections.append("### 声音写法规范（来自 H3 官方指南）\n" + sound_match.group())
            # 案例
            case_match = re.search(r'## 5\..*', base_content, re.DOTALL)
            if case_match:
                sections.append("### 官方案例（来自 H3 官方指南）\n" + case_match.group())

            if sections:
                h3_prompt += "\n\n---\n## H3 官方提示词编写规范参考\n\n" + "\n\n".join(sections)

        # 追加 few-shot 示例
        few_shot = _load_few_shot(product_texture)
        if few_shot:
            h3_prompt += few_shot
        return h3_prompt

    # 最小回退
    return """你是一个专业的零食带货短视频分镜导演，专门为 MiniMax H3 视频生成模型编写提示词。

## 每帧输出字段
- frame: 帧序号
- shot_label: [Shot N]
- cut_timestamp: 第1帧为空，后续帧 At MM:SS.mmm,
- duration: 持续秒数
- motion_phase: 动作相位
- integrated_multimodal_description: 英文多模态描述（画面+动作+运镜+声音，80-150词）
- integrated_multimodal_description_cn: 中文翻译
- description: 中文简述

## 全片输出字段（JSON 数组最后一个对象）
- overall_soundscape: 全片环境音
- non_diegetic_music: 背景音乐

直接输出 JSON 数组，前 N 个对象是帧数据，最后 1 个是全局音频。
"""


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
    fmt: str = "plain",
) -> str:
    """从已生成的帧数据构建 H3 提示词文本

    lang: "cn" 用中文字段，"en" 用英文字段
    fmt: "plain" = H3 普通提示词（纯文本，带标注）
         "director" = H3 导演台脚本格式（[Shot N] At MM:SS.mmm, ... 连续文本）
    """
    if not frames:
        return ""

    # 导演台格式：连续文本，H3 原生 [Shot N] At 时间戳格式
    if fmt == "director":
        return _build_director_script(frames, lang)

    # 普通格式：带标注的纯文本
    def _pick(cn_key: str, en_key: str, default=""):
        if lang == "en":
            return f.get(en_key, f.get(cn_key, default))
        return f.get(cn_key, f.get(en_key, default))

    lines = []
    for i, f in enumerate(frames):
        shot_label = f.get("shot_label", f"[Shot {i+1}]")
        cut_ts = f.get("cut_timestamp", "")
        duration = f.get("duration", 0)

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
            lines.append(imd)
            lines.append("")

        # 描述
        desc = f.get("description", "")
        if desc:
            lines.append(f"备注: {desc}")

        lines.append("")
        lines.append("---")
        lines.append("")

    # 全片音频字段（可能在任意帧中，优先取最后一个非空的）
    soundscape = ""
    music = ""
    for f in frames:
        sc = f.get("overall_soundscape", "")
        if sc:
            soundscape = sc
        mu = f.get("non_diegetic_music", "")
        if mu:
            music = mu

    if soundscape or music:
        lines.append("[全片音频]")
        lines.append("")
        if soundscape:
            lines.append(f"overall_soundscape: {soundscape}")
        if music:
            lines.append(f"non_diegetic_music: {music}")
    else:
        lines.append("[全片音频]")
        lines.append("")
        lines.append("环境音: （需使用 H3 模式生成）")
        lines.append("背景音乐: （需使用 H3 模式生成）")

    return "\n".join(lines)


def _build_director_script(frames: list, lang: str = "en") -> str:
    """构建导演台文本界面脚本格式

    输出格式（导演台 parseOfficialScript 兼容）：
    [Shot 1] Cinematic, ...
    [Shot 2] At 00:03.500, ...
    ...

    overall_soundscape: ...
    non_diegetic_music: ...
    """
    lines = []
    for i, f in enumerate(frames):
        shot_label = f.get("shot_label", f"[Shot {i+1}]")
        cut_ts = f.get("cut_timestamp", "")

        if lang == "en":
            imd = f.get("integrated_multimodal_description", "")
        else:
            imd = f.get("integrated_multimodal_description_cn", f.get("integrated_multimodal_description", ""))

        # 导演台格式：[Shot N] + 时间戳(可选) + 空格 + 描述
        # 如果 imd 已经以 [Shot N] 开头，不再重复
        if imd and imd.strip().startswith("[Shot"):
            # imd 已包含 shot_label，直接用
            lines.append(imd.strip())
        else:
            header = shot_label
            if cut_ts:
                header += f" {cut_ts}"
            lines.append(f"{header} {imd}".strip())

    # 空行分隔
    lines.append("")

    # 全片音频字段（可能在任意帧中，优先取最后一个非空的）
    soundscape = ""
    music = ""
    for f in frames:
        sc = f.get("overall_soundscape", "")
        if sc:
            soundscape = sc
        mu = f.get("non_diegetic_music", "")
        if mu:
            music = mu

    if soundscape:
        lines.append(f"overall_soundscape: {soundscape}")
    if music:
        lines.append(f"non_diegetic_music: {music}")

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

## 生成策略

### 核心任务：写 integrated_multimodal_description
写一段 80-150 词的英文叙事，融合以下元素：
- 开头声明整体风格（Cinematic / 3D CG / Live-action 等）
- 画面主体：产品在做什么物理动作
- 产品质感：颜色、形状、材质、截面等物理特征
- 镜头运动：推/拉/摇/移/跟，幅度和速度，写成自然英语动作
- 声音线索：产品动作产生的物理音效（crunch/sizzle/drip 等）
- 环境氛围：光线/温度/空气感
- 构图比例：9:16 竖屏，关键元素在中间 80%

这是一体化叙事，不是字段拼凑。

### 补充字段
- integrated_multimodal_description_cn：上述描述的纯中文翻译
- motion_phase：动作相位（pre-action / mid-action / post-action / static）
- description：中文简述（15-25字）
- shot_label：[Shot {frame_num}]
- cut_timestamp：{ts_hint}

## 约束
- 禁止出现文字、logo、包装文字、标签、水印
- integrated_multimodal_description_cn 纯中文，禁止残留英文
- 画面比例 9:16 竖屏，关键元素在中间 80%
- 直接输出 JSON，不要输出其他内容

## 输出格式
输出单个 JSON 对象：
```json
{{
  "frame": {frame_num},
  "duration": {duration},
  "shot_label": "[Shot {frame_num}]",
  "cut_timestamp": "",
  "motion_phase": "mid-action",
  "integrated_multimodal_description": "...",
  "integrated_multimodal_description_cn": "...",
  "description": "..."
}}
```
"""
    return prompt
