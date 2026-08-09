"""分镜头运动示意图原型 - 黑白线稿风格

路线 2（程序化绘制）+ 路线 1（AI 生成）结合的原型：
1. 路线 2: 用 Pillow 程序化绘制黑白线稿 + 箭头 + 粒子符号
2. 路线 1: 可选叠加 AI 生成的纹理细节（后续接入 Agnes API）

运行: python prototype_motion_sketch.py
输出: prototype_output/ 目录下的 PNG 文件
"""

from PIL import Image, ImageDraw, ImageFont
import math
import random
import os
from dataclasses import dataclass
from typing import Optional


# ========== 数据结构 ==========

@dataclass
class MotionSketchData:
    """单帧运动示意图数据（从 LLM 分镜结果映射）"""
    frame_num: int
    product_shape: str          # "round", "rect", "cylinder", "irregular"
    product_size: tuple         # (width, height) in canvas units
    product_position: tuple     # (x, y) center position
    motion_type: str            # "crumble", "splash", "stretch", "drop", "rotate", "slide"
    motion_direction: tuple     # (dx, dy) unit vector
    motion_speed: str           # "slow", "medium", "fast"
    particles: list             # ["splash", "crumbs", "dust", "steam"]
    camera_motion: str          # "zoom_in", "pan_left", "orbit", "static"
    description: str            # 中文描述


# ========== 绘制工具 ==========

