"""运动示意图生成模块（黑白线稿分镜蓝图）

为「图生视频」生成一张运动蓝图：黑白线稿 + 手绘箭头 + 粒子符号，
让视频模型理解画面应该怎么动（主体、方向、速度、粒子、镜头）。
只画主体轮廓示意，不给产品外观细节。

三种模式：
- programmatic: 本地 Pillow 程序化绘制（免费、秒出、完全可控）
- ai: 用 Agnes 图片 API 按提示词模板生成手绘风线稿（返回公网 URL）
- hybrid: 先程序化画底稿，再用 Agnes 图生图精修为干净线稿（拿公网 URL）

用法：
    from core.motion_sketch import generate_motion_sketch, from_frame
    ok, path, url, msg = generate_motion_sketch(mgr, frame_dict, sketch_config, output_path)
"""

import base64
import math
import os
import random
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


# ========== 数据结构 ==========

@dataclass
class MotionSketchData:
    """单帧运动示意图数据（从分镜帧字段启发式映射）"""
    frame_num: int = 0
    product_shape: str = "rect"          # round / rect / cylinder / irregular
    product_size: Tuple[int, int] = (240, 160)
    product_position: Tuple[int, int] = (512, 288)
    motion_type: str = "slide"           # crumble / splash / stretch / drop / rotate / slide
    motion_direction: Tuple[float, float] = (0, 0)
    motion_speed: str = "medium"         # slow / medium / fast
    particles: List[str] = field(default_factory=list)  # splash / crumbs / dust / steam
    camera_motion: str = "static"        # zoom_in / pan_left / orbit / static
    description: str = ""


# ========== 从分镜帧提取结构化运动信息 ==========

_SHAPE_KEYWORDS = [
    (("round", "sphere", "ball", "globe", "circle", "spherical", "orb", "dome"), "round"),
    (("cylinder", "bottle", "can", "tube", "jar", "barrel", "roll", "cylindrical"), "cylinder"),
    (("irregular", "organic", "lump", "blob", "amorphous", "uneven", "jagged"), "irregular"),
    # 常见零食形态：薄片/层叠/条状 → 归入 rect（矩形轮廓示意）
    (("thin", "flaky", "layered", "sheet", "slab", "bar", "stick", "rectangular", "flat"), "rect"),
]

_MOTION_KEYWORDS = [
    # crumble: 碎裂/破碎/断裂
    (("crumble", "fractur", "shatter", "break apart", "crush", "splinter",
      "fragment", "break into", "crack", "snap apart", "disintegrat", "flake off",
      "split", "cleave"), "crumble"),
    # splash: 飞溅/喷溅/爆发
    (("splash", "burst", "explod", "erupt", "spray", "squirt",
      "scatter", "fly out", "shoot out", "fan out", "radiate outward",
      "cascade", "sprinkle", "shower"), "splash"),
    # stretch: 拉伸/延展/拉丝/剥离
    (("stretch", "pull", "tear", "rip", "elongate", "extend", "peel", "unfold",
      "draw out", "stringy", "pull apart", "strip", "ribbon", "thread",
      "ooze", "melt", "drip down", "ooze out"), "stretch"),
    # drop: 下落/滴落/倾倒
    (("drop", "fall", "plunge", "drip", "pour",
      "cascade down", "tumble down", "settle", "descend", "sink", "slide down",
      "roll down"), "drop"),
    # rotate: 旋转/翻转/滚动
    (("rotat", "spin", "twist", "tumble", "flip", "revolv",
      "roll", "pivot", "swivel", "spiral", "gyrate", "turn over"), "rotate"),
    # slide: 滑动/平移/推移（默认 fallback 也用这个）
    (("slide", "glide", "drift", "shift", "pan", "move across",
      "travel", "sweep", "push across", "slide over"), "slide"),
]

_FAST_WORDS = ("fast", "quick", "rapid", "burst", "violent", "sudden", "explos", "snap", "shock",
               "shatter", "brisk", "sharp", "staccato", "freeze", "snap to")
_SLOW_WORDS = ("slow", "gentle", "gradual", "soft", "slowly", "leisurely", "delicate",
               "ease-in", "ease in", "decelerate", "smooth", "creeping", "subtle", "drift")


