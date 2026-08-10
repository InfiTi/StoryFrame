"""分镜预览视图

布局：纵向卡片流 — 每帧一行（序号 + 缩略图 + 所有提示词 EN/CN）
整体上下滚动浏览，无需点击切换。
点击缩略图弹出大图预览，点击卡片选中帧。
字体大小可通过 config["ui"]["font_size"] 配置。
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QDialog, QDoubleSpinBox, QPushButton, QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QEvent, QRect, QPoint
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
    """图片放大预览对话框

    点击图片本身不关闭；点击图片外区域（dialog 空白/提示文字）关闭。
    dialog 尺寸设为屏幕 90%，图片居中，周围有可见空白区域供点击关闭。
    """

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        screen = self.screen()
        avail = screen.availableGeometry() if screen else None

        # dialog 尺寸设为屏幕 90%，让图片周围有可见空白区域
        if avail:
            self.setFixedSize(int(avail.width() * 0.9), int(avail.height() * 0.9))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel()
        pix = QPixmap(image_path)
        if not pix.isNull():
            if avail:
                max_w = int(avail.width() * 0.85)
                max_h = int(avail.height() * 0.85)
                if pix.width() > max_w or pix.height() > max_h:
                    pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pix)

        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background: transparent;")
        layout.addWidget(label, stretch=1)

        hint = QLabel("点击图片外区域关闭")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #585b70; font-size: 11px; padding: 4px; background: #11111b;")
        layout.addWidget(hint)

        self.setStyleSheet("QDialog { background: #11111b; }")
        self._image_label = label
        # 点击图片外区域（dialog 空白/label 空白/提示文字）关闭；点击图片像素内不关闭
        self.installEventFilter(self)
        label.installEventFilter(self)
        hint.installEventFilter(self)

    def eventFilter(self, obj, event):
        """点击图片外区域关闭，点击图片像素内不关闭"""
        if event.type() == QEvent.MouseButtonPress:
            if obj is self._image_label:
                # 检查点击是否在 pixmap 实际像素范围内
                pix = self._image_label.pixmap()
                if pix and not pix.isNull():
                    lw = self._image_label.width()
                    lh = self._image_label.height()
                    pw = pix.width()
                    ph = pix.height()
                    # pixmap 居中显示，计算实际 rect
                    x = (lw - pw) // 2
                    y = (lh - ph) // 2
                    pix_rect = QRect(x, y, pw, ph)
                    pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                    if pix_rect.contains(pos):
                        return True  # 点在图片像素上，不关闭
                # 点在 label 空白背景（pixmap 外）：关闭
                self.close()
                return True
            # 点击 dialog 空白或提示文字：关闭
            self.close()
            return True
        return super().eventFilter(obj, event)


class FrameCard(QFrame):
    """单帧卡片 — 序号 + 缩略图 + 提示词(EN/CN) 全部展示"""

    clicked = Signal(int)       # 卡片点击
    image_clicked = Signal(str) # 图片点击（传路径）
    duration_changed = Signal(int, float)  # 帧时长修改（帧索引, 新时长）
    regenerate_clicked = Signal(int)  # 重新生成此帧（帧索引）
    sketch_clicked = Signal(int, str)  # 生成/更新运动示意图（帧索引, 模式: ""/ai/hybrid）

    def __init__(self, frame_data: dict, index: int, font_size: int = 15):
        super().__init__()
        self.index = index
        self.frame_data = frame_data
        self.font_size = font_size
        self.selected = False
        self._init_ui()
        self.update_sketch(self.frame_data.get("motion_sketch_path", ""))
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

        # 缩略图列：产品图 + 运动示意图
        thumb_col = QVBoxLayout()
        thumb_col.setSpacing(6)
        thumb_col.addWidget(self.image_label, alignment=Qt.AlignTop)

        # 运动示意图缩略图（黑白线稿+箭头，喂给视频模型）
        self.sketch_label = QLabel()
        self.sketch_label.setFixedWidth(thumb_w)
        self.sketch_label.setMinimumHeight(thumb_w // 2)
        self.sketch_label.setAlignment(Qt.AlignCenter)
        self.sketch_label.setCursor(Qt.PointingHandCursor)
        self.sketch_label.setStyleSheet(
            f"background: #11111b; border-radius: 6px; color: #585b70; font-size: {fs}px;"
        )
        self.sketch_label.setText("✏️")
        self.sketch_label.mousePressEvent = self._on_sketch_click
        thumb_col.addWidget(self.sketch_label, alignment=Qt.AlignTop)

        layout.addLayout(thumb_col)

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

        # H3 字段：shot_label + cut_timestamp（标准模式为空，不显示）
        shot_label = self.frame_data.get("shot_label", "")
        cut_ts = self.frame_data.get("cut_timestamp", "")
        if shot_label or cut_ts:
            h3_tag = shot_label
            if cut_ts:
                h3_tag = (shot_label + "  " + cut_ts).strip() if shot_label else cut_ts
            self.h3_tag_label = QLabel(h3_tag)
            self.h3_tag_label.setStyleSheet(
                f"color: #bb9af7; font-size: {fs - 2}px; font-weight: bold; "
                f"background: #1e1e2e; border-radius: 4px; padding: 2px 8px;"
            )
            self.h3_tag_label.setToolTip("H3 分镜标签 + 切点时间戳")
            dur_row.addWidget(self.h3_tag_label)

        dur_row.addStretch()

        # 重新生成按钮
        self.regen_btn = QPushButton("🔄")
        self.regen_btn.setFixedSize(fs + 6, fs + 6)
        self.regen_btn.setToolTip("重新生成此帧提示词")
        self.regen_btn.setCursor(Qt.PointingHandCursor)
        self.regen_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; font-size: {fs}px; "
            f"padding: 0px; }}"
            f"QPushButton:hover {{ background: #313244; border-radius: 4px; }}"
        )
        self.regen_btn.clicked.connect(lambda: self.regenerate_clicked.emit(self.index))
        dur_row.addWidget(self.regen_btn)

        # 运动示意图按钮：✏️按设置 / 🎨AI 生成 / 🧬混合精修
        self.sketch_btns = {}
        for emoji, mode, tip in (
            ("✏️", "", "运动示意图（按设置中的生成方式）"),
            ("🎨", "ai", "AI 生成草稿图（调用生图模型接口）"),
            ("🧬", "hybrid", "混合精修草稿图（本地底稿 + 生图模型精修）"),
        ):
            btn = QPushButton(emoji)
            btn.setFixedSize(fs + 6, fs + 6)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ border: none; background: transparent; font-size: {fs}px; "
                f"padding: 0px; }}"
                f"QPushButton:hover {{ background: #313244; border-radius: 4px; }}"
            )
            btn.clicked.connect(lambda checked=False, m=mode: self.sketch_clicked.emit(self.index, m))
            dur_row.addWidget(btn)
            self.sketch_btns[mode] = btn

        # 复制草稿图 URL 按钮
        self.copy_sketch_url_btn = QPushButton("📋")
        self.copy_sketch_url_btn.setFixedSize(fs + 6, fs + 6)
        self.copy_sketch_url_btn.setToolTip("复制草稿图公网URL（粘贴给外部AI使用）")
        self.copy_sketch_url_btn.setCursor(Qt.PointingHandCursor)
        self.copy_sketch_url_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; font-size: {fs}px; "
            f"padding: 0px; }}"
            f"QPushButton:hover {{ background: #313244; border-radius: 4px; }}"
        )
        self.copy_sketch_url_btn.clicked.connect(self._copy_sketch_url)
        dur_row.addWidget(self.copy_sketch_url_btn)

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

        # H3 多模态综合描述（空则不显示）
        imd_en = self.frame_data.get("integrated_multimodal_description", "")
        imd_cn = self.frame_data.get("integrated_multimodal_description_cn", "")
        if imd_en or imd_cn:
            self._add_field(content, "多模态描述", imd_en, imd_cn)

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

        # H3 全片音频字段（只在最后一帧的 frame_data 中存在，空则不显示）
        soundscape = self.frame_data.get("overall_soundscape", "")
        music = self.frame_data.get("non_diegetic_music", "")
        if soundscape or music:
            audio_frame = QFrame()
            audio_frame.setStyleSheet(
                "QFrame { background: #1a1b2e; border: 1px solid #bb9af7; border-radius: 4px; }"
            )
            audio_layout = QVBoxLayout(audio_frame)
            audio_layout.setContentsMargins(8, 4, 8, 4)
            audio_layout.setSpacing(2)
            audio_title = QLabel("全片音频（H3）")
            audio_title.setStyleSheet(
                f"font-size: {fs - 3}px; color: #bb9af7; font-weight: bold; background: transparent;"
            )
            audio_layout.addWidget(audio_title)
            if soundscape:
                sc_label = QLabel("环境音")
                sc_label.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; font-weight: bold; background: transparent;")
                audio_layout.addWidget(sc_label)
                sc_text = QLabel(soundscape)
                sc_text.setWordWrap(True)
                sc_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
                sc_text.setStyleSheet(f"font-size: {fs}px; color: #cdd6f4; background: transparent;")
                audio_layout.addWidget(sc_text)
            if music:
                mu_label = QLabel("背景音乐")
                mu_label.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; font-weight: bold; background: transparent;")
                audio_layout.addWidget(mu_label)
                mu_text = QLabel(music)
                mu_text.setWordWrap(True)
                mu_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
                mu_text.setStyleSheet(f"font-size: {fs}px; color: #a6adc8; background: transparent;")
                audio_layout.addWidget(mu_text)
            content.addWidget(audio_frame)

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

    def update_sketch(self, image_path: str):
        """更新运动示意图缩略图"""
        self.frame_data["motion_sketch_path"] = image_path
        if image_path and Path(image_path).exists():
            pix = QPixmap(image_path)
            if not pix.isNull():
                scaled = pix.scaledToWidth(self.thumb_w, Qt.SmoothTransformation)
                self.sketch_label.setPixmap(scaled)
                self.sketch_label.setFixedHeight(scaled.height())
                self.sketch_label.setStyleSheet("background: transparent; border-radius: 6px;")
                self.sketch_label.setToolTip("运动示意图（点击放大）")
                return
        self.sketch_label.setPixmap(QPixmap())
        self.sketch_label.setText("✏️")
        self.sketch_label.setFixedHeight(self.thumb_w // 2)
        self.sketch_label.setStyleSheet(
            f"background: #11111b; border-radius: 6px; color: #585b70; "
            f"font-size: {self.font_size}px;"
        )
        self.sketch_label.setToolTip("生成/更新运动示意图")

    def _copy_sketch_url(self):
        """复制草稿图公网URL到剪贴板"""
        from PySide6.QtWidgets import QApplication
        url = self.frame_data.get("motion_sketch_url", "")
        if not url:
            # 没有公网URL，提示
            from PySide6.QtWidgets import QToolTip
            QToolTip.showText(self.copy_sketch_url_btn.mapToGlobal(QPoint(0, -30)),
                              "该帧没有草稿图公网URL（可能用程序化模式生成）")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(url)
        from PySide6.QtWidgets import QToolTip
        QToolTip.showText(self.copy_sketch_url_btn.mapToGlobal(QPoint(0, -30)),
                          "已复制草稿图URL到剪贴板")

    def _on_duration_spin_changed(self, value: float):
        """帧时长被修改"""
        self.frame_data["duration"] = round(value, 1)
        self.duration_changed.emit(self.index, round(value, 1))

    def _on_image_click(self, event):
        """点击缩略图放大"""
        img_path = self.frame_data.get("image_path")
        if img_path and Path(img_path).exists():
            self.image_clicked.emit(img_path)

    def _on_sketch_click(self, event):
        """点击运动示意图放大"""
        path = self.frame_data.get("motion_sketch_path", "")
        if path and Path(path).exists():
            self.image_clicked.emit(path)

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
    frame_regenerate = Signal(int)  # 重新生成帧（帧索引）
    sketch_requested = Signal(int, str)  # 生成运动示意图（帧索引, 模式: ""/ai/hybrid）

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
            card.regenerate_clicked.connect(self.frame_regenerate)
            card.sketch_clicked.connect(self.sketch_requested)
            self.container_layout.addWidget(card)
            self.cards.append(card)

        self.container_layout.addStretch()

        # 默认选中第一帧
        if frames:
            self._on_card_clicked(0)

    def add_frame(self, frame: dict, index: int = -1):
        """追加单帧到视图末尾（或指定位置插入），用于逐帧实时显示"""
        # 移除空状态
        if self.empty_label.parent() is not None:
            self.container_layout.removeWidget(self.empty_label)
        # 移除末尾的 stretch
        stretch_item = None
        if self.container_layout.count() > 0:
            last_item = self.container_layout.takeAt(self.container_layout.count() - 1)
            if last_item.spacerItem():
                stretch_item = last_item

        if index < 0 or index >= len(self.frames):
            # 末尾追加
            self.frames.append(frame)
            card = FrameCard(frame, len(self.frames) - 1, font_size=self.font_size)
            card.clicked.connect(self._on_card_clicked)
            card.image_clicked.connect(self._on_image_clicked)
            card.duration_changed.connect(self._on_duration_changed)
            card.regenerate_clicked.connect(self.frame_regenerate)
            card.sketch_clicked.connect(self.sketch_requested)
            self.container_layout.addWidget(card)
            self.cards.append(card)
        else:
            # 指定位置插入
            self.frames.insert(index, frame)
            card = FrameCard(frame, index, font_size=self.font_size)
            card.clicked.connect(self._on_card_clicked)
            card.image_clicked.connect(self._on_image_clicked)
            card.duration_changed.connect(self._on_duration_changed)
            card.regenerate_clicked.connect(self.frame_regenerate)
            card.sketch_clicked.connect(self.sketch_requested)
            self.container_layout.insertWidget(index, card)
            self.cards.insert(index, card)
            # 后续卡片索引 +1
            for i in range(index + 1, len(self.cards)):
                self.cards[i].index = i

        # 还原 stretch
        if stretch_item:
            self.container_layout.addItem(stretch_item)
        else:
            self.container_layout.addStretch()

        # 滚动到新帧
        self._scroll_to_card(len(self.cards) - 1)

    def _scroll_to_card(self, index: int):
        """滚动到指定卡片"""
        if 0 <= index < len(self.cards):
            self.scroll.ensureWidgetVisible(self.cards[index])

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
            card.regenerate_clicked.connect(self.frame_regenerate)
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

    def update_frame_sketch(self, index: int, image_path: str):
        """更新某帧的运动示意图"""
        if 0 <= index < len(self.cards):
            self.frames[index]["motion_sketch_path"] = image_path
            self.cards[index].update_sketch(image_path)

    def set_sketch_buttons_enabled(self, enabled: bool):
        """启用/禁用所有卡片上的运动示意图按钮（生成中防重复点击）"""
        for card in self.cards:
            for btn in card.sketch_btns.values():
                btn.setEnabled(enabled)

    def update_frame_data(self, index: int, frame_data: dict):
        """更新某帧的完整数据（重新生成后调用），重建该卡片"""
        if not (0 <= index < len(self.frames)):
            return
        self.frames[index] = frame_data
        # 保留选中状态
        was_selected = (self.selected_index == index)
        # 重建该卡片
        old_card = self.cards[index]
        # 先从布局中移除旧卡片，再 deleteLater
        layout_index = self.container_layout.indexOf(old_card)
        self.container_layout.removeWidget(old_card)
        old_card.setParent(None)
        old_card.deleteLater()
        # 创建新卡片
        new_card = FrameCard(frame_data, index, font_size=self.font_size)
        new_card.clicked.connect(self._on_card_clicked)
        new_card.image_clicked.connect(self._on_image_clicked)
        new_card.duration_changed.connect(self._on_duration_changed)
        new_card.regenerate_clicked.connect(self.frame_regenerate)
        # 插入到原来位置
        self.container_layout.insertWidget(layout_index, new_card)
        self.cards[index] = new_card
        if was_selected:
            new_card.set_selected(True)


class ReferenceBar(QFrame):
    """参考图栏 — 拖拽导入多张图片作为图生图输入"""

    references_changed = Signal(list)

    SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.webp')

    def __init__(self, font_size: int = 15, parent=None):
        super().__init__(parent)
        self.font_size = font_size
        self._references = []
        self.setAcceptDrops(True)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        fs = self.font_size
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 标题行
        header = QHBoxLayout()
        title = QLabel("📎 参考图（图生图输入）")
        title.setStyleSheet(f"font-size: {fs - 2}px; color: #bb9af7; font-weight: bold; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        self._count_label = QLabel("0 张")
        self._count_label.setStyleSheet(f"font-size: {fs - 3}px; color: #585b70; background: transparent;")
        header.addWidget(self._count_label)
        clear_btn = QPushButton("清空")
        clear_btn.setFixedHeight(20)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"QPushButton {{ color: #a6adc8; font-size: {fs - 3}px; background: #313244; border: none; border-radius: 4px; padding: 2px 8px; }}"
            f"QPushButton:hover {{ background: #45475a; }}"
        )
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        # 缩略图滚动区
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(96)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._thumbs_widget = QWidget()
        self._thumbs_layout = QHBoxLayout(self._thumbs_widget)
        self._thumbs_layout.setContentsMargins(0, 0, 0, 0)
        self._thumbs_layout.setSpacing(6)
        self._thumbs_layout.addStretch()
        self._scroll.setWidget(self._thumbs_widget)
        layout.addWidget(self._scroll)

        # 拖拽提示（空时显示）
        self._hint = QLabel("拖拽图片到此处，或点击选择")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setCursor(Qt.PointingHandCursor)
        self._hint.setStyleSheet(
            f"color: #585b70; font-size: {fs - 2}px; border: 1px dashed #45475a; border-radius: 4px; padding: 10px;"
        )
        self._hint.mousePressEvent = self._on_hint_click
        layout.addWidget(self._hint)

        self._update_visibility()

    def _apply_style(self):
        self.setStyleSheet("QFrame { background: #1a1b2e; border: 1px solid #313244; border-radius: 6px; }")

    def _update_visibility(self):
        has = bool(self._references)
        self._hint.setVisible(not has)
        self._scroll.setVisible(has)
        self._count_label.setText(f"{len(self._references)} 张")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p and p.lower().endswith(self.SUPPORTED_EXTS):
                paths.append(p)
        if paths:
            self._references.extend(paths)
            self._update_thumbs()
            self._update_visibility()
            self.references_changed.emit(self._references)
            event.acceptProposedAction()

    def _on_hint_click(self, event):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择参考图", "", "图片文件 (*.jpg *.jpeg *.png *.webp)"
        )
        if paths:
            self._references.extend(paths)
            self._update_thumbs()
            self._update_visibility()
            self.references_changed.emit(self._references)

    def _update_thumbs(self):
        # 清空现有（保留末尾 stretch）
        while self._thumbs_layout.count() > 1:
            item = self._thumbs_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for i, path in enumerate(self._references):
            thumb = self._make_thumb(path, i)
            self._thumbs_layout.insertWidget(i, thumb)

    def _make_thumb(self, path, index):
        fs = self.font_size
        container = QFrame()
        container.setFixedSize(76, 88)
        container.setCursor(Qt.PointingHandCursor)
        container.setToolTip(f"{Path(path).name}\n点击删除")
        container.setStyleSheet("QFrame { background: #11111b; border-radius: 4px; } QFrame:hover { border: 1px solid #f38ba8; }")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(2, 2, 2, 2)
        cl.setSpacing(2)
        img = QLabel()
        img.setFixedSize(72, 68)
        img.setAlignment(Qt.AlignCenter)
        pix = QPixmap(path)
        if not pix.isNull():
            img.setPixmap(pix.scaled(72, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        img.setStyleSheet("background: transparent;")
        cl.addWidget(img)
        name = QLabel(Path(path).name[:10])
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"font-size: {fs - 5}px; color: #585b70; background: transparent;")
        cl.addWidget(name)
        container.mousePressEvent = lambda e, idx=index: self._remove_at(idx)
        return container

    def _remove_at(self, index):
        if 0 <= index < len(self._references):
            del self._references[index]
            self._update_thumbs()
            self._update_visibility()
            self.references_changed.emit(self._references)

    def get_references(self):
        return list(self._references)

    def clear(self):
        if not self._references:
            return
        self._references.clear()
        self._update_thumbs()
        self._update_visibility()
        self.references_changed.emit(self._references)