class MotionSketchRenderer:
    """黑白线稿运动示意图渲染器"""

    def __init__(self, width=1024, height=576, seed=42):
        self.width = width
        self.height = height
        self._seed = seed
        self.bg_color = (245, 245, 248)  # 浅灰白
        self.line_color = (30, 30, 35)   # 近黑
        self.arrow_color = (60, 60, 70)  # 深灰
        self.particle_color = (100, 100, 110)  # 中灰
        self.text_color = (50, 50, 55)
        self.dash_color = (120, 120, 130)

    def render(self, data: MotionSketchData) -> Image.Image:
        """渲染一帧运动示意图"""
        random.seed(self._seed + data.frame_num)  # 固定种子，保证可复现
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        # 1. 画框线
        self._draw_frame_border(draw)

        # 2. 画运动残影（起始位置的虚线轮廓）
        self._draw_motion_ghosts(draw, data)

        # 3. 画产品轮廓（破碎类用断裂虚线）
        self._draw_product(draw, data)

        # 3b. 碎裂/断裂标记（轮廓缺口 + 内部裂纹）
        self._draw_break_marks(draw, data)

        # 4. 画运动箭头（手绘流线 + 开口箭头）
        self._draw_motion_arrows(draw, data)

        # 5. 画粒子效果（从轮廓边缘向外飞出）
        self._draw_particles(draw, data)

        # 6. 画镜头运动指示
        self._draw_camera_indicator(draw, data)

        # 7. 主体标记（让 AI 知道谁是主角）
        self._draw_subject_marker(draw, data)

        # 8. 画标注文字
        self._draw_annotations(draw, data)

        return img

    def _draw_frame_border(self, draw: ImageDraw.Draw):
        """画画面边框"""
        margin = 20
        draw.rectangle(
            [margin, margin, self.width - margin, self.height - margin],
            outline=self.line_color, width=3
        )
        # 画对角线参考点（构图标记）
        cx, cy = self.width // 2, self.height // 2
        for x, y in [(cx, cy)]:
            draw.line([(x-8, y), (x+8, y)], fill=self.dash_color, width=1)
            draw.line([(x, y-8), (x, y+8)], fill=self.dash_color, width=1)

    def _draw_product(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画产品轮廓（黑白线稿风格）"""
        cx, cy = data.product_position
        w, h = data.product_size

        if data.product_shape == "round":
            # 圆形/球形产品
            draw.ellipse(
                [cx - w//2, cy - h//2, cx + w//2, cy + h//2],
                outline=self.line_color, width=4
            )
            # 内部纹理线（表示球面）
            draw.arc(
                [cx - w//2, cy - h//2, cx + w//2, cy + h//2],
                start=200, end=340, fill=self.dash_color, width=1
            )
            draw.arc(
                [cx - w//2 + 10, cy - h//2 + 10, cx + w//2 - 10, cy + h//2 - 10],
                start=210, end=330, fill=self.dash_color, width=1
            )

        elif data.product_shape == "rect":
            # 矩形/方形产品
            draw.rectangle(
                [cx - w//2, cy - h//2, cx + w//2, cy + h//2],
                outline=self.line_color, width=4
            )
            # 内部分层线（表示截面层次）
            for i in range(1, 4):
                y_offset = cy - h//2 + (h * i // 4)
                draw.line(
                    [(cx - w//2 + 5, y_offset), (cx + w//2 - 5, y_offset)],
                    fill=self.dash_color, width=1
                )

        elif data.product_shape == "cylinder":
            # 圆柱形产品
            top_y = cy - h//2
            bot_y = cy + h//2
            ellipse_h = max(15, h // 6)
            # 主体
            draw.line([(cx - w//2, top_y), (cx - w//2, bot_y)], fill=self.line_color, width=4)
            draw.line([(cx + w//2, top_y), (cx + w//2, bot_y)], fill=self.line_color, width=4)
            # 顶部椭圆
            draw.ellipse(
                [cx - w//2, top_y - ellipse_h//2, cx + w//2, top_y + ellipse_h//2],
                outline=self.line_color, width=3
            )
            # 底部椭圆（前半部分实线）
            draw.arc(
                [cx - w//2, bot_y - ellipse_h//2, cx + w//2, bot_y + ellipse_h//2],
                start=0, end=180, fill=self.line_color, width=2
            )
            draw.arc(
                [cx - w//2, bot_y - ellipse_h//2, cx + w//2, bot_y + ellipse_h//2],
                start=180, end=360, fill=self.dash_color, width=1
            )

        elif data.product_shape == "irregular":
            # 不规则形状（用多边形近似）
            points = []
            num_points = 8
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                r = w // 2 * (0.7 + 0.3 * math.sin(angle * 3))
                px = cx + r * math.cos(angle)
                py = cy + (h // 2) * (0.7 + 0.3 * math.cos(angle * 2)) * math.sin(angle)
                points.append((px, py))
            draw.polygon(points, outline=self.line_color, width=4)
            # 内部裂纹线
            for i in range(3):
                start = points[i * 2]
                end = points[(i * 2 + 3) % len(points)]
                mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                draw.line([start, mid, end], fill=self.dash_color, width=1)

    def _draw_motion_arrows(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画运动方向箭头（手绘流线风格，避免工程化直线）"""
        cx, cy = data.product_position
        dx, dy = data.motion_direction

        if (dx, dy) == (0, 0):
            return

        # 箭头长度根据速度
        speed_map = {"slow": 90, "medium": 140, "fast": 190}
        arrow_len = speed_map.get(data.motion_speed, 110)

        # 主方向：3 条轻微弯曲的流线（手绘感）
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
            # 只有中间那条画箭头头，避免太密
            if i == 1:
                self._draw_arrow_head(draw, (ex, ey), (dx, dy),
                                      size=16, color=self.arrow_color, width=3)

        # 如果是碎裂/飞溅，画多个放射小箭头（从边缘向外）
        if data.motion_type in ("crumble", "splash"):
            num_arrows = 6
            base_angle = math.atan2(dy, dx)
            for i in range(num_arrows):
                angle = base_angle + (i - 2.5) * 0.55
                adx = math.cos(angle)
                ady = math.sin(angle)
                small_len = arrow_len * 0.5
                sx = cx + adx * (data.product_size[0] // 2 + 10)
                sy = cy + ady * (data.product_size[1] // 2 + 10)
                ex = sx + adx * small_len
                ey = sy + ady * small_len
                self._draw_sketchy_line(draw, (sx, sy), (ex, ey),
                                        self.particle_color, width=2, wobble=1.2)
                self._draw_arrow_head(draw, (ex, ey), (adx, ady),
                                      size=9, color=self.particle_color, width=2)

        # 如果是拉伸/延展，画变形箭头
        elif data.motion_type == "stretch":
            perp_dx = -dy
            perp_dy = dx
            for sign in [-1, 1]:
                sx = cx + perp_dx * sign * 20
                sy = cy + perp_dy * sign * 20
                ex = sx + dx * arrow_len * 0.7
                ey = sy + dy * arrow_len * 0.7
                self._draw_sketchy_line(draw, (sx, sy), (ex, ey),
                                        self.particle_color, width=2, wobble=1.2)
                self._draw_arrow_head(draw, (ex, ey), (dx, dy),
                                      size=9, color=self.particle_color, width=2)

    def _draw_particles(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画粒子效果符号（从主体边缘向外飞散，避免堆在轮廓内）"""
        cx, cy = data.product_position
        dx, dy = data.motion_direction
        w, h = data.product_size
        base_angle = math.atan2(dy, dx) if (dx, dy) != (0, 0) else -math.pi / 2

        def edge_point(angle: float, spread: float = 8.0):
            """从椭圆边缘向外取点，保证粒子飞出轮廓"""
            ex = cx + math.cos(angle) * (w / 2 + spread)
            ey = cy + math.sin(angle) * (h / 2 + spread)
            return ex, ey

        for particle in data.particles:
            if particle == "splash":
                # 水花：沿主方向扇区放射液滴（大小递减）+ 弧线
                for i in range(3):
                    angle = base_angle + (i - 1) * 0.5
                    px, py = edge_point(angle, 6 + i * 16)
                    r = max(2, 7 - i * 2)
                    draw.ellipse([px-r, py-r, px+r, py+r],
                                 outline=self.particle_color, width=2)
                    tx = px - math.cos(angle) * 12
                    ty = py - math.sin(angle) * 12
                    self._draw_sketchy_line(draw, (tx, ty), (px, py),
                                            self.particle_color, width=2, wobble=1.0)
                # 水花弧线（飞溅弧）
                arc_start = base_angle - 0.8
                arc_end = base_angle + 0.8
                self._draw_arc_line(draw, cx, cy, max(w, h) // 2 + 20,
                                    arc_start, arc_end, self.particle_color,
                                    wobble=1.5)

            elif particle == "crumbs":
                # 碎片：小三角/方块，从边缘向外飞出，沿主方向更密集
                for i in range(12):
                    if i < 8:
                        angle = base_angle + random.uniform(-0.9, 0.9)
                    else:
                        angle = random.uniform(0, 2 * math.pi)
                    px, py = edge_point(angle, random.uniform(4, 28))
                    size = random.randint(3, 7)
                    shape = random.choice(["triangle", "square"])
                    if shape == "triangle":
                        draw.polygon(
                            [(px, py - size), (px - size, py + size), (px + size, py + size)],
                            outline=self.particle_color, width=2
                        )
                    else:
                        draw.rectangle(
                            [px - size, py - size, px + size, py + size],
                            outline=self.particle_color, width=2
                        )

            elif particle == "dust":
                # 粉尘：小圆点群，从边缘向外散布
                for i in range(16):
                    angle = base_angle + random.uniform(-1.4, 1.4)
                    px, py = edge_point(angle, random.uniform(2, 42))
                    r = random.randint(1, 3)
                    draw.ellipse([px-r, py-r, px+r, py+r],
                                 fill=self.particle_color)

            elif particle == "steam":
                # 蒸汽：波浪线
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
                        draw.line([points[k], points[k+1]],
                                  fill=self.particle_color, width=2)

    def _draw_camera_indicator(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画镜头运动指示（画面边缘的箭头/标记）"""
        margin = 20

        if data.camera_motion == "zoom_in":
            # 放大：四角向内的箭头
            arrow_size = 20
            for corner in [(margin, margin), (self.width - margin, margin),
                          (margin, self.height - margin), (self.width - margin, self.height - margin)]:
                cx, cy = corner
                # 向中心的箭头
                center_x, center_y = self.width // 2, self.height // 2
                dx = (center_x - cx) / max(1, abs(center_x - cx))
                dy = (center_y - cy) / max(1, abs(center_y - cy))
                ex = cx + dx * arrow_size
                ey = cy + dy * arrow_size
                draw.line([(cx, cy), (ex, ey)], fill=self.arrow_color, width=3)
                self._draw_arrow_head(draw, (ex, ey), (dx, dy),
                                      size=8, color=self.arrow_color)

        elif data.camera_motion == "pan_left":
            # 左移：左右两侧的水平箭头
            y = self.height // 2
            # 右侧推出
            draw.line([(self.width - 40, y), (self.width - 70, y)],
                      fill=self.arrow_color, width=3)
            self._draw_arrow_head(draw, (self.width - 70, y), (-1, 0),
                                  size=8, color=self.arrow_color)
            # 标注
            draw.text((self.width - 80, y + 10), "PAN ←", fill=self.text_color)

        elif data.camera_motion == "orbit":
            # 环绕：弧形箭头
            cx, cy = self.width // 2, self.height // 2
            r = min(self.width, self.height) // 2 - 40
            # 上半弧
            draw.arc([cx - r, cy - r, cx + r, cy + r],
                     start=200, end=340, fill=self.arrow_color, width=3)
            # 箭头在弧线末端
            angle_rad = math.radians(340)
            ex = cx + r * math.cos(angle_rad)
            ey = cy + r * math.sin(angle_rad)
            self._draw_arrow_head(draw, (ex, ey), (0.3, 0.95),
                                  size=8, color=self.arrow_color)

    def _draw_annotations(self, draw: ImageDraw.Draw, data: MotionSketchData):
        """画标注文字"""
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 11)
            font_cn = ImageFont.truetype("msyh.ttc", 13)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 14)
                font_small = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 11)
                font_cn = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 13)
            except:
                font = ImageFont.load_default()
                font_small = font
                font_cn = font

        # 帧号（左上角）
        draw.text((30, 5), f"FRAME {data.frame_num}",
                  fill=self.text_color, font=font)

        # 运动类型标签（右上角）
        motion_labels = {
            "crumble": "CRUMBLE",
            "splash": "SPLASH",
            "stretch": "STRETCH",
            "drop": "DROP",
            "rotate": "ROTATE",
            "slide": "SLIDE",
        }
        label = motion_labels.get(data.motion_type, data.motion_type.upper())
        bbox = draw.textbbox((0, 0), label, font=font_small)
        label_w = bbox[2] - bbox[0]
        draw.text((self.width - 30 - label_w, 5), label,
                  fill=self.text_color, font=font_small)

        # 底部描述
        draw.text((30, self.height - 35), data.description,
                  fill=self.text_color, font=font_cn)

        # 速度标记
        speed_label = f"SPEED: {data.motion_speed.upper()}"
        bbox = draw.textbbox((0, 0), speed_label, font=font_small)
        label_w = bbox[2] - bbox[0]
        draw.text((self.width - 30 - label_w, self.height - 25), speed_label,
                  fill=self.text_color, font=font_small)

    # ========== 辅助绘制方法 ==========

    def _draw_dashed_line(self, draw, start, end, color, width=2, dash_len=6, gap_len=3):
        """画虚线"""
        sx, sy = start
        ex, ey = end
        total_len = math.sqrt((ex - sx)**2 + (ey - sy)**2)
        if total_len == 0:
            return
        dx = (ex - sx) / total_len
        dy = (ey - sy) / total_len
        pos = 0
        while pos < total_len:
            dash_end = min(pos + dash_len, total_len)
            x1 = sx + dx * pos
            y1 = sy + dy * pos
            x2 = sx + dx * dash_end
            y2 = sy + dy * dash_end
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            pos += dash_len + gap_len

    def _draw_arrow_head(self, draw, tip, direction, size=10, color=(0, 0, 0), width=2):
        """画开口箭头（手绘 V 形，不填充）"""
        tx, ty = tip
        dx, dy = direction
        mag = math.sqrt(dx*dx + dy*dy)
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
        """画弧线（可选手绘抖动）"""
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
            draw.line([points[i], points[i+1]], fill=color, width=2)

    def _draw_motion_ghosts(self, draw, data: MotionSketchData):
        """画运动残影：沿运动反方向的虚线轮廓，表示物体从哪里来"""
        dx, dy = data.motion_direction
        if (dx, dy) == (0, 0):
            return
        cx, cy = data.product_position
        w, h = data.product_size
        for i, k in enumerate([1, 2]):
            gx = int(cx - dx * w * 0.55 * k)
            gy = int(cy - dy * h * 0.55 * k)
            gw = max(24, w - i * 28)
            gh = max(24, h - i * 28)
            self._draw_ghost_shape(draw, data.product_shape, gx, gy, gw, gh)

    def _draw_ghost_shape(self, draw, shape, cx, cy, w, h):
        """画虚线残影轮廓"""
        color = self.dash_color
        if shape == "round":
            for a in range(0, 360, 12):
                rad1 = math.radians(a)
                rad2 = math.radians(a + 8)
                x1 = cx + (w / 2) * math.cos(rad1)
                y1 = cy + (h / 2) * math.sin(rad1)
                x2 = cx + (w / 2) * math.cos(rad2)
                y2 = cy + (h / 2) * math.sin(rad2)
                draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
        elif shape == "cylinder":
            top_y = cy - h // 2
            bot_y = cy + h // 2
            self._draw_dashed_line(draw, (cx - w // 2, top_y), (cx - w // 2, bot_y),
                                   color, width=2, dash_len=6, gap_len=4)
            self._draw_dashed_line(draw, (cx + w // 2, top_y), (cx + w // 2, bot_y),
                                   color, width=2, dash_len=6, gap_len=4)
            for a in range(180, 361, 15):
                rad1 = math.radians(a)
                rad2 = math.radians(a + 10)
                x1 = cx + (w / 2) * math.cos(rad1)
                y1 = top_y + (h // 6) * math.sin(rad1)
                x2 = cx + (w / 2) * math.cos(rad2)
                y2 = top_y + (h // 6) * math.sin(rad2)
                draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
        else:
            # rect / irregular 用虚线矩形近似
            x1, y1 = cx - w // 2, cy - h // 2
            x2, y2 = cx + w // 2, cy + h // 2
            self._draw_dashed_line(draw, (x1, y1), (x2, y1), color, width=2, dash_len=8, gap_len=5)
            self._draw_dashed_line(draw, (x2, y1), (x2, y2), color, width=2, dash_len=8, gap_len=5)
            self._draw_dashed_line(draw, (x2, y2), (x1, y2), color, width=2, dash_len=8, gap_len=5)
            self._draw_dashed_line(draw, (x1, y2), (x1, y1), color, width=2, dash_len=8, gap_len=5)

    def _draw_sketchy_line(self, draw, start, end, color, width=1, wobble=1.5, segments=8):
        """画手绘抖动线"""
        sx, sy = start
        ex, ey = end
        for i in range(segments):
            t0 = i / segments
            t1 = (i + 1) / segments
            j0 = random.uniform(-wobble, wobble) if i else 0
            k0 = random.uniform(-wobble, wobble) if i else 0
            j1 = random.uniform(-wobble, wobble) if i < segments - 1 else 0
            k1 = random.uniform(-wobble, wobble) if i < segments - 1 else 0
            x1 = sx + (ex - sx) * t0 + j0
            y1 = sy + (ey - sy) * t0 + k0
            x2 = sx + (ex - sx) * t1 + j1
            y2 = sy + (ey - sy) * t1 + k1
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

    def _draw_curved_line(self, draw, start, mid, end, color, width=2, wobble=1.5, steps=16):
        """画带弧度的曲线（二次贝塞尔近似）+ 手绘抖动"""
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

    def _draw_break_marks(self, draw, data: MotionSketchData):
        """画碎裂/断裂标记：轮廓边缘的缺口刻痕 + 内部裂纹"""
        if data.motion_type not in ("crumble", "stretch"):
            return
        cx, cy = data.product_position
        w, h = data.product_size
        for i in range(6):
            angle = 2 * math.pi * i / 6 + 0.4
            ex = cx + math.cos(angle) * (w / 2 + 4)
            ey = cy + math.sin(angle) * (h / 2 + 4)
            x1 = ex - math.cos(angle) * 7
            y1 = ey - math.sin(angle) * 7
            x2 = ex + math.cos(angle) * 7
            y2 = ey + math.sin(angle) * 7
            draw.line([(x1, y1), (x2, y2)], fill=self.particle_color, width=2)
        for _ in range(2):
            sx = cx + random.randint(-w // 4, w // 4)
            sy = cy + random.randint(-h // 4, h // 4)
            pts = [(sx, sy)]
            px, py = sx, sy
            for _ in range(3):
                px += random.randint(-28, 28)
                py += random.randint(-28, 28)
                pts.append((px, py))
            for i in range(len(pts) - 1):
                draw.line([pts[i], pts[i + 1]], fill=self.particle_color, width=2)

    def _draw_subject_marker(self, draw, data: MotionSketchData):
        """画主体标记：V 形指针 + SUBJECT 标签，明确谁是主角"""
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


# ========== 示例数据（模拟分镜） ==========

def build_ai_sketch_prompt(data: MotionSketchData) -> str:
    """生成 Agnes AI 模式的运动示意图提示词模板。

    注意：这个阶段只画主体轮廓示意，不给产品外观细节——
    让 AI 知道"谁是主角、往哪动、有什么粒子效果"即可。
    """
    shape_names = {
        "round": "round blob",
        "rect": "rectangular box",
        "cylinder": "cylinder",
        "irregular": "irregular shape",
    }
    motion_names = {
        "slide": "sliding",
        "crumble": "crumbling apart",
        "splash": "splashing",
        "stretch": "stretching",
        "drop": "dropping",
        "rotate": "rotating",
    }
    camera_names = {
        "zoom_in": "camera zooming in",
        "pan_left": "camera panning left",
        "orbit": "camera orbiting",
        "static": "static camera",
    }
    dx, dy = data.motion_direction
    dir_key = f"({int(dx)},{int(dy)})"
    direction_names = {
        "(-1,0)": "moving left",
        "(1,0)": "moving right",
        "(0,-1)": "moving up",
        "(0,1)": "moving down",
    }
    direction = direction_names.get(dir_key, "moving in a specified direction")
    shape = shape_names.get(data.product_shape, "simple shape")
    motion = motion_names.get(data.motion_type, data.motion_type)
    camera = camera_names.get(data.camera_motion, "static camera")
    particles = "、".join(data.particles) if data.particles else "none"
    return (
        "black and white rough line sketch, motion storyboard blueprint, "
        "a single simple {shape} as the subject, no product detail, no color, "
        "hand-drawn style arrows showing {direction} {motion}, "
        "particle marks ({particles}) bursting outward, {camera}, "
        "minimal line art, white background, schematic diagram style"
    ).format(shape=shape, direction=direction, motion=motion,
             particles=particles, camera=camera)


def get_demo_frames() -> list[MotionSketchData]:
    """生成 5 帧演示数据，模拟一个饼干产品分镜"""
    return [
        # 第1帧：全景展示，静止
        MotionSketchData(
            frame_num=1,
            product_shape="rect",
            product_size=(200, 140),
            product_position=(512, 288),
            motion_type="slide",
            motion_direction=(0, 0),
            motion_speed="slow",
            particles=[],
            camera_motion="zoom_in",
            description="全景展示：产品居中，缓慢放大",
        ),
        # 第2帧：特写，酥脆表面
        MotionSketchData(
            frame_num=2,
            product_shape="rect",
            product_size=(300, 200),
            product_position=(512, 288),
            motion_type="crumble",
            motion_direction=(0.3, -0.7),
            motion_speed="medium",
            particles=["crumbs"],
            camera_motion="zoom_in",
            description="微距特写：表面碎裂掉渣",
        ),
        # 第3帧：掰开动作
        MotionSketchData(
            frame_num=3,
            product_shape="irregular",
            product_size=(280, 180),
            product_position=(512, 288),
            motion_type="stretch",
            motion_direction=(1, 0),
            motion_speed="medium",
            particles=["crumbs"],
            camera_motion="static",
            description="掰开瞬间：展示截面层次",
        ),
        # 第4帧：水花/飞溅
        MotionSketchData(
            frame_num=4,
            product_shape="round",
            product_size=(180, 180),
            product_position=(512, 288),
            motion_type="splash",
            motion_direction=(0, -1),
            motion_speed="fast",
            particles=["splash", "crumbs"],
            camera_motion="zoom_in",
            description="高速飞溅：碎片四溅效果",
        ),
        # 第5帧：定格特写
        MotionSketchData(
            frame_num=5,
            product_shape="rect",
            product_size=(250, 170),
            product_position=(512, 288),
            motion_type="slide",
            motion_direction=(-0.3, 0),
            motion_speed="slow",
            particles=["dust"],
            camera_motion="orbit",
            description="定格收尾：缓慢环绕展示",
        ),
    ]


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    output_dir = "prototype_output"
    os.makedirs(output_dir, exist_ok=True)

    renderer = MotionSketchRenderer(width=1024, height=576)
    frames = get_demo_frames()

    # 生成单帧
    for frame in frames:
        img = renderer.render(frame)
        path = os.path.join(output_dir, f"motion_sketch_frame_{frame.frame_num}.png")
        img.save(path)
        print(f"✅ 已生成: {path}")

    # 打印 Agnes AI 模式提示词模板（只画主体轮廓，不给产品外观）
    print("\n=== Agnes AI 模式提示词模板（无产品外观） ===")
    for frame in frames:
        print(f"Frame {frame.frame_num}: {build_ai_sketch_prompt(frame)}")

    # 生成组合图（所有帧并排）
    total_width = 1024 * len(frames)
    combo = Image.new("RGB", (total_width, 576), (255, 255, 255))
    for i, frame in enumerate(frames):
        img = renderer.render(frame)
        combo.paste(img, (i * 1024, 0))
    combo_path = os.path.join(output_dir, "motion_sketch_combo.png")
    combo.save(combo_path)
    print(f"✅ 组合图已生成: {combo_path}")
    print(f"\n共生成 {len(frames) + 1} 张图，查看 {output_dir}/ 目录")


if __name__ == "__main__":
    main()
