"""分镜预览视图

布局：左侧帧列表（垂直可滚动）+ 右侧提示词详情面板
点击缩略图弹出大图预览。
字体大小可通过 config["ui"]["font_size"] 配置。
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QSizePolicy, QTextEdit,
    QListWidget, QListWidgetItem, QDialog, QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QFont
from pathlib import Path
import json
import os


def _load_font_size() -> int:
    """从 config.json 读取字体大小，默认 13"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("ui", {}).get("font_size", 13)
    except Exception:
        return 13


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
                max_w = int(avail.width() * 0.8)
                max_h = int(avail.height() * 0.8)
                if pix.width() > max_w or pix.height() > max_h:
                    pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pix)

        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background: #11111b;")
        layout.addWidget(label)

        self.setStyleSheet("QDialog { background: #11111b; }")


class FrameListItem(QWidget):
    """帧列表项 - 显示序号+缩略图+描述"""

    def __init__(self, frame_data: dict, index: int, font_size: int = 13):
        super().__init__()
        self.index = index
        self.frame_data = frame_data
        self.font_size = font_size
        self._init_ui()

    def _init_ui(self):
        fs = self.font_size
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 左侧：帧序号
        num_label = QLabel(f"{self.frame_data.get('frame', self.index + 1)}")
        num_size = fs + 6  # 序号稍大
        num_label.setFixedSize(num_size + 8, num_size + 8)
        num_label.setAlignment(Qt.AlignCenter)
        num_label.setStyleSheet(
            f"QLabel {{ background: #313244; border-radius: {num_size // 2 + 4}px; "
            f"font-weight: bold; font-size: {num_size}px; color: #cdd6f4; }}"
        )
        layout.addWidget(num_label)

        # 中间：缩略图
        thumb_size = fs + 43  # 13→56, 15→58, 18→61
        self.image_label = QLabel()
        self.image_label.setFixedSize(thumb_size, thumb_size)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            f"background: #11111b; border-radius: 4px; color: #585b70; font-size: {fs}px;"
        )
        self.image_label.setText("无图")

        img_path = self.frame_data.get("image_path")
        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(thumb_size, thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setStyleSheet("background: transparent;")

        layout.addWidget(self.image_label)

        # 右侧：时长+描述
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        duration = self.frame_data.get("duration", 0)
        dur_label = QLabel(f"{duration:.1f}s")
        dur_label.setStyleSheet(f"color: #a6adc8; font-size: {fs}px;")
        info_layout.addWidget(dur_label)

        desc = self.frame_data.get("description", "")
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"font-size: {fs}px; color: #a6adc8;")
        desc_label.setMaximumWidth(180)
        info_layout.addWidget(desc_label)

        layout.addLayout(info_layout, stretch=1)


