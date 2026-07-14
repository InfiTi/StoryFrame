"""风格模板定义"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class StyleTemplate:
    """风格模板"""
    name: str           # 模板名称（中文）
    key: str            # 模板标识（英文）
    description: str    # 模板描述
    # 图片提示词风格关键词（英文，会拼接到图片提示词中）
    image_style_words: List[str] = field(default_factory=list)
    # 镜头描述风格关键词（英文，描述镜头运动）
    camera_style_words: List[str] = field(default_factory=list)
    # 画面节奏描述
    pacing: str = "normal"
    # 推荐分镜数
    recommended_frames: int = 5


# 预置风格模板
TEMPLATES: List[StyleTemplate] = [
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
    ),
]


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
