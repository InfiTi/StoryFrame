"""分镜预览视图

布局：纵向卡片流 — 每帧一行（序号 + 缩略图 + 所有提示词 EN/CN）
整体上下滚动浏览，无需点击切换。
点击缩略图弹出大图预览，点击卡片选中帧。
字体大小可通过 config["ui"]["font_size"] 配置。
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QDialog, QDoubleSpinBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from pathlib import Path
import json
import os


def _load_font_size() -> int:
    """从 config.json 读取字体大小，默认 15"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("ui", {}).get("font_size", 15)
    except Exception:
        return 15


class ImagePreviewDialog(QDialog):
    """图片放大预览对话框"""

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel()
        pix = QPixmap(image_path)
        if not pix.isNull():
            screen = self.screen()
            if screen:
                avail = screen.availableGeometry()
                max_w = int(avail.width() * 0.85)
                max_h = int(avail.height() * 0.85)
                if pix.width() > max_w or pix.height() > max_h:
                    pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pix)

        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background: #11111b;")
        layout.addWidget(label)

        self.setStyleSheet("QDialog { background: #11111b; }")


class FrameCard(QFrame):
    """单帧卡片 — 序号 + 缩略图 + 提示词(EN/CN) 全部展示"""

    clicked = Signal(int)       # 卡片点击
    image_clicked = Signal(str) # 图片点击（传路径）
    duration_changed = Signal(int, float)  # 帧时长修改（帧索引, 新时长）

    def __init__(self, frame_data: dict, index: int, font_size: int = 15):
        super().__init__()
        self.index = index
        self.frame_data = frame_data
        self.font_size = font_size
        self.selected = False
        self._init_ui()
        self._update_style()

    def _init_ui(self):
        fs = self.font_size
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 左侧：帧序号
        num_size = fs + 8
        self.num_label = QLabel(str(self.frame_data.get("frame", self.index + 1)))
        self.num_label.setFixedSize(num_size, num_size)
        self.num_label.setAlignment(Qt.AlignCenter)
        self.num_label.setStyleSheet(
            f"QLabel {{ background: #313244; border-radius: {num_size // 2}px; "
            f"font-weight: bold; font-size: {fs + 3}px; color: #cdd6f4; }}"
        )
        layout.addWidget(self.num_label, alignment=Qt.AlignTop)

        # 缩略图（可点击放大）— 宽度固定，高度跟随内容
        thumb_w = fs * 8  # 15→120, 18→144
        self.thumb_w = thumb_w
        self.image_label = QLabel()
        self.image_label.setFixedWidth(thumb_w)
        self.image_label.setMinimumHeight(thumb_w)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setCursor(Qt.PointingHandCursor)
        self.image_label.setStyleSheet(
            f"background: #11111b; border-radius: 6px; color: #585b70; font-size: {fs}px;"
        )
        self.image_label.setText("无图")

        img_path = self.frame_data.get("image_path")
        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path)
            if not pix.isNull():
                # 等比缩放，宽度对齐 thumb_w
                scaled = pix.scaledToWidth(thumb_w, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setFixedHeight(scaled.height())
                self.image_label.setStyleSheet("background: transparent; border-radius: 6px;")
                self.image_label.setToolTip("点击放大")
            else:
                self.image_label.setToolTip("无图片")
        else:
            self.image_label.setToolTip("无图片")

        self.image_label.mousePressEvent = self._on_image_click
        layout.addWidget(self.image_label, alignment=Qt.AlignTop)

        # 右侧：所有提示词
        content = QVBoxLayout()
        content.setSpacing(6)

        # 时长（可编辑）
        duration = self.frame_data.get("duration", 0)
        dur_row = QHBoxLayout()
        dur_row.setSpacing(4)
        dur_icon = QLabel("⏱")
        dur_icon.setStyleSheet(f"color: #585b70; font-size: {fs - 1}px; background: transparent;")
        dur_icon.setFixedWidth(fs)
        dur_row.addWidget(dur_icon)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.5, 30.0)
        self.duration_spin.setSingleStep(0.5)
        self.duration_spin.setDecimals(1)
        self.duration_spin.setSuffix("s")
        self.duration_spin.setValue(duration)
        self.duration_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.duration_spin.setFixedWidth(fs * 5)
        self.duration_spin.setStyleSheet(
            f"QDoubleSpinBox {{ color: #a6adc8; font-size: {fs - 1}px; "
            f"background: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 2px 6px; }}"
        )
        self.duration_spin.valueChanged.connect(self._on_duration_spin_changed)
        dur_row.addWidget(self.duration_spin)
        dur_row.addStretch()
        content.addLayout(dur_row)

        # 图片提示词 EN/CN
        self._add_field(content, "图片提示词",
                        self.frame_data.get("image_prompt", ""),
                        self.frame_data.get("image_prompt_cn", ""))

        # 镜头运动 EN/CN（短字段，同行）
        self._add_short_field(content, "镜头运动",
                              self.frame_data.get("camera_motion", ""),
                              self.frame_data.get("camera_motion_cn", ""))

        # 画面动态 EN/CN（短字段，同行）
        self._add_short_field(content, "画面动态",
                              self.frame_data.get("motion_hint", ""),
                              self.frame_data.get("motion_hint_cn", ""))

        # 画面描述
        desc = self.frame_data.get("description", "")
        if desc:
            desc_frame = QFrame()
            desc_frame.setStyleSheet("QFrame { background: #1e1e2e; border-radius: 4px; }")
            desc_layout = QVBoxLayout(desc_frame)
            desc_layout.setContentsMargins(8, 4, 8, 4)
            desc_layout.setSpacing(2)
            desc_title = QLabel("画面描述")
            desc_title.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; font-weight: bold; background: transparent;")
            desc_layout.addWidget(desc_title)
            desc_text = QLabel(desc)
            desc_text.setWordWrap(True)
            desc_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            desc_text.setStyleSheet(f"font-size: {fs}px; color: #a6adc8; background: transparent;")
            desc_layout.addWidget(desc_text)
            content.addWidget(desc_frame)

        content.addStretch()
        layout.addLayout(content, stretch=1)

    def _add_field(self, parent_layout, title, en_text, cn_text):
        """添加长字段区域（EN/CN 各占多行）"""
        fs = self.font_size
        section = QFrame()
        section.setStyleSheet("QFrame { background: #1e1e2e; border-radius: 4px; }")
        sl = QVBoxLayout(section)
        sl.setContentsMargins(8, 4, 8, 4)
        sl.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; font-weight: bold; background: transparent;")
        sl.addWidget(title_label)

        if en_text:
            en_label = QLabel(f"EN")
            en_label.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; font-weight: bold; background: transparent;")
            sl.addWidget(en_label)
            en_content = QLabel(en_text)
            en_content.setWordWrap(True)
            en_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
            en_content.setStyleSheet(f"font-size: {fs}px; color: #cdd6f4; background: transparent;")
            sl.addWidget(en_content)

        if cn_text:
            cn_label = QLabel(f"CN")
            cn_label.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; font-weight: bold; background: transparent;")
            sl.addWidget(cn_label)
            cn_content = QLabel(cn_text)
            cn_content.setWordWrap(True)
            cn_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
            cn_content.setStyleSheet(f"font-size: {fs}px; color: #a6adc8; background: transparent;")
            sl.addWidget(cn_content)

        if not en_text and not cn_text:
            empty = QLabel("—")
            empty.setStyleSheet(f"font-size: {fs}px; color: #585b70; background: transparent;")
            sl.addWidget(empty)

        parent_layout.addWidget(section)

    def _add_short_field(self, parent_layout, title, en_text, cn_text):
        """添加短字段（EN/CN 同行）"""
        fs = self.font_size
        section = QFrame()
        section.setStyleSheet("QFrame { background: #1e1e2e; border-radius: 4px; }")
        sl = QVBoxLayout(section)
        sl.setContentsMargins(8, 4, 8, 4)
        sl.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; font-weight: bold; background: transparent;")
        sl.addWidget(title_label)

        # EN 和 CN 同行
        line = QLabel()
        parts = []
        if en_text:
            parts.append(f'<span style="color:#585b70; font-size:{fs-3}px; font-weight:bold;">EN </span>'
                         f'<span style="color:#cdd6f4; font-size:{fs}px;">{en_text}</span>')
        if cn_text:
            parts.append(f'<span style="color:#585b70; font-size:{fs-3}px; font-weight:bold;">  CN </span>'
                         f'<span style="color:#a6adc8; font-size:{fs}px;">{cn_text}</span>')
        if parts:
            line.setText("&nbsp;&nbsp;".join(parts))
            line.setTextFormat(Qt.RichText)
            line.setWordWrap(True)
            line.setTextInteractionFlags(Qt.TextSelectableByMouse)
        else:
            line.setText("—")
            line.setStyleSheet(f"font-size: {fs}px; color: #585b70; background: transparent;")
        sl.addWidget(line)

        parent_layout.addWidget(section)

    def _update_style(self):
        if self.selected:
            self.setStyleSheet(
                "FrameCard { border: 2px solid #89b4fa; border-radius: 8px; background: #181825; }"
            )
        else:
            self.setStyleSheet(
                "FrameCard { border: 2px solid #313244; border-radius: 8px; background: #181825; }"
            )

    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()

    def update_image(self, image_path: str):
        """更新图片"""
        self.frame_data["image_path"] = image_path
        pix = QPixmap(image_path)
        if not pix.isNull():
            scaled = pix.scaledToWidth(self.thumb_w, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setFixedHeight(scaled.height())
            self.image_label.setStyleSheet("background: transparent; border-radius: 6px;")
            self.image_label.setToolTip("点击放大")

    def _on_duration_spin_changed(self, value: float):
        """帧时长被修改"""
        self.frame_data["duration"] = round(value, 1)
        self.duration_changed.emit(self.index, round(value, 1))

    def _on_image_click(self, event):
        """点击缩略图放大"""
        img_path = self.frame_data.get("image_path")
        if img_path and Path(img_path).exists():
            self.image_clicked.emit(img_path)

    def mousePressEvent(self, event):
        """点击卡片选中"""
        # 如果点的是图片区域，不触发选中（图片有自己的处理）
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        if self.image_label.geometry().contains(pos):
            return
        self.clicked.emit(self.index)
        super().mousePressEvent(event)


class StoryboardView(QWidget):
    """分镜预览视图 — 纵向卡片流，上下滚动浏览所有帧"""

    frame_selected = Signal(int)  # 选中帧变化
    frame_duration_changed = Signal(int, float)  # 帧时长修改（帧索引, 新时长）

    def __init__(self):
        super().__init__()
        self.frames = []
        self.cards = []
        self.selected_index = -1
        self.font_size = _load_font_size()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: #1e1e2e; }
            QScrollBar:vertical { background: #181825; width: 12px; border: none; }
            QScrollBar::handle:vertical { background: #45475a; border-radius: 5px; min-height: 40px; }
            QScrollBar::handle:vertical:hover { background: #585b70; }
            QScrollBar::add-line, QScrollBar::sub-line { border: none; background: none; height: 0; }
        """)

        self.container = QWidget()
        self.container.setStyleSheet("background: #1e1e2e;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(8)

        # 空状态
        self.empty_label = QLabel("点击「生成分镜」开始创建分镜脚本")
        self.empty_label.setStyleSheet(
            f"color: #585b70; font-size: {self.font_size + 2}px; padding: 60px;"
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.container_layout.addWidget(self.empty_label)

        self.container_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def set_frames(self, frames: list):
        """设置分镜数据"""
        # 清空旧卡片
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()

        # 移除空状态
        if self.container_layout.count() > 0:
            item = self.container_layout.takeAt(0)
            if item.widget() == self.empty_label:
                pass  # 已移除
            else:
                # 放回去
                self.container_layout.insertItem(0, item)

        # 清空容器布局
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w and w != self.empty_label:
                w.deleteLater()

        if not frames:
            self.container_layout.addWidget(self.empty_label)
            self.container_layout.addStretch()
            return

        self.frames = frames
        for i, frame in enumerate(frames):
            card = FrameCard(frame, i, font_size=self.font_size)
            card.clicked.connect(self._on_card_clicked)
            card.image_clicked.connect(self._on_image_clicked)
            card.duration_changed.connect(self._on_duration_changed)
            self.container_layout.addWidget(card)
            self.cards.append(card)

        self.container_layout.addStretch()

        # 默认选中第一帧
        if frames:
            self._on_card_clicked(0)

    def _on_card_clicked(self, index: int):
        """卡片点击选中"""
        self.selected_index = index
        for i, card in enumerate(self.cards):
            card.set_selected(i == index)
        self.frame_selected.emit(index)

    def _on_image_clicked(self, image_path: str):
        """图片点击放大"""
        if image_path and Path(image_path).exists():
            dlg = ImagePreviewDialog(image_path, self)
            dlg.exec()

    def _on_duration_changed(self, index: int, duration: float):
        """帧时长被修改"""
        if 0 <= index < len(self.frames):
            self.frames[index]["duration"] = duration
        self.frame_duration_changed.emit(index, duration)

    def reload_font_size(self):
        """重新加载字体大小并刷新视图"""
        self.font_size = _load_font_size()
        prev_index = self.selected_index
        # 重建卡片
        frames = self.frames
        # 清空
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w and w != self.empty_label:
                w.deleteLater()

        if not frames:
            self.container_layout.addWidget(self.empty_label)
            self.container_layout.addStretch()
            return

        self.frames = frames
        for i, frame in enumerate(frames):
            card = FrameCard(frame, i, font_size=self.font_size)
            card.clicked.connect(self._on_card_clicked)
            card.image_clicked.connect(self._on_image_clicked)
            card.duration_changed.connect(self._on_duration_changed)
            self.container_layout.addWidget(card)
            self.cards.append(card)

        self.container_layout.addStretch()

        if 0 <= prev_index < len(frames):
            self._on_card_clicked(prev_index)

    def update_frame_image(self, index: int, image_path: str):
        """更新某帧的图片"""
        if 0 <= index < len(self.cards):
            self.frames[index]["image_path"] = image_path
            self.cards[index].update_image(image_path)
