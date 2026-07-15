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
from core.product_parser import parse_product_markdown, scan_product_directory, ProductInfo
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
                 product_info=None):
        super().__init__()
        self.llm_config = llm_config
        self.product_name = product_name
        self.product_desc = product_desc
        self.selling_points = selling_points
        self.template = template
        self.frame_count = frame_count
        self.total_duration = total_duration
        self.product_info = product_info

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
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

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
        self.product_list.setMaximumHeight(160)
        self.product_list.setStyleSheet("""
            QListWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QListWidget::item:hover {
                background-color: #45475a;
            }
        """)
        self.product_list.itemClicked.connect(self._on_product_selected)
        product_form.addRow(self.product_list)

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

        left_layout.addWidget(product_group)

        # 风格模板
        style_group = QGroupBox("风格模板")
        style_layout = QVBoxLayout(style_group)

        self.style_combo = QComboBox()
        for t in TEMPLATES:
            self.style_combo.addItem(f"{t.name} - {t.description}", t.key)
        style_layout.addWidget(self.style_combo)

        self.style_desc_label = QLabel()
        self.style_desc_label.setWordWrap(True)
        self.style_desc_label.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 4px;")
        style_layout.addWidget(self.style_desc_label)

        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        left_layout.addWidget(style_group)

        # 分镜参数
        param_group = QGroupBox("分镜参数")
        param_form = QFormLayout(param_group)

        self.frame_count_spin = QSpinBox()
        self.frame_count_spin.setRange(3, 10)
        self.frame_count_spin.setValue(self.config["storyboard"]["frame_count"])
        param_form.addRow("分镜数：", self.frame_count_spin)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(self.config["storyboard"]["duration"])
        param_form.addRow("总时长（秒）：", self.duration_spin)

        left_layout.addWidget(param_group)

        # 历史缓存版本
        cache_group = QGroupBox("历史版本")
        cache_layout = QHBoxLayout(cache_group)
        self.cache_combo = QComboBox()
        self.cache_combo.setStyleSheet("""
            QComboBox { padding: 4px 8px; }
        """)
        self.cache_combo.addItem("-- 无缓存 --", "")
        cache_layout.addWidget(self.cache_combo, 1)
        self.cache_load_btn = QPushButton("加载")
        self.cache_load_btn.setFixedWidth(50)
        self.cache_load_btn.clicked.connect(self._load_selected_cache)
        cache_layout.addWidget(self.cache_load_btn)
        left_layout.addWidget(cache_group)

        # 操作按钮
        self.generate_script_btn = QPushButton("🎬 生成分镜脚本")
        self.generate_script_btn.setMinimumHeight(40)
        self.generate_script_btn.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #11111b; font-size: 14px; font-weight: bold; border-radius: 6px; border: none; }"
            "QPushButton:hover { background: #b4befe; }"
            "QPushButton:disabled { background: #313244; color: #585b70; }"
        )
        self.generate_script_btn.clicked.connect(self._generate_script)
        left_layout.addWidget(self.generate_script_btn)

        self.generate_images_btn = QPushButton("🖼️ 生成全部图片")
        self.generate_images_btn.setMinimumHeight(36)
        self.generate_images_btn.setEnabled(False)
        self.generate_images_btn.setStyleSheet(
            "QPushButton { background: #a6e3a1; color: #11111b; font-size: 13px; border-radius: 6px; border: none; }"
            "QPushButton:hover { background: #94e2d5; }"
            "QPushButton:disabled { background: #313244; color: #585b70; }"
        )
        self.generate_images_btn.clicked.connect(self._generate_all_images)
        left_layout.addWidget(self.generate_images_btn)

        # 导出按钮
        export_layout = QHBoxLayout()
        self.export_json_btn = QPushButton("导出 JSON")
        self.export_json_btn.setEnabled(False)
        self.export_json_btn.clicked.connect(self._export_json)
        export_layout.addWidget(self.export_json_btn)

        self.export_md_btn = QPushButton("导出 MD")
        self.export_md_btn.setEnabled(False)
        self.export_md_btn.clicked.connect(self._export_markdown)
        export_layout.addWidget(self.export_md_btn)

        self.export_pkg_btn = QPushButton("导出全部")
        self.export_pkg_btn.setEnabled(False)
        self.export_pkg_btn.clicked.connect(self._export_package)
        export_layout.addWidget(self.export_pkg_btn)

        left_layout.addLayout(export_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        left_layout.addWidget(self.status_label)

        left_layout.addStretch()

        # 设置按钮
        self.settings_btn = QPushButton("⚙ 设置")
        self.settings_btn.setMaximumWidth(100)
        self.settings_btn.clicked.connect(self._open_settings)
        left_layout.addWidget(self.settings_btn)

        # ========== 右侧面板 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 分镜视图（包含帧列表+详情+提示词）
        self.storyboard_view = StoryboardView()
        self.storyboard_view.frame_selected.connect(self._on_frame_selected)
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
        copy_group_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        bottom_bar.addWidget(copy_group_label)

        self.copy_prompt_en_btn = QPushButton("提示词EN")
        self.copy_prompt_en_btn.setFixedHeight(30)
        self.copy_prompt_en_btn.setStyleSheet(
            "QPushButton { background: #313244; color: #cdd6f4; font-size: 11px; border-radius: 4px; border: 1px solid #45475a; padding: 2px 10px; }"
            "QPushButton:hover { background: #45475a; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.copy_prompt_en_btn.setEnabled(False)
        self.copy_prompt_en_btn.clicked.connect(lambda: self._copy_all_field("image_prompt"))
        bottom_bar.addWidget(self.copy_prompt_en_btn)

        self.copy_prompt_cn_btn = QPushButton("提示词CN")
        self.copy_prompt_cn_btn.setFixedHeight(30)
        self.copy_prompt_cn_btn.setStyleSheet(
            "QPushButton { background: #313244; color: #cdd6f4; font-size: 11px; border-radius: 4px; border: 1px solid #45475a; padding: 2px 10px; }"
            "QPushButton:hover { background: #45475a; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.copy_prompt_cn_btn.setEnabled(False)
        self.copy_prompt_cn_btn.clicked.connect(lambda: self._copy_all_field("image_prompt_cn"))
        bottom_bar.addWidget(self.copy_prompt_cn_btn)

        self.copy_motion_en_btn = QPushButton("镜头EN")
        self.copy_motion_en_btn.setFixedHeight(30)
        self.copy_motion_en_btn.setStyleSheet(
            "QPushButton { background: #313244; color: #cdd6f4; font-size: 11px; border-radius: 4px; border: 1px solid #45475a; padding: 2px 10px; }"
            "QPushButton:hover { background: #45475a; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.copy_motion_en_btn.setEnabled(False)
        self.copy_motion_en_btn.clicked.connect(lambda: self._copy_all_field("camera_motion"))
        bottom_bar.addWidget(self.copy_motion_en_btn)

        self.copy_motion_cn_btn = QPushButton("镜头CN")
        self.copy_motion_cn_btn.setFixedHeight(30)
        self.copy_motion_cn_btn.setStyleSheet(
            "QPushButton { background: #313244; color: #cdd6f4; font-size: 11px; border-radius: 4px; border: 1px solid #45475a; padding: 2px 10px; }"
            "QPushButton:hover { background: #45475a; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.copy_motion_cn_btn.setEnabled(False)
        self.copy_motion_cn_btn.clicked.connect(lambda: self._copy_all_field("camera_motion_cn"))
        bottom_bar.addWidget(self.copy_motion_cn_btn)

        self.copy_hint_en_btn = QPushButton("动态EN")
        self.copy_hint_en_btn.setFixedHeight(30)
        self.copy_hint_en_btn.setStyleSheet(
            "QPushButton { background: #313244; color: #cdd6f4; font-size: 11px; border-radius: 4px; border: 1px solid #45475a; padding: 2px 10px; }"
            "QPushButton:hover { background: #45475a; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.copy_hint_en_btn.setEnabled(False)
        self.copy_hint_en_btn.clicked.connect(lambda: self._copy_all_field("motion_hint"))
        bottom_bar.addWidget(self.copy_hint_en_btn)

        self.copy_hint_cn_btn = QPushButton("动态CN")
        self.copy_hint_cn_btn.setFixedHeight(30)
        self.copy_hint_cn_btn.setStyleSheet(
            "QPushButton { background: #313244; color: #cdd6f4; font-size: 11px; border-radius: 4px; border: 1px solid #45475a; padding: 2px 10px; }"
            "QPushButton:hover { background: #45475a; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.copy_hint_cn_btn.setEnabled(False)
        self.copy_hint_cn_btn.clicked.connect(lambda: self._copy_all_field("motion_hint_cn"))
        bottom_bar.addWidget(self.copy_hint_cn_btn)

        # 豆包提示词按钮
        doubao_sep = QLabel("│")
        doubao_sep.setStyleSheet("color: #45475a; font-size: 14px;")
        bottom_bar.addWidget(doubao_sep)

        self.doubao_img_btn = QPushButton("📎 豆包图片")
        self.doubao_img_btn.setFixedHeight(30)
        self.doubao_img_btn.setStyleSheet(
            "QPushButton { background: #a6e3a1; color: #11111b; font-size: 11px; font-weight: bold; border-radius: 4px; border: none; padding: 2px 12px; }"
            "QPushButton:hover { background: #94d68a; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.doubao_img_btn.setEnabled(False)
        self.doubao_img_btn.clicked.connect(self._copy_doubao_image_prompt)
        bottom_bar.addWidget(self.doubao_img_btn)

        self.doubao_video_btn = QPushButton("🎬 豆包视频")
        self.doubao_video_btn.setFixedHeight(30)
        self.doubao_video_btn.setStyleSheet(
            "QPushButton { background: #f9e2af; color: #11111b; font-size: 11px; font-weight: bold; border-radius: 4px; border: none; padding: 2px 12px; }"
            "QPushButton:hover { background: #efd9a6; }"
            "QPushButton:disabled { background: #181825; color: #585b70; }"
        )
        self.doubao_video_btn.setEnabled(False)
        self.doubao_video_btn.clicked.connect(self._copy_doubao_video_prompt)
        bottom_bar.addWidget(self.doubao_video_btn)

        right_layout.addLayout(bottom_bar)

        # 组装
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)

        # 初始化风格描述
        self._on_style_changed(0)

    def _apply_style(self):
        """应用全局样式 - 深色主题"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #1e1e2e;
                color: #cdd6f4;
                font-size: 13px;
            }
            QGroupBox {
                font-weight: bold;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
                background: #181825;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 6px;
                color: #89b4fa;
            }
            QLabel {
                color: #cdd6f4;
            }
            QPushButton {
                padding: 6px 14px;
                border-radius: 4px;
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
            }
            QPushButton:hover {
                background: #45475a;
            }
            QPushButton:pressed {
                background: #585b70;
            }
            QPushButton:disabled {
                background: #181825;
                color: #585b70;
                border: 1px solid #313244;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                padding: 5px 8px;
                border: 1px solid #45475a;
                border-radius: 4px;
                background: #11111b;
                color: #cdd6f4;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #89b4fa;
            }
            QTextEdit {
                background: #11111b;
                color: #cdd6f4;
            }
            QComboBox QAbstractItemView {
                background: #1e1e2e;
                color: #cdd6f4;
                selection-background-color: #313244;
                border: 1px solid #45475a;
            }
            QProgressBar {
                border: 1px solid #45475a;
                border-radius: 4px;
                text-align: center;
                color: #cdd6f4;
                background: #11111b;
            }
            QProgressBar::chunk {
                background: #89b4fa;
                border-radius: 3px;
            }
            QScrollArea {
                border: 1px solid #45475a;
                background: #181825;
            }
            QScrollBar:horizontal {
                background: #181825;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #45475a;
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #585b70;
            }
            QScrollBar:vertical {
                background: #181825;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #45475a;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #585b70;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
            QFrame {
                color: #cdd6f4;
            }
        """)

    def _on_style_changed(self, index: int):
        """风格模板切换"""
        template = TEMPLATES[index]
        self.style_desc_label.setText(
            f"🎨 {template.description}\n"
            f"📷 推荐 {template.recommended_frames} 帧"
        )
        self.frame_count_spin.setValue(template.recommended_frames)

    def _load_product_list(self):
        """从配置的商品目录加载商品列表"""
        self.product_list.clear()
        directory = self.config.get("product", {}).get("directory", "")
        if not directory:
            return
        try:
            products = scan_product_directory(directory)
            for p in products:
                item_text = p["name"]
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, p["md_path"])
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
            # 刷新该商品的缓存列表
            self._refresh_cache_combo(info.name)
        except Exception as e:
            QMessageBox.critical(self, "解析失败", f"解析商品信息失败：\n\n{e}")

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

        lines = []
        lines.append(f"你是一个专业的零食带货短视频美术指导。我会给你商品参考图和分镜描述，你需要根据这些信息生成对应的图片。主要产品是{category}。")
        lines.append("")
        lines.append("## 图片要求")
        lines.append("- 构图：主体内容集中在画面中间 80% 区域，上下各留 10% 的留白空间（不要放重要元素在上下边缘）")
        lines.append("- 原因：后期会裁切上下边缘（水印区域），所以关键信息、商品、文字必须在中间 80% 以内")
        lines.append("- 风格：快速、简洁、冲击力强，色彩饱和度高，适合短视频带货")
        lines.append("- 商品还原：严格参考我给的商品参考图，保持商品外观、颜色、包装高度一致")
        lines.append("- 不要在画面中生成任何中文文字")
        lines.append("- 画面比例：9:16（竖屏短视频）")
        lines.append("")
        lines.append(f"## 分镜列表（共 {frame_count} 帧，请一次性全部生成）")
        lines.append("")
        for i, f in enumerate(frames):
            frame_num = f.get("frame", i + 1)
            duration = f.get("duration", 0)
            lines.append(f"### 第 {frame_num} 帧（{duration:.1f}s）")
            lines.append(f"画面描述：{f.get('description', '—')}")
            lines.append(f"图片提示词：{f.get('image_prompt_cn', f.get('image_prompt', '—'))}")
            lines.append(f"画面动态：{f.get('motion_hint_cn', f.get('motion_hint', '—'))}")
            lines.append("")

        lines.append(f"请根据以上分镜列表，结合我提供的商品参考图，一次性生成全部 {frame_count} 张图片。")

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        self.status_label.setText(f"已复制豆包图片提示词（{frame_count} 帧）")

    def _copy_doubao_video_prompt(self):
        """复制豆包视频生成提示词"""
        if not self.current_frames_data:
            return
        category = self._get_product_category()
        frames = self.current_frames_data
        frame_count = len(frames)

        lines = []
        lines.append(f"现在根据刚才生成的图片，逐帧生成对应的视频。主要产品是{category}。")
        lines.append("")
        lines.append("## 视频要求")
        lines.append("- 主体始终保持在画面中间 80% 区域，上下各 10% 不要有重要内容（会被裁切掉水印）")
        lines.append("- 风格：快速、简洁、冲击力强，节奏干脆利落")
        lines.append("- 商品外观必须与参考图保持一致")
        lines.append("- 不要出现任何文字或水印")
        lines.append("- 画面比例：9:16（竖屏短视频）")
        lines.append("")
        lines.append(f"## 逐帧视频指令（共 {frame_count} 帧）")
        lines.append("")
        for i, f in enumerate(frames):
            frame_num = f.get("frame", i + 1)
            duration = f.get("duration", 0)
            lines.append(f"### 第 {frame_num} 帧（{duration:.1f}s）")
            lines.append(f"镜头运动：{f.get('camera_motion_cn', f.get('camera_motion', '—'))}")
            lines.append(f"画面动态：{f.get('motion_hint_cn', f.get('motion_hint', '—'))}")
            lines.append(f"时长：{duration:.1f} 秒")
            lines.append("")

        lines.append("请逐帧生成视频，每生成一段等我确认后再生成下一段。".format(frame_count))

        text = "\n".join(lines)
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
