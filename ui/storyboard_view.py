"""分镜预览视图

布局：左侧帧列表（垂直可滚动）+ 右侧提示词详情面板
点击缩略图弹出大图预览。
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QSizePolicy, QTextEdit,
    QListWidget, QListWidgetItem, QDialog, QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path


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
            # 获取屏幕可用尺寸，图片按比例缩放到 80% 屏幕
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

    def __init__(self, frame_data: dict, index: int):
        super().__init__()
        self.index = index
        self.frame_data = frame_data
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 左侧：帧序号
        num_label = QLabel(f"{self.frame_data.get('frame', self.index + 1)}")
        num_label.setFixedSize(36, 36)
        num_label.setAlignment(Qt.AlignCenter)
        num_label.setStyleSheet(
            "QLabel { background: #313244; border-radius: 18px; "
            "font-weight: bold; font-size: 16px; color: #cdd6f4; }"
        )
        layout.addWidget(num_label)

        # 中间：缩略图
        self.image_label = QLabel()
        self.image_label.setFixedSize(56, 56)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background: #11111b; border-radius: 4px; color: #585b70; font-size: 12px;"
        )
        self.image_label.setText("无图")

        img_path = self.frame_data.get("image_path")
        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setStyleSheet("background: transparent;")

        layout.addWidget(self.image_label)

        # 右侧：时长+描述
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        duration = self.frame_data.get("duration", 0)
        dur_label = QLabel(f"{duration:.1f}s")
        dur_label.setStyleSheet("color: #a6adc8; font-size: 13px;")
        info_layout.addWidget(dur_label)

        desc = self.frame_data.get("description", "")
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 13px; color: #a6adc8;")
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
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # ===== 左侧：帧列表 =====
        left_frame = QFrame()
        left_frame.setFixedWidth(260)
        left_frame.setStyleSheet("QFrame { background: #181825; border-radius: 6px; }")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        title = QLabel("分镜列表")
        title.setStyleSheet("font-size: 13px; font-weight: bold; padding: 2px; color: #cdd6f4;")
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
        self.frame_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #89b4fa;")
        right_layout.addWidget(self.frame_title)

        # 图片预览区（可点击放大）
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(256, 256)
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

        # 图片提示词
        self._add_prompt_section(scroll_content_layout, "图片提示词", "image_prompt")
        # 镜头运动
        self._add_prompt_section(scroll_content_layout, "镜头运动", "camera_motion")
        # 画面动态
        self._add_prompt_section(scroll_content_layout, "画面动态", "motion_hint")
        # 画面描述
        self._add_prompt_section(scroll_content_layout, "画面描述", "description")

        scroll_content_layout.addStretch()
        scroll.setWidget(scroll_content)
        right_layout.addWidget(scroll, stretch=1)

        main_layout.addWidget(right_frame, stretch=1)

    def _add_prompt_section(self, parent_layout, title, field_key):
        """添加一个提示词区域（标题+EN+CN）"""
        section = QFrame()
        section.setStyleSheet("""
            QFrame { background: #11111b; border-radius: 6px; border: 1px solid #313244; }
        """)
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(10, 8, 10, 8)
        section_layout.setSpacing(4)

        header = QLabel(title)
        header.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa;")
        section_layout.addWidget(header)

        # 英文
        en_label = QLabel("EN")
        en_label.setStyleSheet("font-size: 10px; color: #585b70; font-weight: bold;")
        section_layout.addWidget(en_label)

        en_text = QLabel()
        en_text.setWordWrap(True)
        en_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        en_text.setStyleSheet("font-size: 12px; color: #cdd6f4; background: transparent;")
        en_text.setText("—")
        section_layout.addWidget(en_text)

        # 中文
        cn_label = QLabel("CN")
        cn_label.setStyleSheet("font-size: 10px; color: #585b70; font-weight: bold;")
        section_layout.addWidget(cn_label)

        cn_text = QLabel()
        cn_text.setWordWrap(True)
        cn_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cn_text.setStyleSheet("font-size: 12px; color: #cdd6f4; background: transparent;")
        cn_text.setText("—")
        section_layout.addWidget(cn_text)

        parent_layout.addWidget(section)

        # 存引用以便更新
        if not hasattr(self, '_field_widgets'):
            self._field_widgets = {}
        self._field_widgets[field_key] = (en_text, cn_text)

    def set_frames(self, frames: list):
        """设置分镜数据"""
        self.list_widget.clear()
        self.list_items.clear()
        self.frames = frames

        if not frames:
            self.list_widget.addItem("（无分镜数据）")
            return

        for i, frame in enumerate(frames):
            item_widget = FrameListItem(frame, i)
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(240, 76))
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
            self.list_items.append(list_item)

        # 默认选中第一帧
        if frames:
            self.list_widget.setCurrentRow(0)

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

        # 标题
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
            # 更新列表项缩略图
            if index < len(self.list_items):
                item = self.list_items[index]
                widget = self.list_widget.itemWidget(item)
                if widget and hasattr(widget, "image_label"):
                    pix = QPixmap(image_path)
                    if not pix.isNull():
                        scaled = pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        widget.image_label.setPixmap(scaled)
                        widget.image_label.setStyleSheet("background: transparent;")
            # 如果当前选中的就是这一帧，更新预览
            if index == self.selected_index:
                pix = QPixmap(image_path)
                if not pix.isNull():
                    scaled = pix.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.preview_label.setPixmap(scaled)
                    self.preview_label.setStyleSheet("background: transparent; border-radius: 6px;")
