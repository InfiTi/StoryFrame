"""主窗口"""

import json
import os
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QFormLayout, QMessageBox, QFileDialog,
    QProgressBar, QSplitter, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QApplication,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize
from PySide6.QtGui import QFont, QPixmap

from config import load_config, save_config, OUTPUT_DIR
from core.templates import TEMPLATES, get_template_by_name
from core.llm_client import LLMClient
from core.image_client import ImageClient
from core.storyboard import generate_storyboard, Storyboard, StoryboardFrame
from core.product_parser import parse_product_markdown, scan_product_directory, ProductInfo, update_product_markdown
from core.script_cache import save_cache, list_cache, load_cache, cleanup_cache
from core.exporter import export_json, export_markdown, export_package
from ui.settings_dialog import SettingsDialog
from ui.storyboard_view import StoryboardView


# ========== Worker 线程 ==========

class GenerateScriptWorker(QObject):
    """生成分镜脚本的工作线程"""
    finished = Signal(object)  # Storyboard
    error = Signal(str)
    chunk = Signal(str)  # 流式片段

    def __init__(self, llm_config, product_name, product_desc,
                 selling_points, template, frame_count, total_duration,
                 product_info=None, direction=""):
        super().__init__()
        self.llm_config = llm_config
        self.product_name = product_name
        self.product_desc = product_desc
        self.selling_points = selling_points
        self.template = template
        self.frame_count = frame_count
        self.total_duration = total_duration
        self.product_info = product_info
        self.direction = direction

    def run(self):
        try:
            llm = LLMClient(
                base_url=self.llm_config["base_url"],
                api_key=self.llm_config["api_key"],
                model=self.llm_config["model"],
            )

            def on_chunk(text):
                self.chunk.emit(text)

            sb = generate_storyboard(
                llm=llm,
                product_name=self.product_name,
                product_desc=self.product_desc,
                selling_points=self.selling_points,
                template=self.template,
                frame_count=self.frame_count,
                total_duration=self.total_duration,
                product_info=self.product_info,
                direction=self.direction,
                on_chunk=on_chunk,
            )
            llm.close()
            self.finished.emit(sb)
        except Exception as e:
            self.error.emit(str(e))


class GenerateImageWorker(QObject):
    """生成单帧图片的工作线程"""
    finished = Signal(int, str)  # frame_index, image_path
    error = Signal(int, str)     # frame_index, error_msg

    def __init__(self, image_config, frame_index, prompt, output_path,
                 reference_image=None, denoise=0.6, reference_images=None):
        super().__init__()
        self.image_config = image_config
        self.frame_index = frame_index
        self.prompt = prompt
        self.output_path = output_path
        self.reference_image = reference_image
        self.denoise = denoise
        self.reference_images = reference_images

    def run(self):
        try:
            client = ImageClient(
                provider=self.image_config["provider"],
                base_url=self.image_config["base_url"],
                api_key=self.image_config["api_key"],
                model=self.image_config["model"],
                size=self.image_config["size"],
                quality=self.image_config["quality"],
            )
            ok, msg = client.generate(
                self.prompt, self.output_path,
                reference_image=self.reference_image,
                denoise=self.denoise,
                reference_images=self.reference_images,
            )
            client.close()
            if ok:
                self.finished.emit(self.frame_index, self.output_path)
            else:
                self.error.emit(self.frame_index, msg)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(self.frame_index, str(e))


