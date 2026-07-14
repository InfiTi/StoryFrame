"""分镜预览视图"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QSizePolicy, QTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
from pathlib import Path


class FrameCard(QFrame):
    """单帧分镜卡片"""

    clicked = Signal(int)  # 点击时发送帧序号

    def __init__(self, frame_data: dict, index: int):
        super().__init__()
        self.index = index
        self.frame_data = frame_data
        self.selected = False
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)
        self.setFixedWidth(180)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 帧序号
        header = QLabel(f"第 {self.frame_data.get('frame', self.index + 1)} 帧")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # 时长
        duration = self.frame_data.get("duration", 0)
        dur_label = QLabel(f"{duration:.1f}s")
        dur_label.setAlignment(Qt.AlignCenter)
        dur_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(dur_label)

        # 图片预览
        self.image_label = QLabel()
        self.image_label.setFixedSize(160, 160)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: #f0f0f0; border-radius: 4px;")
        self.image_label.setText("暂无图片")
        self.image_label.setStyleSheet("background: #f0f0f0; border-radius: 4px; color: #999; font-size: 12px;")

        img_path = self.frame_data.get("image_path")
        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setStyleSheet("background: transparent;")

        layout.addWidget(self.image_label)

        # 中文描述
        desc = self.frame_data.get("description", "")
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 11px; color: #333;")
        desc_label.setMaximumHeight(50)
        layout.addWidget(desc_label)

    def _update_style(self):
        if self.selected:
            self.setStyleSheet("FrameCard { border: 2px solid #4a90d9; border-radius: 6px; background: #f5faff; }")
        else:
            self.setStyleSheet("FrameCard { border: 2px solid #ddd; border-radius: 6px; background: white; }")

    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()

    def update_image(self, image_path: str):
        """更新图片"""
        self.frame_data["image_path"] = image_path
        pix = QPixmap(image_path)
        if not pix.isNull():
            scaled = pix.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)


class StoryboardView(QWidget):
    """分镜预览视图 - 水平时间轴"""

    frame_selected = Signal(int)  # 选中帧变化

    def __init__(self):
        super().__init__()
        self.frames = []
        self.cards = []
        self.selected_index = -1
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title = QLabel("分镜时间轴")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.timeline_widget = QWidget()
        self.timeline_layout = QHBoxLayout(self.timeline_widget)
        self.timeline_layout.setContentsMargins(10, 10, 10, 10)
        self.timeline_layout.setSpacing(12)
        self.timeline_layout.setAlignment(Qt.AlignLeft)

        # 空状态提示
        self.empty_label = QLabel("点击「生成分镜」开始创建分镜脚本")
        self.empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.timeline_layout.addWidget(self.empty_label)

        scroll.setWidget(self.timeline_widget)
        layout.addWidget(scroll, stretch=1)

    def set_frames(self, frames: list):
        """设置分镜数据"""
        # 清空旧卡片
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        self.timeline_layout.takeAt(0)  # 移除空状态

        if not frames:
            self.timeline_layout.addWidget(self.empty_label)
            return

        self.frames = frames
        for i, frame in enumerate(frames):
            card = FrameCard(frame, i)
            card.clicked.connect(self._on_card_clicked)
            self.timeline_layout.addWidget(card)
            self.cards.append(card)

        # 添加弹簧
        self.timeline_layout.addStretch()

    def _on_card_clicked(self, index: int):
        """卡片点击"""
        self.selected_index = index
        for i, card in enumerate(self.cards):
            card.set_selected(i == index)
        self.frame_selected.emit(index)

    def update_frame_image(self, index: int, image_path: str):
        """更新某帧的图片"""
        if 0 <= index < len(self.cards):
            self.cards[index].update_image(image_path)