def from_frame(frame: dict) -> MotionSketchData:
    """从分镜帧数据（StoryboardFrame.to_dict / 缓存 JSON）提取结构化运动信息。

    采用关键词启发式解析 motion_hint / video_prompt / camera_motion / image_prompt，
    保证不依赖 LLM 额外输出字段也能工作。
    """
    frame_num = int(frame.get("frame", 0) or 0)
    motion_hint = str(frame.get("motion_hint", "") or "")
    video_prompt = str(frame.get("video_prompt", "") or "")
    image_prompt = str(frame.get("image_prompt", "") or "")
    camera = str(frame.get("camera_motion", "") or "")
    description = str(frame.get("description", "") or "")
    text = f"{motion_hint} {video_prompt}".lower()
    img_text = image_prompt.lower()
    cam_text = camera.lower()

    # 1. 产品形状（只画轮廓示意，不涉及外观）
    shape = "rect"
    for kws, s in _SHAPE_KEYWORDS:
        if any(k in img_text for k in kws):
            shape = s
            break

    # 2. 运动类型
    motion_type = "slide"
    for kws, mt in _MOTION_KEYWORDS:
        if any(k in text for k in kws):
            motion_type = mt
            break

    # 3. 速度
    speed = "medium"
    if any(k in text for k in _FAST_WORDS):
        speed = "fast"
    elif any(k in text for k in _SLOW_WORDS):
        speed = "slow"

    # 4. 方向（关键词优先，缺省按运动类型）
    default_dir = {
        "crumble": (0.7, -0.7),
        "splash": (0.0, -1.0),
        "stretch": (1.0, 0.0),
        "drop": (0.0, 1.0),
        "rotate": (0.0, 0.0),
        "slide": (1.0, 0.0),
    }.get(motion_type, (0.0, 0.0))
    dx, dy = default_dir
    # 方向关键词扩展：覆盖 LLM 实际用词
    if any(k in text for k in ("left", "backward", "pull back")):
        dx = -1
    elif any(k in text for k in ("right", "forward", "push forward", "push-in")):
        dx = 1
    if any(k in text for k in ("upward", "upward ", "rise", "ascend", "upward motion")
           ) or ("up" in text and "cup" not in text and "closeup" not in text):
        dy = -1
    elif any(k in text for k in ("downward", "descend", "sink", "settle", "cascade down",
                                  "tumble down", "slide down", "roll down", "drip down")):
        dy = 1
    # radial/lateral/inward/outward 方向标记
    if "radial" in text or "radiate outward" in text or "fan out" in text:
        dx, dy = 0.0, -1.0  # 向外辐射，用向上示意
    elif "lateral" in text or "sideways" in text:
        dx, dy = 1.0, 0.0
    elif "inward" in text or "toward center" in text:
        dx, dy = 0.0, 1.0  # 向内聚拢，用向下示意
    mag = math.hypot(dx, dy)
    direction = (dx / mag, dy / mag) if mag else (0.0, 0.0)

    # 5. 粒子效果（关键词扩展覆盖 LLM 实际用词）
    particles: List[str] = []
    if motion_type in ("crumble", "stretch") or any(
            k in text for k in ("crumb", "frag", "piece", "chip", "shard",
                                 "flake", "scrap", "bit", "morsel", "crumb")):
        particles.append("crumbs")
    if motion_type == "splash" or any(
            k in text for k in ("splash", "water", "liquid", "droplet", "drip",
                                 "spray", "sprinkle", "shower", "scatter")):
        particles.append("splash")
    if any(k in text for k in ("dust", "powder", "puff", "cloud",
                                "scallion", "matcha", "cocoa", "flour", "sugar")):
        particles.append("dust")
    if any(k in text for k in ("steam", "vapor", "smoke", "mist",
                                "aroma", "waft", "wisps")):
        particles.append("steam")

    # 6. 镜头运动（关键词扩展覆盖 LLM 运镜预设实际用词）
    camera_motion = "static"
    if any(k in cam_text for k in ("zoom", "push", "push-in", "dolly", "macro",
                                    "close-up", "closeup", "snap zoom", "slow push",
                                    "rack focus", "pull back", "pull focus")):
        camera_motion = "zoom_in"
    elif any(k in cam_text for k in ("pan", "whip pan", "tilt", "sweep",
                                      "slide across", "lateral")):
        camera_motion = "pan_left"
    elif any(k in cam_text for k in ("orbit", "rotate", "spin", "revolv", "aroun",
                                      "arc shot", "overhead rotation", "circular")):
        camera_motion = "orbit"

    # 7. 主体大小：特写镜头放大
    size = (240, 160)
    if "macro" in cam_text or "close" in cam_text:
        size = (300, 200)
    elif shape == "round":
        size = (200, 200)
    elif shape == "cylinder":
        size = (200, 260)

    return MotionSketchData(
        frame_num=frame_num,
        product_shape=shape,
        product_size=size,
        motion_type=motion_type,
        motion_direction=direction,
        motion_speed=speed,
        particles=particles,
        camera_motion=camera_motion,
        description=description,
    )