# ========== 主窗口 ==========

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StoryFrame - 分镜图生成器")
        self.setMinimumSize(1400, 900)
        self.config = load_config()
        self.current_storyboard: Storyboard | None = None
        self.current_frames_data: list = []
        self.product_info: ProductInfo | None = None
        self.current_product_folder: str = ""

        # Worker 管理
        self.script_thread = None
        self.script_worker = None
        self.image_threads = []
        self.image_workers = []
        self._current_image_thread = None
        self._current_image_worker = None
        self._image_queue = []
        self._image_project_dir = None
        self._image_reference = None
        self._image_denoise = 0.6

        self._init_ui()
        self._apply_style()
        self._load_product_list()

    def _init_ui(self):
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 8, 12, 12)
        root_layout.setSpacing(8)

        # ========== 顶部工具栏 ==========
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # 历史版本（左侧，紧凑）
        cache_label = QLabel("历史版本：")
        cache_label.setStyleSheet("color: #565f89; font-size: 12px;")
        toolbar.addWidget(cache_label)
        self.cache_combo = QComboBox()
        self.cache_combo.addItem("-- 无缓存 --", "")
        self.cache_combo.setFixedWidth(180)
        toolbar.addWidget(self.cache_combo)
        self.cache_load_btn = QPushButton("📂 加载")
        self.cache_load_btn.clicked.connect(self._load_selected_cache)
        toolbar.addWidget(self.cache_load_btn)

        toolbar.addStretch()

        # 核心操作按钮（右侧）
        self.generate_script_btn = QPushButton("🎬 生成分镜脚本")
        self.generate_script_btn.setMinimumHeight(36)
        self.generate_script_btn.setMinimumWidth(140)
        self.generate_script_btn.setStyleSheet(
            "QPushButton { background: #7aa2f7; color: #0f1117; font-size: 13px; font-weight: bold; border-radius: 6px; border: none; padding: 4px 16px; }"
            "QPushButton:hover { background: #89b0ff; }"
            "QPushButton:disabled { background: #2a2e3f; color: #4c5375; }"
        )
        self.generate_script_btn.clicked.connect(self._generate_script)
        toolbar.addWidget(self.generate_script_btn)

        self.generate_images_btn = QPushButton("🖼️ 生成全部图片")
        self.generate_images_btn.setMinimumHeight(36)
        self.generate_images_btn.setMinimumWidth(130)
        self.generate_images_btn.setEnabled(False)
        self.generate_images_btn.setStyleSheet(
            "QPushButton { background: #9ece6a; color: #0f1117; font-size: 13px; font-weight: bold; border-radius: 6px; border: none; padding: 4px 14px; }"
            "QPushButton:hover { background: #b5e89a; }"
            "QPushButton:disabled { background: #2a2e3f; color: #4c5375; }"
        )
        self.generate_images_btn.clicked.connect(self._generate_all_images)
        toolbar.addWidget(self.generate_images_btn)

        # 导出按钮组
        export_sep = QLabel("│")
        export_sep.setStyleSheet("color: #2a2e3f; font-size: 16px;")
        toolbar.addWidget(export_sep)
        self.export_json_btn = QPushButton("导出 JSON")
        self.export_json_btn.setEnabled(False)
        self.export_json_btn.clicked.connect(self._export_json)
        toolbar.addWidget(self.export_json_btn)
        self.export_md_btn = QPushButton("导出 MD")
        self.export_md_btn.setEnabled(False)
        self.export_md_btn.clicked.connect(self._export_markdown)
        toolbar.addWidget(self.export_md_btn)
        self.export_pkg_btn = QPushButton("导出全部")
        self.export_pkg_btn.setEnabled(False)
        self.export_pkg_btn.clicked.connect(self._export_package)
        toolbar.addWidget(self.export_pkg_btn)

        # 设置按钮（最右）
        self.settings_btn = QPushButton("⚙ 设置")
        self.settings_btn.setFixedWidth(70)
        self.settings_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(self.settings_btn)

        root_layout.addLayout(toolbar)

        # ========== 分镜参数行（独立行，避免拥挤） ==========
        param_row = QHBoxLayout()
        param_row.setSpacing(12)
        param_label = QLabel("分镜数：")
        param_label.setStyleSheet("color: #7aa2f7; font-size: 12px; font-weight: bold;")
        param_row.addWidget(param_label)
        self.frame_count_spin = QSpinBox()
        self.frame_count_spin.setRange(3, 10)
        self.frame_count_spin.setValue(self.config["storyboard"]["frame_count"])
        self.frame_count_spin.setFixedWidth(80)
        self.frame_count_spin.setStyleSheet(
            "QSpinBox { padding-right: 20px; }"
            "QSpinBox::up-button { width: 18px; }"
            "QSpinBox::down-button { width: 18px; }"
        )
        param_row.addWidget(self.frame_count_spin)

        param_row.addSpacing(16)

        dur_label = QLabel("总时长：")
        dur_label.setStyleSheet("color: #7aa2f7; font-size: 12px; font-weight: bold;")
        param_row.addWidget(dur_label)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(self.config["storyboard"]["duration"])
        self.duration_spin.setFixedWidth(80)
        self.duration_spin.setStyleSheet(
            "QSpinBox { padding-right: 20px; }"
            "QSpinBox::up-button { width: 18px; }"
            "QSpinBox::down-button { width: 18px; }"
        )
        self.duration_spin.valueChanged.connect(self._on_total_duration_changed)
        param_row.addWidget(self.duration_spin)
        dur_unit = QLabel("秒")
        dur_unit.setStyleSheet("color: #565f89; font-size: 12px;")
        param_row.addWidget(dur_unit)

        param_row.addStretch()
        root_layout.addLayout(param_row)

        # ========== 视频方向输入行 ==========
        direction_row = QHBoxLayout()
        direction_row.setSpacing(8)
        direction_label = QLabel("🎬 视频方向：")
        direction_label.setStyleSheet("color: #7aa2f7; font-size: 12px; font-weight: bold;")
        direction_label.setFixedWidth(90)
        direction_row.addWidget(direction_label)
        self.direction_input = QLineEdit()
        self.direction_input.setPlaceholderText("如：强调性价比、节日氛围、搞笑风格、突出原材料...")
        self.direction_input.setStyleSheet("QLineEdit { color: #c0caf5; font-size: 12px; }")
        direction_row.addWidget(self.direction_input, 1)
        root_layout.addLayout(direction_row)

        # 进度条 + 状态（工具栏下方，细条）
        status_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        status_row.addWidget(self.progress_bar, 1)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #565f89; font-size: 11px;")
        status_row.addWidget(self.status_label)
        root_layout.addLayout(status_row)

        # ========== 主内容区（左 + 右） ==========
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        root_layout.addLayout(main_layout)

        # ========== 左侧面板 ==========
        left_panel = QWidget()
        left_panel.setFixedWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)

        # 产品输入
        product_group = QGroupBox("产品输入")
        product_form = QFormLayout(product_group)

        # 商品列表
        product_form.addRow(QLabel("选择商品："))

        self.product_list = QListWidget()
        self.product_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.product_list.setMinimumHeight(200)
        self.product_list.setMaximumHeight(350)
        self.product_list.setTextElideMode(Qt.ElideRight)
        self.product_list.setWordWrap(False)
        self.product_list.itemClicked.connect(self._on_product_selected)
        product_form.addRow(self.product_list)

        # 刷新按钮
        self.refresh_product_btn = QPushButton("🔄 刷新商品列表")
        self.refresh_product_btn.setFixedHeight(32)
        self.refresh_product_btn.clicked.connect(self._load_product_list)
        product_form.addRow(self.refresh_product_btn)

        self.product_name_input = QLineEdit()
        self.product_name_input.setPlaceholderText("如：芒果干")
        product_form.addRow("零食名称：", self.product_name_input)

        self.product_category_input = QLineEdit()
        self.product_category_input.setPlaceholderText("如：饼干、面包、牛肉干")
        product_form.addRow("商品类目：", self.product_category_input)

        self.product_desc_input = QTextEdit()
        self.product_desc_input.setPlaceholderText("描述产品外观、口感、包装等...")
        self.product_desc_input.setMaximumHeight(100)
        product_form.addRow("产品描述：", self.product_desc_input)

        self.selling_points_input = QTextEdit()
        self.selling_points_input.setPlaceholderText("如：芒果味浓郁、柔软不粘牙、独立包装...")
        self.selling_points_input.setMaximumHeight(100)
        product_form.addRow("卖点：", self.selling_points_input)

        # 保存商品信息回 Markdown
        self.save_product_btn = QPushButton("💾 保存商品信息")
        self.save_product_btn.setFixedHeight(34)
        self.save_product_btn.setEnabled(False)
        self.save_product_btn.clicked.connect(self._save_product_info)
        product_form.addRow(self.save_product_btn)

        left_layout.addWidget(product_group)

        # 风格模板
        style_group = QGroupBox("风格模板")
        style_layout = QVBoxLayout(style_group)

        self.style_combo = QComboBox()
        for t in TEMPLATES:
            self.style_combo.addItem(f"{t.name} - {t.description}", t.key)
        style_layout.addWidget(self.style_combo)

        # 背景音乐选择
        bgm_row = QHBoxLayout()
        bgm_label = QLabel("🎵 背景音乐：")
        bgm_label.setFixedWidth(90)
        bgm_row.addWidget(bgm_label)

        self.bgm_combo = QComboBox()
        self.bgm_combo.addItem("古典")
        self.bgm_combo.addItem("冲击感")
        self.bgm_combo.addItem("轻柔")
        self.bgm_combo.addItem("清新")
        self.bgm_combo.addItem("国潮")
        self.bgm_combo.addItem("动感")
        self.bgm_combo.addItem("温暖")
        self.bgm_combo.addItem("欢快")
        self.bgm_combo.addItem("悬疑")
        self.bgm_combo.addItem("电子")
        bgm_row.addWidget(self.bgm_combo, 1)
        style_layout.addLayout(bgm_row)

        self.style_desc_label = QLabel()
        self.style_desc_label.setWordWrap(True)
        self.style_desc_label.setStyleSheet("color: #565f89; font-size: 12px; padding: 4px;")
        style_layout.addWidget(self.style_desc_label)

        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        left_layout.addWidget(style_group)

        left_layout.addStretch()

        # ========== 右侧面板 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 分镜视图（包含帧列表+详情+提示词）
        self.storyboard_view = StoryboardView()
        self.storyboard_view.frame_selected.connect(self._on_frame_selected)
        self.storyboard_view.frame_duration_changed.connect(self._on_frame_duration_changed)
        right_layout.addWidget(self.storyboard_view, stretch=1)

        # 底部操作栏
        bottom_bar = QHBoxLayout()

        self.generate_single_btn = QPushButton("🖼️ 生成此帧图片")
        self.generate_single_btn.setEnabled(False)
        self.generate_single_btn.clicked.connect(self._generate_single_image)
        bottom_bar.addWidget(self.generate_single_btn)
        bottom_bar.addStretch()

        # 复制按钮组
        copy_group_label = QLabel("复制全部帧：")
        copy_group_label.setStyleSheet("color: #565f89; font-size: 12px;")
        bottom_bar.addWidget(copy_group_label)

        self.copy_prompt_en_btn = QPushButton("提示词EN")
        self.copy_prompt_en_btn.setFixedHeight(30)
        self.copy_prompt_en_btn.setEnabled(False)
        self.copy_prompt_en_btn.clicked.connect(lambda: self._copy_all_field("image_prompt"))
        bottom_bar.addWidget(self.copy_prompt_en_btn)

        self.copy_prompt_cn_btn = QPushButton("提示词CN")
        self.copy_prompt_cn_btn.setFixedHeight(30)
        self.copy_prompt_cn_btn.setEnabled(False)
        self.copy_prompt_cn_btn.clicked.connect(lambda: self._copy_all_field("image_prompt_cn"))
        bottom_bar.addWidget(self.copy_prompt_cn_btn)

        self.copy_motion_en_btn = QPushButton("镜头EN")
        self.copy_motion_en_btn.setFixedHeight(30)
        self.copy_motion_en_btn.setEnabled(False)
        self.copy_motion_en_btn.clicked.connect(lambda: self._copy_all_field("camera_motion"))
        bottom_bar.addWidget(self.copy_motion_en_btn)

        self.copy_motion_cn_btn = QPushButton("镜头CN")
        self.copy_motion_cn_btn.setFixedHeight(30)
        self.copy_motion_cn_btn.setEnabled(False)
        self.copy_motion_cn_btn.clicked.connect(lambda: self._copy_all_field("camera_motion_cn"))
        bottom_bar.addWidget(self.copy_motion_cn_btn)

        self.copy_hint_en_btn = QPushButton("动态EN")
        self.copy_hint_en_btn.setFixedHeight(30)
        self.copy_hint_en_btn.setEnabled(False)
        self.copy_hint_en_btn.clicked.connect(lambda: self._copy_all_field("motion_hint"))
        bottom_bar.addWidget(self.copy_hint_en_btn)

        self.copy_hint_cn_btn = QPushButton("动态CN")
        self.copy_hint_cn_btn.setFixedHeight(30)
        self.copy_hint_cn_btn.setEnabled(False)
        self.copy_hint_cn_btn.clicked.connect(lambda: self._copy_all_field("motion_hint_cn"))
        bottom_bar.addWidget(self.copy_hint_cn_btn)

        # 豆包提示词按钮
        doubao_sep = QLabel("│")
        doubao_sep.setStyleSheet("color: #2a2e3f; font-size: 14px;")
        bottom_bar.addWidget(doubao_sep)

        self.doubao_img_btn = QPushButton("📎 豆包图片")
        self.doubao_img_btn.setFixedHeight(30)
        self.doubao_img_btn.setStyleSheet(
            "QPushButton { background: #9ece6a; color: #0f1117; font-size: 11px; font-weight: bold; border-radius: 6px; border: none; padding: 2px 12px; }"
            "QPushButton:hover { background: #b5e89a; }"
            "QPushButton:disabled { background: #1f2233; color: #3b4056; }"
        )
        self.doubao_img_btn.setEnabled(False)
        self.doubao_img_btn.clicked.connect(self._copy_doubao_image_prompt)
        bottom_bar.addWidget(self.doubao_img_btn)

        self.doubao_video_btn = QPushButton("🎬 豆包视频")
        self.doubao_video_btn.setFixedHeight(30)
        self.doubao_video_btn.setStyleSheet(
            "QPushButton { background: #e0af68; color: #0f1117; font-size: 11px; font-weight: bold; border-radius: 6px; border: none; padding: 2px 12px; }"
            "QPushButton:hover { background: #f0c878; }"
            "QPushButton:disabled { background: #1f2233; color: #3b4056; }"
        )
        self.doubao_video_btn.setEnabled(False)
        self.doubao_video_btn.clicked.connect(self._copy_doubao_video_prompt)
        bottom_bar.addWidget(self.doubao_video_btn)

        right_layout.addLayout(bottom_bar)

        # 组装（左侧面板直接放入，不滚动）
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)

        # 初始化风格描述
        self._on_style_changed(0)

    def _apply_style(self):
        """应用全局样式 - Tokyo Night 深蓝主题"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #0f1117;
                color: #a9b1d6;
                font-size: 13px;
            }
            QGroupBox {
                font-weight: bold;
                color: #7aa2f7;
                border: 1px solid #2a2e3f;
                border-radius: 8px;
                margin-top: 12px;
                padding: 18px 10px 10px 10px;
                background: #161720;
            }
            QGroupBox::title {
                left: 12px;
                padding: 0 8px;
                color: #7aa2f7;
                font-size: 13px;
            }
            QLabel {
                color: #a9b1d6;
            }
            QPushButton {
                padding: 7px 14px;
                border-radius: 6px;
                background: #2a2e3f;
                color: #a9b1d6;
                border: 1px solid #2a2e3f;
            }
            QPushButton:hover {
                background: #3b4056;
                border: 1px solid #4c5375;
            }
            QPushButton:pressed {
                background: #4c5375;
            }
            QPushButton:disabled {
                background: #161720;
                color: #3b4056;
                border: 1px solid #1f2233;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                padding: 6px 10px;
                border: 1px solid #2a2e3f;
                border-radius: 6px;
                background: #11131a;
                color: #c0caf5;
                selection-background-color: #3d59a1;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #7aa2f7;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #4c5375;
            }
            QTextEdit {
                background: #11131a;
                color: #c0caf5;
            }
            QComboBox QAbstractItemView {
                background: #11131a;
                color: #c0caf5;
                selection-background-color: #2a2e3f;
                selection-color: #7aa2f7;
                border: 1px solid #2a2e3f;
                border-radius: 6px;
                padding: 4px;
            }
            QProgressBar {
                border: 1px solid #2a2e3f;
                border-radius: 6px;
                text-align: center;
                color: #a9b1d6;
                background: #11131a;
                height: 20px;
            }
            QProgressBar::chunk {
                background: #7aa2f7;
                border-radius: 4px;
            }
            QScrollArea {
                border: none;
                background: #0f1117;
            }
            QScrollBar:horizontal {
                background: #0f1117;
                height: 10px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #2a2e3f;
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #4c5375;
            }
            QScrollBar:vertical {
                background: #0f1117;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #2a2e3f;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4c5375;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
            QFrame {
                color: #a9b1d6;
            }
            QListWidget {
                background: #11131a;
                border: 1px solid #2a2e3f;
                border-radius: 8px;
                color: #c0caf5;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 14px;
                border-radius: 4px;
                border-bottom: 1px solid #1f2233;
            }
            QListWidget::item:selected {
                background: #3d59a1;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background: #2a2e3f;
            }
        """)

    def _on_style_changed(self, index: int):
        """风格模板切换"""
        template = TEMPLATES[index]
        self.style_desc_label.setText(
            f"🎨 {template.description}\n"
            f"📷 推荐 {template.recommended_frames} 帧 | 冲击：{template.impact_level} | 节奏：{template.pacing_strategy}"
        )
        self.frame_count_spin.setValue(template.recommended_frames)
        # 同步背景音乐
        if template.bgm:
            i = self.bgm_combo.findText(template.bgm)
            if i >= 0:
                self.bgm_combo.setCurrentIndex(i)

    def _load_product_list(self):
        """从配置的商品目录加载商品列表"""
        self.product_list.clear()
        directory = self.config.get("product", {}).get("directory", "")
        if not directory:
            return
        try:
            products = scan_product_directory(directory)
            for p in products:
                full_name = p["name"]
                list_item = QListWidgetItem(full_name)
                list_item.setData(Qt.UserRole, p["md_path"])
                list_item.setToolTip(full_name)
                self.product_list.addItem(list_item)
            if products:
                self.status_label.setText(f"已加载 {len(products)} 个商品")
        except Exception as e:
            self.status_label.setText(f"加载商品列表失败: {e}")

    def _on_product_selected(self, item):
        """点击商品列表项，解析对应的 Markdown 文件"""
        md_path = item.data(Qt.UserRole)
        if not md_path:
            return
        try:
            info = parse_product_markdown(md_path)
            self.product_info = info

            # 记录商品文件夹路径（用于查找参考图）
            from pathlib import Path
            self.current_product_folder = str(Path(md_path).parent)

            # 填充输入框
            self.product_name_input.setText(info.name)
            self.product_category_input.setText(info.category)
            self.product_desc_input.setPlainText(info.description)

            # 卖点用换行分隔
            points_text = "\n".join(info.selling_points)
            self.selling_points_input.setPlainText(points_text)

            # 状态提示
            texture_cn = "、".join(info.texture_keywords[:8]) if info.texture_keywords else "未检测到"
            self.status_label.setText(
                f"已选择：{info.name} | 质感关键词：{texture_cn}"
            )
            # 启用保存按钮
            self.save_product_btn.setEnabled(True)
            # 刷新该商品的缓存列表
            self._refresh_cache_combo(info.name)
        except Exception as e:
            QMessageBox.critical(self, "解析失败", f"解析商品信息失败：\n\n{e}")

    def _save_product_info(self):
        """将界面上修改的商品信息回写到 Markdown 文件"""
        if not self.product_info or not hasattr(self, 'current_product_folder'):
            return
        
        # 找到当前商品的 MD 文件路径
        md_path = None
        for i in range(self.product_list.count()):
            item = self.product_list.item(i)
            item_name = item.text()
            if item_name == self.product_info.name or (self.product_info.title and item_name in self.product_info.title):
                md_path = item.data(Qt.UserRole)
                break
        if not md_path:
            # fallback: 从 product_info.raw_text 的路径找
            return
        
        updated_fields = []
        
        # 保存商品类目
        new_category = self.product_category_input.text().strip()
        if new_category and new_category != self.product_info.category:
            if update_product_markdown(md_path, "商品类目", new_category):
                self.product_info.category = new_category
                updated_fields.append("类目")
        
        # 保存产品描述（写入「产品描述」字段，如果表格中没有则新增）
        new_desc = self.product_desc_input.toPlainText().strip()
        if new_desc and new_desc != self.product_info.description:
            if update_product_markdown(md_path, "产品描述", new_desc):
                self.product_info.description = new_desc
                updated_fields.append("描述")
        
        # 保存卖点（用分号连接，写入「卖点」字段）
        new_points = self.selling_points_input.toPlainText().strip()
        old_points = "\n".join(self.product_info.selling_points)
        if new_points and new_points != old_points:
            if update_product_markdown(md_path, "卖点", new_points.replace("\n", ";")):
                self.product_info.selling_points = new_points.split("\n")
                updated_fields.append("卖点")
        
        if updated_fields:
            self.status_label.setText(f"已保存到 Markdown：{'、'.join(updated_fields)}")
        else:
            self.status_label.setText("没有需要保存的更改")

    def _open_settings(self):
        """打开设置"""
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.config = load_config()
            self.status_label.setText("设置已保存")
            # 刷新分镜视图字体大小
            self.storyboard_view.reload_font_size()
        self._load_product_list()


    def _generate_script(self):
        """生成分镜脚本"""
        product_name = self.product_name_input.text().strip()
        product_desc = self.product_desc_input.toPlainText().strip()
        selling_points = self.selling_points_input.toPlainText().strip()

        if not product_name:
            QMessageBox.warning(self, "提示", "请输入零食名称")
            return
        if not product_desc:
            QMessageBox.warning(self, "提示", "请输入产品描述")
            return

        template = get_template_by_name(TEMPLATES[self.style_combo.currentIndex()].name)
        frame_count = self.frame_count_spin.value()
        total_duration = self.duration_spin.value()

        # 禁用按钮
        self.generate_script_btn.setEnabled(False)
        self.generate_images_btn.setEnabled(False)
        self.export_json_btn.setEnabled(False)
        self.export_md_btn.setEnabled(False)
        self.export_pkg_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.status_label.setText("正在生成分镜脚本...")
        self._chunk_count = 0

        # 启动工作线程
        self.script_thread = QThread()
        self.script_worker = GenerateScriptWorker(
            llm_config=self.config["llm"],
            product_name=product_name,
            product_desc=product_desc,
            selling_points=selling_points or "美味零食",
            template=template,
            frame_count=frame_count,
            total_duration=total_duration,
            product_info=self.product_info,
            direction=self.direction_input.text().strip(),
        )
        self.script_worker.moveToThread(self.script_thread)
        self.script_thread.started.connect(self.script_worker.run)
        self.script_worker.finished.connect(self._on_script_finished)
        self.script_worker.error.connect(self._on_script_error)
        self.script_worker.chunk.connect(self._on_script_chunk)
        self.script_worker.finished.connect(self.script_thread.quit)
        self.script_worker.error.connect(self.script_thread.quit)
        self.script_thread.start()

    def _on_script_chunk(self, text: str):
        """流式输出进度"""
        cursor = self.status_label.text()
        # 简单显示收到字符数
        if not hasattr(self, '_chunk_count'):
            self._chunk_count = 0
        self._chunk_count += len(text)
        self.status_label.setText(f"正在生成分镜脚本... 已接收 {self._chunk_count} 字符")

    def _on_total_duration_changed(self, total_duration: int):
        """总时长改变后，按比例缩放各帧时长（保持现有节奏）"""
        if not self.current_frames_data:
            self.statusBar().showMessage("请先生成分镜再调整总时长", 3000)
            return
        frame_count = len(self.current_frames_data)
        if frame_count == 0:
            return
        old_total = sum(f.get("duration", 0) for f in self.current_frames_data)
        if old_total <= 0:
            # 旧数据异常，fallback 到平均分配
            per_frame = total_duration / frame_count
            for frame in self.current_frames_data:
                frame["duration"] = round(per_frame, 1)
        else:
            ratio = total_duration / old_total
            for frame in self.current_frames_data:
                frame["duration"] = round(frame.get("duration", 0) * ratio, 1)
        # 同步 storyboard 对象
        if self.current_storyboard:
            for i, f in enumerate(self.current_storyboard.frames):
                f.duration = self.current_frames_data[i]["duration"]
        # 刷新视图
        self.storyboard_view.set_frames(self.current_frames_data)

    def _on_frame_duration_changed(self, index: int, duration: float):
        """单帧时长被修改，同步数据并更新总时长显示"""
        if not self.current_frames_data or not (0 <= index < len(self.current_frames_data)):
            return
        self.current_frames_data[index]["duration"] = duration
        # 同步 storyboard 对象
        if self.current_storyboard and index < len(self.current_storyboard.frames):
            self.current_storyboard.frames[index].duration = duration
        # 更新总时长输入框（不触发信号，避免循环）
        new_total = sum(f.get("duration", 0) for f in self.current_frames_data)
        self.duration_spin.blockSignals(True)
        self.duration_spin.setValue(int(round(new_total)))
        self.duration_spin.blockSignals(False)

    def _on_script_finished(self, storyboard: Storyboard):
        """分镜脚本生成完成"""
        self.current_storyboard = storyboard
        self.current_frames_data = [f.__dict__ for f in storyboard.frames]

        # 保存到缓存
        product_name = storyboard.product_name
        max_versions = self.config.get("cache", {}).get("max_versions", 3)
        save_cache(product_name, storyboard.to_dict(), storyboard.style_name)
        cleanup_cache(product_name, max_versions)
        self._refresh_cache_combo(product_name)

        # 更新视图
        self.storyboard_view.set_frames(self.current_frames_data)

        # 恢复按钮
        self.generate_script_btn.setEnabled(True)
        self.generate_images_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
        self.export_md_btn.setEnabled(True)
        self.export_pkg_btn.setEnabled(True)
        self.copy_prompt_en_btn.setEnabled(True)
        self.copy_prompt_cn_btn.setEnabled(True)
        self.copy_motion_en_btn.setEnabled(True)
        self.copy_motion_cn_btn.setEnabled(True)
        self.copy_hint_en_btn.setEnabled(True)
        self.copy_hint_cn_btn.setEnabled(True)
        self.doubao_img_btn.setEnabled(True)
        self.doubao_video_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"已生成 {len(storyboard.frames)} 帧分镜脚本（已缓存）")

    def _on_script_error(self, error: str):
        """分镜脚本生成失败"""
        self.generate_script_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("生成失败")
        QMessageBox.critical(self, "错误", f"生成分镜脚本失败：\n\n{error}")

    def _refresh_cache_combo(self, product_name: str):
        """刷新历史版本下拉框"""
        self.cache_combo.clear()
        self.cache_combo.addItem("-- 无缓存 --", "")
        if not product_name:
            return
        max_versions = self.config.get("cache", {}).get("max_versions", 3)
        versions = list_cache(product_name, max_versions)
        for v in versions:
            label = f"{v['timestamp']} | {v['style_name']} | {v['frame_count']}帧"
            self.cache_combo.addItem(label, v["file"])

    def _load_selected_cache(self):
        """加载选中的缓存版本"""
        file_path = self.cache_combo.currentData()
        if not file_path:
            return
        data = load_cache(file_path)
        if not data:
            QMessageBox.warning(self, "加载失败", "缓存文件已损坏或不存在")
            return

        # 重建 Storyboard 对象
        from core.storyboard import StoryboardFrame
        frames = []
        for item in data.get("frames", []):
            frames.append(StoryboardFrame(
                frame=item.get("frame", len(frames) + 1),
                duration=item.get("duration", 3.0),
                image_prompt=item.get("image_prompt", ""),
                image_prompt_cn=item.get("image_prompt_cn", ""),
                camera_motion=item.get("camera_motion", ""),
                camera_motion_cn=item.get("camera_motion_cn", ""),
                motion_hint=item.get("motion_hint", ""),
                motion_hint_cn=item.get("motion_hint_cn", ""),
                description=item.get("description", ""),
                image_path=item.get("image_path"),
            ))

        self.current_storyboard = Storyboard(
            product_name=data.get("product_name", ""),
            product_desc=data.get("product_desc", ""),
            style_name=data.get("style_name", ""),
            frames=frames,
        )
        self.current_frames_data = [f.__dict__ for f in frames]

        # 更新视图
        self.storyboard_view.set_frames(self.current_frames_data)

        self.generate_images_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
        self.export_md_btn.setEnabled(True)
        self.export_pkg_btn.setEnabled(True)
        self.copy_prompt_en_btn.setEnabled(True)
        self.copy_prompt_cn_btn.setEnabled(True)
        self.copy_motion_en_btn.setEnabled(True)
        self.copy_motion_cn_btn.setEnabled(True)
        self.copy_hint_en_btn.setEnabled(True)
        self.copy_hint_cn_btn.setEnabled(True)
        self.doubao_img_btn.setEnabled(True)
        self.doubao_video_btn.setEnabled(True)
        self.status_label.setText(f"已加载缓存版本：{len(frames)} 帧")

    def _on_frame_selected(self, index: int):
        """选中某帧"""
        self.generate_single_btn.setEnabled(True)

    def _copy_all_field(self, field_name: str):
        """复制所有帧的指定字段"""
        if not self.current_frames_data:
            return
        # 长字段（image_prompt）用空行分隔，短字段用换行分隔
        multiline = field_name in ("image_prompt", "image_prompt_cn")
        lines = []
        for f in self.current_frames_data:
            val = f.get(field_name, "")
            if multiline:
                lines.append(f"[Frame {f.get('frame', '?')}]\n{val}")
            else:
                lines.append(f"[Frame {f.get('frame', '?')}] {val}")
        sep = "\n\n" if multiline else "\n"
        text = sep.join(lines)
        QApplication.clipboard().setText(text)

        # 状态提示
        field_labels = {
            "image_prompt": "图片提示词（英文）",
            "image_prompt_cn": "图片提示词（中文）",
            "camera_motion": "镜头运动（英文）",
            "camera_motion_cn": "镜头运动（中文）",
            "motion_hint": "画面动态（英文）",
            "motion_hint_cn": "画面动态（中文）",
        }
        label = field_labels.get(field_name, field_name)
        self.status_label.setText(f"已复制 {len(self.current_frames_data)} 帧{label}")

    def _get_product_summary(self) -> str:
        """获取商品摘要信息"""
        name = self.product_name_input.text().strip()
        category = self.product_category_input.text().strip()
        desc = self.product_desc_input.toPlainText().strip()
        selling = self.selling_points_input.toPlainText().strip()
        parts = []
        if name:
            parts.append(f"商品名称：{name}")
        if category:
            parts.append(f"商品类目：{category}")
        if desc:
            parts.append(f"商品描述：{desc}")
        if selling:
            parts.append(f"卖点：{selling}")
        return "\n".join(parts) if parts else "（未填写商品信息）"

    def _get_product_category(self) -> str:
        """获取商品类目，用于豆包提示词中简要描述"""
        category = self.product_category_input.text().strip()
        if category:
            return category
        # 如果没填类目，从名称里尝试提取
        name = self.product_name_input.text().strip()
        return name if name else "零食"

    def _copy_doubao_image_prompt(self):
        """复制豆包图片生成提示词"""
        if not self.current_frames_data:
            return
        category = self._get_product_category()
        frames = self.current_frames_data
        frame_count = len(frames)
        template = TEMPLATES[self.style_combo.currentIndex()]

        from core.prompt_loader import get_doubao_image_prompt
        text = get_doubao_image_prompt(category, frames, frame_count, negative_words=template.negative_words)
        if not text:
            return  # 模板加载失败

        QApplication.clipboard().setText(text)
        self.status_label.setText(f"已复制豆包图片提示词（{frame_count} 帧）")

    def _copy_doubao_video_prompt(self):
        """复制豆包视频生成提示词"""
        if not self.current_frames_data:
            return
        category = self._get_product_category()
        frames = self.current_frames_data
        frame_count = len(frames)
        bgm_style = self.bgm_combo.currentText()
        template = TEMPLATES[self.style_combo.currentIndex()]

        from core.prompt_loader import get_doubao_video_prompt
        text = get_doubao_video_prompt(category, frames, frame_count, bgm_style, negative_words=template.negative_words)
        if not text:
            return  # 模板加载失败

        QApplication.clipboard().setText(text)
        self.status_label.setText(f"已复制豆包视频提示词（{frame_count} 帧）")

    def _generate_single_image(self):
        """生成选中帧的图片"""
        idx = self.storyboard_view.selected_index
        if idx < 0 or not self.current_frames_data:
            return

        self._generate_images([idx])

    def _generate_all_images(self):
        """生成所有帧的图片"""
        if not self.current_frames_data:
            return
        indices = list(range(len(self.current_frames_data)))
        self._generate_images(indices)

    def _generate_images(self, indices: list):
        """生成图片"""
        if not self.current_storyboard:
            return

        # 如果是 ComfyUI/SD/Kontext provider，让用户选参考图
        provider = self.config["image"].get("provider", "")
        reference_image = None
        reference_images = None
        denoise = self.config["image"].get("denoise", 0.6)

        if provider in ("comfyui", "sd", "kontext"):
            reference_image = self._select_reference_image()
            if reference_image is None:
                return  # 用户取消
            reference_images = [reference_image]

        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = OUTPUT_DIR / f"{self.current_storyboard.product_name}_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(indices))
        self.progress_bar.setValue(0)
        self.status_label.setText(f"正在生成 {len(indices)} 张图片...")
        self.generate_images_btn.setEnabled(False)
        self.generate_single_btn.setEnabled(False)

        self._image_total = len(indices)
        self._image_done = 0
        self._image_errors = []
        self._image_queue = list(indices)  # 待生成队列
        self._image_project_dir = project_dir
        self._image_reference = reference_image
        self._image_reference_images = reference_images
        self._image_denoise = denoise

        # 串行生成第一帧
        self._generate_next_image()

    def _generate_next_image(self):
        """串行生成下一帧图片"""
        if not self._image_queue:
            self._finish_image_generation()
            return

        idx = self._image_queue.pop(0)
        frame = self.current_storyboard.frames[idx]
        output_path = str(self._image_project_dir / f"frame_{frame.frame}.png")

        self.status_label.setText(
            f"正在生成第 {idx + 1}/{self._image_total} 帧..."
        )

        thread = QThread()
        worker = GenerateImageWorker(
            image_config=self.config["image"],
            frame_index=idx,
            prompt=frame.image_prompt,
            output_path=output_path,
            reference_image=self._image_reference,
            denoise=self._image_denoise,
            reference_images=getattr(self, '_image_reference_images', None),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_image_finished)
        worker.error.connect(self._on_image_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._on_thread_cleanup)
        # 存引用防止被GC
        self._current_image_thread = thread
        self._current_image_worker = worker
        thread.start()

    def _select_reference_image(self):
        """选择商品参考图"""
        # 优先从商品目录中找图片
        product_folder = None
        if hasattr(self, 'current_product_folder') and self.current_product_folder:
            product_folder = Path(self.current_product_folder)
        elif self.product_info and self.product_info.raw_text:
            # 尝试从缓存的商品路径找
            pass

        # 扫描商品目录下的图片
        image_files = []
        if product_folder and product_folder.exists():
            for sub in ["原始图", "处理图", ""]:
                search_dir = product_folder / sub if sub else product_folder
                if search_dir.exists():
                    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                        image_files.extend(sorted(search_dir.glob(ext)))

        if not image_files:
            # 没找到图片，让用户手动选
            path, _ = QFileDialog.getOpenFileName(
                self, "选择商品参考图",
                "",
                "图片文件 (*.jpg *.jpeg *.png *.webp)"
            )
            return path if path else None

        # 弹出选择对话框
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QPushButton, QHBoxLayout as QHL
        from PySide6.QtGui import QPixmap, QIcon

        dialog = QDialog(self)
        dialog.setWindowTitle("选择商品参考图")
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"找到 {len(image_files)} 张图片，选择一张作为参考："))

        list_widget = QListWidget()
        list_widget.setIconSize(QSize(80, 80))
        for img_path in image_files[:30]:  # 最多显示30张
            item = QListWidgetItem(str(img_path))
            pixmap = QPixmap(str(img_path))
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap.scaled(80, 80, Qt.KeepAspectRatio)))
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        # 也允许手动选
        btn_layout = QHL()
        manual_btn = QPushButton("手动选择...")
        manual_btn.clicked.connect(lambda: (
            dialog.done(2) if QFileDialog.getOpenFileName(
                self, "选择商品参考图", "", "图片文件 (*.jpg *.jpeg *.png *.webp)"
            )[0] else None
        ))
        btn_layout.addWidget(manual_btn)
        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        result = dialog.exec()
        if result == QDialog.Accepted and list_widget.currentItem():
            return list_widget.currentItem().text()
        return None

    def _on_thread_cleanup(self):
        """线程结束后清理并生成下一帧"""
        self._current_image_thread = None
        self._current_image_worker = None
        if self._image_queue:
            self._generate_next_image()

    def _on_image_finished(self, frame_index: int, image_path: str):
        """单帧图片生成完成"""
        self._image_done += 1
        self.progress_bar.setValue(self._image_done)

        # 更新数据和视图
        if 0 <= frame_index < len(self.current_frames_data):
            self.current_frames_data[frame_index]["image_path"] = image_path
        self.storyboard_view.update_frame_image(frame_index, image_path)

        if self._image_done >= self._image_total:
            self._finish_image_generation()

    def _on_image_error(self, frame_index: int, error: str):
        """单帧图片生成失败"""
        self._image_done += 1
        self._image_errors.append(f"第 {frame_index + 1} 帧: {error}")
        self.progress_bar.setValue(self._image_done)

        if self._image_done >= self._image_total:
            self._finish_image_generation()

    def _finish_image_generation(self):
        """图片生成完毕"""
        self.generate_images_btn.setEnabled(True)
        self.generate_single_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if self._image_errors:
            self.status_label.setText(
                f"完成 {self._image_done - len(self._image_errors)}/{self._image_total}，"
                f"{len(self._image_errors)} 张失败"
            )
            QMessageBox.warning(
                self, "部分失败",
                f"以下图片生成失败：\n\n" + "\n".join(self._image_errors)
            )
        else:
            self.status_label.setText(f"全部 {self._image_total} 张图片生成完成")

    def _export_json(self):
        """导出 JSON"""
        if not self.current_storyboard:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 JSON", "", "JSON 文件 (*.json)"
        )
        if path:
            export_json(self.current_storyboard, path)
            self.status_label.setText(f"已导出到 {path}")

    def _export_markdown(self):
        """导出 Markdown"""
        if not self.current_storyboard:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Markdown", "", "Markdown 文件 (*.md)"
        )
        if path:
            export_markdown(self.current_storyboard, path)
            self.status_label.setText(f"已导出到 {path}")

    def _export_package(self):
        """导出完整包"""
        if not self.current_storyboard:
            return
        path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if path:
            # 更新 storyboard 中的 image_path
            for i, frame_data in enumerate(self.current_frames_data):
                if i < len(self.current_storyboard.frames):
                    self.current_storyboard.frames[i].image_path = frame_data.get("image_path")
            result = export_package(self.current_storyboard, path)
            self.status_label.setText(f"已导出到 {result}")
            QMessageBox.information(self, "导出完成", f"已导出到：\n{result}")