class StoryboardView(QWidget):
    """分镜预览视图 - 左侧帧列表 + 右侧详情"""

    frame_selected = Signal(int)  # 选中帧变化
    image_clicked = Signal(str)   # 点击图片（传路径）

    def __init__(self):
        super().__init__()
        self.frames = []
        self.list_items = []
        self.selected_index = -1
        self.font_size = _load_font_size()
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # ===== 左侧：帧列表 =====
        left_frame = QFrame()
        left_frame.setFixedWidth(280)
        left_frame.setStyleSheet("QFrame { background: #181825; border-radius: 6px; }")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        title = QLabel("分镜列表")
        title.setStyleSheet(f"font-size: {self.font_size + 2}px; font-weight: bold; padding: 2px; color: #cdd6f4;")
        left_layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #11111b;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #313244;
                border: 1px solid #89b4fa;
            }
            QListWidget::item:hover {
                background: #1e1e2e;
            }
        """)
        self.list_widget.setSpacing(4)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        left_layout.addWidget(self.list_widget)

        main_layout.addWidget(left_frame)

        # ===== 右侧：详情区域 =====
        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background: #181825; border-radius: 6px; }")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        # 帧标题
        self.frame_title = QLabel("选择一帧查看详情")
        self.frame_title.setStyleSheet(f"font-size: {self.font_size + 4}px; font-weight: bold; color: #89b4fa;")
        right_layout.addWidget(self.frame_title)

        # 图片预览区（可点击放大）
        preview_size = 256
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(preview_size, preview_size)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background: #11111b; border-radius: 6px; color: #585b70; font-size: 12px;"
        )
        self.preview_label.setText("暂无图片")
        self.preview_label.setCursor(Qt.PointingHandCursor)
        self.preview_label.mousePressEvent = self._on_preview_click
        right_layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)

        # 滚动区域包裹提示词
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #181825; width: 10px; border: none; }
            QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #585b70; }
            QScrollBar::add-line, QScrollBar::sub-line { border: none; background: none; }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        scroll_content_layout.setSpacing(10)

        # 提示词区域
        self._field_widgets = {}
        self._add_prompt_section(scroll_content_layout, "图片提示词", "image_prompt")
        self._add_prompt_section(scroll_content_layout, "镜头运动", "camera_motion")
        self._add_prompt_section(scroll_content_layout, "画面动态", "motion_hint")
        self._add_prompt_section(scroll_content_layout, "画面描述", "description")

        scroll_content_layout.addStretch()
        scroll.setWidget(scroll_content)
        right_layout.addWidget(scroll, stretch=1)

        main_layout.addWidget(right_frame, stretch=1)

    def _add_prompt_section(self, parent_layout, title, field_key):
        """添加一个提示词区域（标题+EN+CN）"""
        fs = self.font_size
        section = QFrame()
        section.setStyleSheet("""
            QFrame { background: #11111b; border-radius: 6px; border: 1px solid #313244; }
        """)
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(10, 8, 10, 8)
        section_layout.setSpacing(4)

        header = QLabel(title)
        header.setStyleSheet(f"font-weight: bold; font-size: {fs + 1}px; color: #89b4fa;")
        section_layout.addWidget(header)

        # 英文
        en_label = QLabel("EN")
        en_label.setStyleSheet(f"font-size: {fs - 2}px; color: #585b70; font-weight: bold;")
        section_layout.addWidget(en_label)

        en_text = QLabel()
        en_text.setWordWrap(True)
        en_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        en_text.setStyleSheet(f"font-size: {fs}px; color: #cdd6f4; background: transparent;")
        en_text.setText("—")
        section_layout.addWidget(en_text)

        # 中文
        cn_label = QLabel("CN")
        cn_label.setStyleSheet(f"font-size: {fs - 2}px; color: #585b70; font-weight: bold;")
        section_layout.addWidget(cn_label)

        cn_text = QLabel()
        cn_text.setWordWrap(True)
        cn_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cn_text.setStyleSheet(f"font-size: {fs}px; color: #cdd6f4; background: transparent;")
        cn_text.setText("—")
        section_layout.addWidget(cn_text)

        parent_layout.addWidget(section)
        self._field_widgets[field_key] = (en_text, cn_text)

    def set_frames(self, frames: list):
        """设置分镜数据"""
        self.list_widget.clear()
        self.list_items.clear()
        self.frames = frames

        if not frames:
            self.list_widget.addItem("（无分镜数据）")
            return

        item_height = self.font_size + 63  # 13→76, 16→79, 18→81
        for i, frame in enumerate(frames):
            item_widget = FrameListItem(frame, i, font_size=self.font_size)
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(260, item_height))
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
            self.list_items.append(list_item)

        if frames:
            self.list_widget.setCurrentRow(0)

    def reload_font_size(self):
        """重新加载字体大小并刷新视图"""
        self.font_size = _load_font_size()
        # 保存当前选中
        prev_index = self.selected_index
        # 重建整个 UI
        # 清除旧布局
        old_layout = self.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    sub = item.layout()
                    if sub:
                        self._clear_layout(sub)
            old_layout.invalidate()
        self._field_widgets = {}
        self.list_items = []
        self._init_ui()
        # 恢复数据
        if self.frames:
            self.set_frames(self.frames)
            if 0 <= prev_index < len(self.frames):
                self.list_widget.setCurrentRow(prev_index)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub = item.layout()
                if sub:
                    self._clear_layout(sub)

    def _on_row_changed(self, row: int):
        """列表选中行变化"""
        if row < 0 or row >= len(self.frames):
            return
        self.selected_index = row
        self.frame_selected.emit(row)
        self._update_detail(row)

    def _update_detail(self, index: int):
        """更新右侧详情"""
        if index < 0 or index >= len(self.frames):
            return
        frame = self.frames[index]

        frame_num = frame.get("frame", index + 1)
        duration = frame.get("duration", 0)
        self.frame_title.setText(f"第 {frame_num} 帧  ·  {duration:.1f}s")

        # 图片预览
        img_path = frame.get("image_path")
        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
                self.preview_label.setStyleSheet("background: transparent; border-radius: 6px;")
            else:
                self._set_no_image()
        else:
            self._set_no_image()

        # 提示词
        field_pairs = [
            ("image_prompt", "image_prompt_cn"),
            ("camera_motion", "camera_motion_cn"),
            ("motion_hint", "motion_hint_cn"),
        ]
        for en_key, cn_key in field_pairs:
            en_text, cn_text = self._field_widgets.get(en_key, (None, None))
            if en_text:
                en_text.setText(frame.get(en_key, "—") or "—")
            if cn_text:
                cn_text.setText(frame.get(cn_key, "—") or "—")

        # description 只有中文
        en_text, cn_text = self._field_widgets.get("description", (None, None))
        if en_text:
            en_text.setText("—")
        if cn_text:
            cn_text.setText(frame.get("description", "—") or "—")

    def _set_no_image(self):
        self.preview_label.setText("暂无图片")
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setStyleSheet(
            "background: #11111b; border-radius: 6px; color: #585b70; font-size: 12px;"
        )

    def _on_preview_click(self, event):
        """点击预览图，放大显示"""
        if self.selected_index < 0 or self.selected_index >= len(self.frames):
            return
        img_path = self.frames[self.selected_index].get("image_path")
        if img_path and Path(img_path).exists():
            dlg = ImagePreviewDialog(img_path, self)
            dlg.exec()

    def update_frame_image(self, index: int, image_path: str):
        """更新某帧的图片"""
        if 0 <= index < len(self.frames):
            self.frames[index]["image_path"] = image_path
            if index < len(self.list_items):
                item = self.list_items[index]
                widget = self.list_widget.itemWidget(item)
                if widget and hasattr(widget, "image_label"):
                    pix = QPixmap(image_path)
                    if not pix.isNull():
                        thumb_size = self.font_size + 43
                        scaled = pix.scaled(thumb_size, thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        widget.image_label.setPixmap(scaled)
                        widget.image_label.setStyleSheet("background: transparent;")
            if index == self.selected_index:
                pix = QPixmap(image_path)
                if not pix.isNull():
                    scaled = pix.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.preview_label.setPixmap(scaled)
                    self.preview_label.setStyleSheet("background: transparent; border-radius: 6px;")
