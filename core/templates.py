"""风格模板定义

模板来源：
1. 优先从 templates.json 加载（用户可自定义）
2. 回退到内置默认模板
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List
from pathlib import Path

TEMPLATES_FILE = Path(__file__).parent.parent / "templates.json"


@dataclass
class StyleTemplate:
    """风格模板"""
    name: str
    key: str
    description: str
    image_style_words: List[str] = field(default_factory=list)
    camera_style_words: List[str] = field(default_factory=list)
    pacing: str = "normal"
    recommended_frames: int = 5
    bgm: str = ""
    # 新增：冲击强度（低/中/高）
    impact_level: str = "中"
    # 新增：节奏策略
    pacing_strategy: str = "均匀分配"
    # 新增：负向排除词（按风格区分）
    negative_words: str = "no text, no words, no letters, no logo, no watermark, no label, no hands, no people"


# 内置默认模板
_DEFAULT_TEMPLATES = [
    StyleTemplate(
        name="高端",
        key="premium",
        description="奢华质感，金色点缀，影棚光效，高端大气",
        image_style_words=[
            "luxurious", "gold accent", "studio lighting",
            "premium feel", "elegant", "refined",
            "dark background", "soft reflections", "high-end product photography",
        ],
        camera_style_words=[
            "slow dolly in", "elegant reveal", "graceful pan",
            "smooth tracking shot",
        ],
        pacing="slow",
        recommended_frames=5,
        bgm="古典",
        impact_level="低",
        pacing_strategy="均匀分配",
    ),
    StyleTemplate(
        name="升格",
        key="hero",
        description="戏剧化高角度，英雄镜头，大气磅礴",
        image_style_words=[
            "dramatic", "high-angle", "hero shot",
            "dynamic composition", "epic scale", "bold lighting",
            "cinematic", "powerful stance",
        ],
        camera_style_words=[
            "sweeping crane up", "scale reveal", "dramatic zoom out",
            "hero angle sweep",
        ],
        pacing="dramatic",
        recommended_frames=5,
        bgm="冲击感",
        impact_level="高",
        pacing_strategy="慢开场快结尾",
    ),
    StyleTemplate(
        name="慢镜头",
        key="slowmo",
        description="特写细节，凝固瞬间，柔和散景",
        image_style_words=[
            "close-up detail", "motion frozen", "soft bokeh",
            "shallow depth of field", "dreamy", "smooth",
            "delicate texture", "gentle light",
        ],
        camera_style_words=[
            "slow-motion zoom into texture", "gentle push-in",
            "floating drift", "soft focus pull",
        ],
        pacing="very_slow",
        recommended_frames=4,
        bgm="轻柔",
        impact_level="低",
        pacing_strategy="均匀分配",
    ),
    StyleTemplate(
        name="超近距离",
        key="macro",
        description="微距镜头，极近特写，细节探索",
        image_style_words=[
            "macro shot", "extreme close-up", "detail focus",
            "texture exploration", "micro detail",
            "shallow depth of field", "crisp focus",
        ],
        camera_style_words=[
            "micro push-in", "texture exploration",
            "slow rack focus", "detail pan",
        ],
        pacing="slow",
        recommended_frames=6,
        bgm="清新",
        impact_level="中",
        pacing_strategy="均匀分配",
    ),
    StyleTemplate(
        name="日系清新",
        key="fresh",
        description="自然柔光，淡彩色调，极简风格",
        image_style_words=[
            "soft natural light", "pastel tones", "minimalist",
            "clean composition", "fresh", "airy",
            "Japanese aesthetic", "subtle colors",
        ],
        camera_style_words=[
            "gentle pan", "breathing rhythm", "soft handheld",
            "natural sway",
        ],
        pacing="normal",
        recommended_frames=5,
        bgm="清新",
        impact_level="低",
        pacing_strategy="均匀分配",
    ),
    StyleTemplate(
        name="国潮",
        key="guochao",
        description="大胆配色，中式美学，潮流感",
        image_style_words=[
            "bold colors", "Chinese aesthetic", "bold typography",
            "traditional pattern", "modern Chinese style",
            "vibrant red and gold", "cultural elements",
        ],
        camera_style_words=[
            "dynamic cut", "rhythm pop", "snap zoom",
            "energetic pan",
        ],
        pacing="fast",
        recommended_frames=5,
        bgm="国潮",
        impact_level="高",
        pacing_strategy="前紧后松",
        negative_words="no text, no words, no letters, no logo, no watermark, no label",
    ),
    StyleTemplate(
        name="活力动感",
        key="energetic",
        description="快节奏，鲜亮色彩，年轻活力",
        image_style_words=[
            "vibrant", "colorful", "energetic",
            "pop art style", "bold contrast", "fun",
            "lifestyle", "youth culture",
        ],
        camera_style_words=[
            "quick pan", "fast cut", "whip pan",
            "dynamic tracking", "speed ramp",
        ],
        pacing="fast",
        recommended_frames=6,
        bgm="动感",
        impact_level="高",
        pacing_strategy="前紧后松",
    ),
    StyleTemplate(
        name="温暖治愈",
        key="cozy",
        description="暖色调，居家氛围，温馨舒适",
        image_style_words=[
            "warm tones", "cozy atmosphere", "home setting",
            "soft lighting", "comfortable", "inviting",
            "lifestyle photography", "golden hour",
        ],
        camera_style_words=[
            "slow pan", "warm push-in", "gentle orbit",
            "soft dolly",
        ],
        pacing="slow",
        recommended_frames=5,
        bgm="温暖",
        impact_level="低",
        pacing_strategy="慢开场快结尾",
        negative_words="no text, no words, no letters, no logo, no watermark, no label",
    ),
    StyleTemplate(
        name="灵动冲击",
        key="dynamic_impact",
        description="快速剪辑，环绕运镜，推近特写，高冲击力抓眼球",
        image_style_words=[
            "high-impact", "dynamic composition", "bold contrast",
            "vivid colors", "sharp focus", "explosive energy",
            "dramatic lighting", "punchy", "eye-catching",
        ],
        camera_style_words=[
            "fast orbit", "rapid push-in", "whip pan",
            "snap zoom", "quick cut", "dynamic circling",
            "hard stop", "speed ramp",
        ],
        pacing="fast",
        recommended_frames=6,
        bgm="冲击感",
        impact_level="高",
        pacing_strategy="前紧后松",
    ),
]


def _load_templates() -> List[StyleTemplate]:
    """加载模板：优先从 templates.json，回退到内置"""
    if TEMPLATES_FILE.exists():
        try:
            data = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
            templates = []
            for item in data:
                templates.append(StyleTemplate(
                    name=item["name"],
                    key=item["key"],
                    description=item["description"],
                    image_style_words=item.get("image_style_words", []),
                    camera_style_words=item.get("camera_style_words", []),
                    pacing=item.get("pacing", "normal"),
                    recommended_frames=item.get("recommended_frames", 5),
                    bgm=item.get("bgm", ""),
                    impact_level=item.get("impact_level", "中"),
                    pacing_strategy=item.get("pacing_strategy", "均匀分配"),
                    negative_words=item.get("negative_words", "no text, no words, no letters, no logo, no watermark, no label, no hands, no people"),
                ))
            if templates:
                return templates
        except Exception:
            pass
    return _DEFAULT_TEMPLATES


# 启动时加载
TEMPLATES: List[StyleTemplate] = _load_templates()


def get_template(key: str) -> StyleTemplate:
    """根据 key 获取模板"""
    for t in TEMPLATES:
        if t.key == key:
            return t
    return TEMPLATES[0]


def get_template_by_name(name: str) -> StyleTemplate:
    """根据中文名获取模板"""
    for t in TEMPLATES:
        if t.name == name:
            return t
    return TEMPLATES[0]