# ========== 程序化渲染器 ==========

class MotionSketchRenderer:
    """黑白线稿运动示意图渲染器（手绘风格，线条较粗）"""

    def __init__(self, width: int = 1024, height: int = 576, seed: int = 42):
        self.width = width
        self.height = height
        self._seed = seed
        self.bg_color = (245, 245, 248)
        self.line_color = (30, 30, 35)
        self.arrow_color = (60, 60, 70)
        self.particle_color = (100, 100, 110)
        self.text_color = (50, 50, 55)
        self.dash_color = (120, 120, 130)

    def render(self, data: MotionSketchData) -> Image.Image:
        """渲染一帧运动示意图"""
        random.seed(self._seed + data.frame_num)
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        self._draw_frame_border(draw)
        self._draw_motion_ghosts(draw, data)
        self._draw_product(draw, data)
        self._draw_break_marks(draw, data)
        self._draw_motion_arrows(draw, data)
        self._draw_particles(draw, data)
        self._draw_camera_indicator(draw, data)
        self._draw_subject_marker(draw, data)
        self._draw_annotations(draw, data)
        return img

    def _draw_frame_border(self, draw: ImageDraw.Draw):
        margin = 20
        draw.rectangle(
            [margin, margin, self.width - margin, self.height - margin],
            outline=self.line_color, width=3,
        )
        cx, cy = self.width // 2, self.height // 2
        draw.line([(cx - 8, cy), (cx + 8, cy)], fill=self.dash_color, width=1)
        draw.line([(cx, cy - 8), (cx, cy + 8)], fill=self.dash_color, width=1)

    def _draw_product(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画产品轮廓（黑白线稿，只画主体示意）"""
        cx, cy = data.product_position
        w, h = data.product_size

        if data.product_shape == "round":
            draw.ellipse(
                [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
                outline=self.line_color, width=4,
            )
            draw.arc([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
                     start=200, end=340, fill=self.dash_color, width=2)
            draw.arc([cx - w // 2 + 10, cy - h // 2 + 10, cx + w // 2 - 10, cy + h // 2 - 10],
                     start=210, end=330, fill=self.dash_color, width=2)
        elif data.product_shape == "rect":
            draw.rectangle(
                [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
                outline=self.line_color, width=4,
            )
            for i in range(1, 4):
                y_offset = cy - h // 2 + (h * i // 4)
                draw.line([(cx - w // 2 + 6, y_offset), (cx + w // 2 - 6, y_offset)],
                          fill=self.dash_color, width=2)
        elif data.product_shape == "cylinder":
            top_y = cy - h // 2
            bot_y = cy + h // 2
            ellipse_h = max(15, h // 6)
            draw.line([(cx - w // 2, top_y), (cx - w // 2, bot_y)],
                      fill=self.line_color, width=4)
            draw.line([(cx + w // 2, top_y), (cx + w // 2, bot_y)],
                      fill=self.line_color, width=4)
            draw.ellipse([cx - w // 2, top_y - ellipse_h // 2,
                          cx + w // 2, top_y + ellipse_h // 2],
                         outline=self.line_color, width=3)
            draw.arc([cx - w // 2, bot_y - ellipse_h // 2,
                      cx + w // 2, bot_y + ellipse_h // 2],
                     start=0, end=180, fill=self.line_color, width=3)
            draw.arc([cx - w // 2, bot_y - ellipse_h // 2,
                      cx + w // 2, bot_y + ellipse_h // 2],
                     start=180, end=360, fill=self.dash_color, width=2)
        else:  # irregular
            points = []
            num_points = 8
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                r = w // 2 * (0.7 + 0.3 * math.sin(angle * 3))
                px = cx + r * math.cos(angle)
                py = cy + (h // 2) * (0.7 + 0.3 * math.cos(angle * 2)) * math.sin(angle)
                points.append((px, py))
            draw.polygon(points, outline=self.line_color, width=4)
            for i in range(3):
                start = points[i * 2]
                end = points[(i * 2 + 3) % len(points)]
                mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                draw.line([start, mid, end], fill=self.dash_color, width=2)

    def _draw_motion_arrows(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画运动方向箭头（手绘流线风格）"""
        cx, cy = data.product_position
        dx, dy = data.motion_direction
        if (dx, dy) == (0, 0):
            return

        speed_map = {"slow": 90, "medium": 140, "fast": 190}
        arrow_len = speed_map.get(data.motion_speed, 110)

        perp_dx, perp_dy = -dy, dx
        for i in range(3):
            offset = (i - 1) * 14
            sx = cx + perp_dx * offset + dx * data.product_size[0] * 0.4
            sy = cy + perp_dy * offset + dy * data.product_size[1] * 0.4
            ex = sx + dx * arrow_len
            ey = sy + dy * arrow_len
            bow = (i - 1) * 10
            mid = ((sx + ex) / 2 + perp_dx * bow,
                   (sy + ey) / 2 + perp_dy * bow)
            self._draw_curved_line(draw, (sx, sy), mid, (ex, ey),
                                   self.arrow_color, width=3, wobble=2.0)
            if i == 1:
                self._draw_arrow_head(draw, (ex, ey), (dx, dy),
                                      size=16, color=self.arrow_color, width=3)

        if data.motion_type in ("crumble", "splash"):
            base_angle = math.atan2(dy, dx)
            for i in range(3):
                angle = base_angle + (i - 1) * 0.55
                adx, ady = math.cos(angle), math.sin(angle)
                small_len = arrow_len * 0.5
                sx = cx + adx * (data.product_size[0] // 2 + 10)
                sy = cy + ady * (data.product_size[1] // 2 + 10)
                ex, ey = sx + adx * small_len, sy + ady * small_len
                self._draw_sketchy_line(draw, (sx, sy), (ex, ey),
                                        self.particle_color, width=2, wobble=1.2)
                self._draw_arrow_head(draw, (ex, ey), (adx, ady),
                                      size=9, color=self.particle_color, width=2)
        elif data.motion_type == "stretch":
            perp_dx, perp_dy = -dy, dx
            for sign in (-1, 1):
                sx = cx + perp_dx * sign * 20
                sy = cy + perp_dy * sign * 20
                ex, ey = sx + dx * arrow_len * 0.7, sy + dy * arrow_len * 0.7
                self._draw_sketchy_line(draw, (sx, sy), (ex, ey),
                                        self.particle_color, width=2, wobble=1.2)
                self._draw_arrow_head(draw, (ex, ey), (dx, dy),
                                      size=9, color=self.particle_color, width=2)

    def _draw_particles(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画粒子效果符号（从主体边缘向外飞散）"""
        cx, cy = data.product_position
        dx, dy = data.motion_direction
        w, h = data.product_size
        base_angle = math.atan2(dy, dx) if (dx, dy) != (0, 0) else -math.pi / 2

        def edge_point(angle: float, spread: float = 8.0):
            return (cx + math.cos(angle) * (w / 2 + spread),
                    cy + math.sin(angle) * (h / 2 + spread))

        for particle in data.particles:
            if particle == "splash":
                for i in range(3):
                    angle = base_angle + (i - 1) * 0.5
                    px, py = edge_point(angle, 6 + i * 16)
                    r = max(2, 7 - i * 2)
                    draw.ellipse([px - r, py - r, px + r, py + r],
                                 outline=self.particle_color, width=2)
                    tx = px - math.cos(angle) * 12
                    ty = py - math.sin(angle) * 12
                    self._draw_sketchy_line(draw, (tx, ty), (px, py),
                                            self.particle_color, width=2, wobble=1.0)
                arc_start = base_angle - 0.8
                arc_end = base_angle + 0.8
                self._draw_arc_line(draw, cx, cy, max(w, h) // 2 + 20,
                                    arc_start, arc_end, self.particle_color, wobble=1.5)
            elif particle == "crumbs":
                for i in range(6):
                    if i < 4:
                        angle = base_angle + random.uniform(-0.7, 0.7)
                    else:
                        angle = random.uniform(0, 2 * math.pi)
                    px, py = edge_point(angle, random.uniform(4, 22))
                    size = random.randint(3, 6)
                    shape = random.choice(["triangle", "square"])
                    if shape == "triangle":
                        draw.polygon(
                            [(px, py - size), (px - size, py + size), (px + size, py + size)],
                            outline=self.particle_color, width=2,
                        )
                    else:
                        draw.rectangle(
                            [px - size, py - size, px + size, py + size],
                            outline=self.particle_color, width=2,
                        )
            elif particle == "dust":
                for i in range(8):
                    angle = base_angle + random.uniform(-1.2, 1.2)
                    px, py = edge_point(angle, random.uniform(2, 32))
                    r = random.randint(1, 3)
                    draw.ellipse([px - r, py - r, px + r, py + r],
                                 fill=self.particle_color)
            elif particle == "steam":
                for i in range(3):
                    start_y = cy - h // 2 - 10
                    x_offset = cx + (i - 1) * 15
                    points = []
                    for j in range(20):
                        t = j / 19
                        y = start_y - t * 60
                        x = x_offset + math.sin(t * math.pi * 2 + i) * 8
                        points.append((x, y))
                    for k in range(len(points) - 1):
                        draw.line([points[k], points[k + 1]],
                                  fill=self.particle_color, width=2)

    def _draw_camera_indicator(self, draw: ImageDraw.Draw, data: MotionSketchData):
        margin = 20
        if data.camera_motion == "zoom_in":
            arrow_size = 20
            for corner in [(margin, margin), (self.width - margin, margin),
                           (margin, self.height - margin),
                           (self.width - margin, self.height - margin)]:
                cx, cy = corner
                center_x, center_y = self.width // 2, self.height // 2
                dx = (center_x - cx) / max(1, abs(center_x - cx))
                dy = (center_y - cy) / max(1, abs(center_y - cy))
                ex, ey = cx + dx * arrow_size, cy + dy * arrow_size
                draw.line([(cx, cy), (ex, ey)], fill=self.arrow_color, width=3)
                self._draw_arrow_head(draw, (ex, ey), (dx, dy),
                                      size=8, color=self.arrow_color)
        elif data.camera_motion == "pan_left":
            y = self.height // 2
            draw.line([(self.width - 40, y), (self.width - 70, y)],
                      fill=self.arrow_color, width=3)
            self._draw_arrow_head(draw, (self.width - 70, y), (-1, 0),
                                  size=8, color=self.arrow_color)
            draw.text((self.width - 80, y + 10), "PAN \u2190", fill=self.text_color)
        elif data.camera_motion == "orbit":
            cx, cy = self.width // 2, self.height // 2
            r = min(self.width, self.height) // 2 - 40
            draw.arc([cx - r, cy - r, cx + r, cy + r],
                     start=200, end=340, fill=self.arrow_color, width=3)
            angle_rad = math.radians(340)
            ex = cx + r * math.cos(angle_rad)
            ey = cy + r * math.sin(angle_rad)
            self._draw_arrow_head(draw, (ex, ey), (0.3, 0.95),
                                  size=8, color=self.arrow_color)

    def _draw_annotations(self, draw: ImageDraw.Draw, data: MotionSketchData):
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 11)
            font_cn = ImageFont.truetype("msyh.ttc", 13)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 14)
                font_small = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 11)
                font_cn = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 13)
            except (OSError, IOError):
                font = ImageFont.load_default()
                font_small = font
                font_cn = font

        draw.text((30, 5), f"FRAME {data.frame_num}", fill=self.text_color, font=font)
        motion_labels = {
            "crumble": "CRUMBLE", "splash": "SPLASH", "stretch": "STRETCH",
            "drop": "DROP", "rotate": "ROTATE", "slide": "SLIDE",
        }
        label = motion_labels.get(data.motion_type, data.motion_type.upper())
        bbox = draw.textbbox((0, 0), label, font=font_small)
        draw.text((self.width - 30 - (bbox[2] - bbox[0]), 5), label,
                  fill=self.text_color, font=font_small)
        if data.description:
            draw.text((30, self.height - 35), data.description,
                      fill=self.text_color, font=font_cn)
        speed_label = f"SPEED: {data.motion_speed.upper()}"
        bbox = draw.textbbox((0, 0), speed_label, font=font_small)
        draw.text((self.width - 30 - (bbox[2] - bbox[0]), self.height - 25),
                  speed_label, fill=self.text_color, font=font_small)

    def _draw_motion_ghosts(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画运动残影：沿运动反方向的虚线轮廓（只画 1 个，减少视觉杂乱）"""
        dx, dy = data.motion_direction
        if (dx, dy) == (0, 0):
            return
        cx, cy = data.product_position
        w, h = data.product_size
        k = 1
        gx = int(cx - dx * w * 0.55 * k)
        gy = int(cy - dy * h * 0.55 * k)
        gw = max(24, w - 28)
        gh = max(24, h - 28)
        self._draw_ghost_shape(draw, data.product_shape, gx, gy, gw, gh)

    def _draw_ghost_shape(self, draw, shape, cx, cy, w, h):
        color = self.dash_color
        if shape == "round":
            for a in range(0, 360, 12):
                rad1, rad2 = math.radians(a), math.radians(a + 8)
                x1 = cx + (w / 2) * math.cos(rad1)
                y1 = cy + (h / 2) * math.sin(rad1)
                x2 = cx + (w / 2) * math.cos(rad2)
                y2 = cy + (h / 2) * math.sin(rad2)
                draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
        elif shape == "cylinder":
            top_y, bot_y = cy - h // 2, cy + h // 2
            self._draw_dashed_line(draw, (cx - w // 2, top_y), (cx - w // 2, bot_y),
                                   color, width=2, dash_len=6, gap_len=4)
            self._draw_dashed_line(draw, (cx + w // 2, top_y), (cx + w // 2, bot_y),
                                   color, width=2, dash_len=6, gap_len=4)
            for a in range(180, 361, 15):
                rad1, rad2 = math.radians(a), math.radians(a + 10)
                x1 = cx + (w / 2) * math.cos(rad1)
                y1 = top_y + (h // 6) * math.sin(rad1)
                x2 = cx + (w / 2) * math.cos(rad2)
                y2 = top_y + (h // 6) * math.sin(rad2)
                draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
        else:
            x1, y1 = cx - w // 2, cy - h // 2
            x2, y2 = cx + w // 2, cy + h // 2
            self._draw_dashed_line(draw, (x1, y1), (x2, y1), color, width=2, dash_len=8, gap_len=5)
            self._draw_dashed_line(draw, (x2, y1), (x2, y2), color, width=2, dash_len=8, gap_len=5)
            self._draw_dashed_line(draw, (x2, y2), (x1, y2), color, width=2, dash_len=8, gap_len=5)
            self._draw_dashed_line(draw, (x1, y2), (x1, y1), color, width=2, dash_len=8, gap_len=5)

    def _draw_break_marks(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画碎裂/断裂标记：轮廓边缘缺口刻痕 + 内部裂纹（减少数量，降低视觉杂乱）"""
        if data.motion_type not in ("crumble", "stretch"):
            return
        cx, cy = data.product_position
        w, h = data.product_size
        for i in range(4):
            angle = 2 * math.pi * i / 4 + 0.4
            ex = cx + math.cos(angle) * (w / 2 + 4)
            ey = cy + math.sin(angle) * (h / 2 + 4)
            x1 = ex - math.cos(angle) * 7
            y1 = ey - math.sin(angle) * 7
            x2 = ex + math.cos(angle) * 7
            y2 = ey + math.sin(angle) * 7
            draw.line([(x1, y1), (x2, y2)], fill=self.particle_color, width=2)
        for _ in range(1):
            sx = cx + random.randint(-w // 4, w // 4)
            sy = cy + random.randint(-h // 4, h // 4)
            pts = [(sx, sy)]
            px, py = sx, sy
            for _ in range(2):
                px += random.randint(-20, 20)
                py += random.randint(-20, 20)
                pts.append((px, py))
            for i in range(len(pts) - 1):
                draw.line([pts[i], pts[i + 1]], fill=self.particle_color, width=2)

    def _draw_subject_marker(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画主体标记：V 形指针 + SUBJECT 标签"""
        cx, cy = data.product_position
        bottom = cy + data.product_size[1] // 2 + 6
        tip = (cx, bottom)
        base1 = (cx - 8, bottom + 26)
        base2 = (cx + 8, bottom + 26)
        draw.line([base1, tip], fill=self.text_color, width=3)
        draw.line([base2, tip], fill=self.text_color, width=3)
        try:
            font = ImageFont.truetype("arial.ttf", 13)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((cx + 14, bottom + 14), "SUBJECT", fill=self.text_color, font=font)

    # ========== 辅助绘制 ==========

    def _draw_dashed_line(self, draw, start, end, color, width=2, dash_len=6, gap_len=3):
        sx, sy = start
        ex, ey = end
        total_len = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
        if total_len == 0:
            return
        dx = (ex - sx) / total_len
        dy = (ey - sy) / total_len
        pos = 0
        while pos < total_len:
            dash_end = min(pos + dash_len, total_len)
            draw.line([(sx + dx * pos, sy + dy * pos),
                       (sx + dx * dash_end, sy + dy * dash_end)],
                      fill=color, width=width)
            pos += dash_len + gap_len

    def _draw_arrow_head(self, draw, tip, direction, size=10, color=(0, 0, 0), width=2):
        """开口箭头（手绘 V 形，不填充）"""
        tx, ty = tip
        dx, dy = direction
        mag = math.sqrt(dx * dx + dy * dy)
        if mag == 0:
            return
        dx /= mag
        dy /= mag
        px, py = -dy, dx
        p2 = (tx - dx * size + px * size * 0.45, ty - dy * size + py * size * 0.45)
        p3 = (tx - dx * size - px * size * 0.45, ty - dy * size - py * size * 0.45)
        draw.line([p2, (tx, ty)], fill=color, width=width)
        draw.line([p3, (tx, ty)], fill=color, width=width)

    def _draw_arc_line(self, draw, cx, cy, radius, start_angle, end_angle, color, wobble=0.0):
        points = []
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            angle = start_angle + (end_angle - start_angle) * t
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            if wobble and 0 < i < steps:
                x += random.uniform(-wobble, wobble)
                y += random.uniform(-wobble, wobble)
            points.append((x, y))
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=color, width=2)

    def _draw_sketchy_line(self, draw, start, end, color, width=2, wobble=1.5, segments=8):
        sx, sy = start
        ex, ey = end
        for i in range(segments):
            t0, t1 = i / segments, (i + 1) / segments
            j0 = random.uniform(-wobble, wobble) if i else 0
            k0 = random.uniform(-wobble, wobble) if i else 0
            j1 = random.uniform(-wobble, wobble) if i < segments - 1 else 0
            k1 = random.uniform(-wobble, wobble) if i < segments - 1 else 0
            x1 = sx + (ex - sx) * t0 + j0
            y1 = sy + (ey - sy) * t0 + k0
            x2 = sx + (ex - sx) * t1 + j1
            y2 = sy + (ey - sy) * t1 + k1
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

    def _draw_curved_line(self, draw, start, mid, end, color, width=3, wobble=1.5, steps=16):
        sx, sy = start
        mx, my = mid
        ex, ey = end
        prev = None
        for i in range(steps + 1):
            t = i / steps
            inv = 1 - t
            x = inv * inv * sx + 2 * inv * t * mx + t * t * ex
            y = inv * inv * sy + 2 * inv * t * my + t * t * ey
            if 0 < i < steps:
                x += random.uniform(-wobble, wobble)
                y += random.uniform(-wobble, wobble)
            pt = (x, y)
            if prev:
                draw.line([prev, pt], fill=color, width=width)
            prev = pt


# ========== AI 模式提示词 ==========

DEFAULT_AI_PROMPT = (
    "black and white rough line sketch, motion storyboard blueprint, "
    "a single simple {shape} as the subject, no product detail, no color, "
    "hand-drawn style arrows showing {direction} {motion} at {speed} speed, "
    "particle marks ({particles}) bursting outward, {camera}, "
    "scene context: {description}, "
    "minimal line art, white background, schematic diagram style, "
    "clean composition, no clutter, easy to read"
)

DEFAULT_HYBRID_PROMPT = (
    "Preserve this motion sketch exactly as-is: same composition, "
    "same subject outline, arrows, particle marks and camera marks. "
    "Clean up rough edges only, keep black and white line style, "
    "no color, no product detail, no extra elements."
)

_SHAPE_NAMES = {
    "round": "round blob",
    "rect": "rectangular box",
    "cylinder": "cylinder",
    "irregular": "irregular shape",
}
_MOTION_NAMES = {
    "slide": "sliding",
    "crumble": "crumbling apart",
    "splash": "splashing",
    "stretch": "stretching",
    "drop": "dropping",
    "rotate": "rotating",
}
_CAMERA_NAMES = {
    "zoom_in": "camera zooming in",
    "pan_left": "camera panning left",
    "orbit": "camera orbiting",
    "static": "static camera",
}
_DIRECTION_NAMES = {
    "(-1,0)": "moving left",
    "(1,0)": "moving right",
    "(0,-1)": "moving up",
    "(0,1)": "moving down",
}


class _SafeDict(dict):
    """未知占位符原样保留，避免用户模板里写了别的变量名直接报错"""

    def __missing__(self, key):
        return "{" + key + "}"


def prompt_vars(data: MotionSketchData) -> dict:
    """提示词模板可用的占位符变量"""
    dx, dy = data.motion_direction
    dir_key = f"({int(dx)},{int(dy)})"
    return {
        "shape": _SHAPE_NAMES.get(data.product_shape, "simple shape"),
        "motion": _MOTION_NAMES.get(data.motion_type, data.motion_type),
        "direction": _DIRECTION_NAMES.get(dir_key, "in a specified direction"),
        "speed": data.motion_speed,
        "particles": "、".join(data.particles) if data.particles else "none",
        "camera": _CAMERA_NAMES.get(data.camera_motion, "static camera"),
        "description": data.description,
    }


def build_ai_sketch_prompt(data: MotionSketchData, template: str = None) -> str:
    """生成 Agnes AI 模式的运动示意图提示词。

    template 为空时使用 DEFAULT_AI_PROMPT；支持占位符：
    {shape} {motion} {direction} {speed} {particles} {camera} {description}
    """
    tpl = template or DEFAULT_AI_PROMPT
    return tpl.format_map(_SafeDict(prompt_vars(data)))


# ========== 统一生成入口 ==========

def _parse_size(size: str) -> Tuple[int, int]:
    m = re.match(r"(\d+)\s*[xX]\s*(\d+)", str(size))
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1024, 576


def _download(url: str, output_path: str) -> None:
    import httpx
    with httpx.Client(timeout=180.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)


def _agnes_img2img(mgr, local_path: str, size: str,
                   prompt: str = None) -> Tuple[bool, str, str]:
    """把本地底稿传给 Agnes 图生图，返回 (成功, 公网URL, 信息)"""
    with open(local_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"
    cfg = mgr.image_config
    base_url = str(cfg.get("base_url", "")).rstrip("/")
    api_key = cfg.get("api_key", "")
    model = cfg.get("model", "") or "agnes-image-2.1-flash"
    url = f"{base_url}/images/generations"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "prompt": prompt or DEFAULT_HYBRID_PROMPT,
        "size": size,
        "extra_body": {
            "image": [data_uri],
            "response_format": "url",
        },
    }
    import httpx
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    image_url = data["data"][0].get("url", "")
    if not image_url:
        return False, "", f"未获取到图片URL: {data}"
    return True, image_url, "ok"


def generate_motion_sketch(mgr, frame: dict, sketch_config: dict, output_path: str,
                           on_progress=None):
    """生成运动示意图。

    Args:
        mgr: GenerationManager（含 image 配置）
        frame: 分镜帧 dict
        sketch_config: storyboard.motion_sketch 配置 dict（enabled/mode/size）
        output_path: 本地保存路径
        on_progress: 可选回调 (percent, text)，用于 UI 进度反馈

    Returns:
        (ok, local_path, public_url, message)
    """
    def report(pct: int, text: str):
        if on_progress:
            try:
                on_progress(pct, text)
            except Exception:
                pass

    data = from_frame(frame)
    mode = sketch_config.get("mode", "programmatic")
    size = sketch_config.get("size", "1024x576")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if mode == "programmatic":
        report(30, "解析分镜，生成运动信息")
        w, h = _parse_size(size)
        renderer = MotionSketchRenderer(width=w, height=h)
        report(60, "程序化绘制草稿图...")
        renderer.render(data).save(output_path)
        report(100, "完成")
        return True, output_path, "", "程序化绘制完成"

    if mode not in ("ai", "hybrid"):
        return False, "", "", f"不支持的运动示意图模式: {mode}"

    provider = mgr.image_config.get("provider", "")
    if provider != "agnes":
        return False, "", "", (
            f"AI/混合模式需要图片 provider=agnes（当前 {provider}），"
            "请到设置中切换，或用程序化模式"
        )

    if mode == "hybrid":
        report(10, "绘制本地底稿...")
        base_path = output_path + ".base.png"
        w, h = _parse_size(size)
        renderer = MotionSketchRenderer(width=w, height=h)
        renderer.render(data).save(base_path)
        report(40, "调用生图接口精修（Agnes 图生图）...")
        hybrid_prompt = sketch_config.get("hybrid_prompt") or DEFAULT_HYBRID_PROMPT
        ok, url, msg = _agnes_img2img(mgr, base_path, size, hybrid_prompt)
        try:
            if os.path.exists(base_path):
                os.remove(base_path)
        except OSError:
            pass
        if not ok:
            report(100, "失败")
            return False, "", "", f"Agnes 图生图失败: {msg}"
        report(75, "下载精修结果...")
        _download(url, output_path)
        report(100, "完成")
        return True, output_path, url, f"混合模式完成（公网URL: {url}）"

    # mode == "ai"
    template = sketch_config.get("ai_prompt") or DEFAULT_AI_PROMPT
    prompt = build_ai_sketch_prompt(data, template)
    report(30, "调用生图接口（Agnes 文生图）...")
    ok, url, msg = mgr.generate_image_url(prompt, size=size)
    if not ok:
        report(100, "失败")
        return False, "", "", f"Agnes 生成失败: {msg}"
    report(75, "下载生成结果...")
    _download(url, output_path)
    report(100, "完成")
    return True, output_path, url, f"AI 生成完成（公网URL: {url}）"
