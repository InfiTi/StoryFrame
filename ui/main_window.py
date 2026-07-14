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
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont, QPixmap

from config import load_config, save_config, OUTPUT_DIR
from core.templates import TEMPLATES, get_template_by_name
from core.llm_client import LLMClient
from core.image_client import ImageClient
from core.storyboard import generate_storyboard, Storyboard, StoryboardFrame
from core.product_parser import parse_product_markdown, scan_product_directory, ProductInfo
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

    def __init__(self, image_config, frame_index, prompt, output_path):
        super().__init__()
        self.image_config = image_config
        self.frame_index = frame_index
        self.prompt = prompt
        self.output_path = output_path

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
            ok, msg = client.generate(self.prompt, self.output_path)
            client.close()
            if ok:
                self.finished.emit(self.frame_index, self.output_path)
            else:
                self.error.emit(self.frame_index, msg)
        except Exception as e:
            self.error.emit(self.frame_index, str(e))


# ========== 主窗口 ==========

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StoryFrame - 分镜图生成器")
        self.setMinimumSize(1100, 700)
        self.config = load_config()
        self.current_storyboard: Storyboard | None = None
        self.current_frames_data: list = []
        self.product_info: ProductInfo | None = None

        # Worker 管理
        self.script_thread = None
        self.script_worker = None
        self.image_threads = []
        self.image_workers = []

        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ========== 左侧面板 ==========
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)

        # 产品输入
        product_group = QGroupBox("产品输入")
        product_form = QFormLayout(product_group)

        # 商品列表
        product_form.addRow(QLabel("选择商品："))
        self.product_list = QListWidget()
        self.product_list.setMaximumHeight(120)
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

        self.product_desc_input = QTextEdit()
        self.product_desc_input.setPlaceholderText("描述产品外观、口感、包装等...")
        self.product_desc_input.setMaximumHeight(80)
        product_form.addRow("产品描述：", self.product_desc_input)

        self.selling_points_input = QTextEdit()
        self.selling_points_input.setPlaceholderText("如：芒果味浓郁、柔软不粘牙、独立包装...")
        self.selling_points_input.setMaximumHeight(80)
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

        # 分镜时间轴
        self.storyboard_view = StoryboardView()
        right_layout.addWidget(self.storyboard_view, stretch=3)

        # 帧详情
        detail_group = QGroupBox("帧详情")
        detail_layout = QVBoxLayout(detail_group)

        # 图片提示词
        detail_layout.addWidget(QLabel("图片提示词（用于 AI 生图）："))
        self.image_prompt_edit = QTextEdit()
        self.image_prompt_edit.setReadOnly(True)
        self.image_prompt_edit.setMaximumHeight(80)
        detail_layout.addWidget(self.image_prompt_edit)

        # 镜头运动
        detail_layout.addWidget(QLabel("镜头运动（用于图生视频）："))
        self.camera_motion_edit = QTextEdit()
        self.camera_motion_edit.setReadOnly(True)
        self.camera_motion_edit.setMaximumHeight(60)
        detail_layout.addWidget(self.camera_motion_edit)

        # 画面动态提示
        detail_layout.addWidget(QLabel("画面动态（产品怎么动）："))
        self.motion_hint_edit = QTextEdit()
        self.motion_hint_edit.setReadOnly(True)
        self.motion_hint_edit.setMaximumHeight(60)
        detail_layout.addWidget(self.motion_hint_edit)

        # 单帧生成图片按钮
        self.generate_single_btn = QPushButton("🖼️ 生成此帧图片")
        self.generate_single_btn.setEnabled(False)
        self.generate_single_btn.clicked.connect(self._generate_single_image)
        detail_layout.addWidget(self.generate_single_btn)

        right_layout.addWidget(detail_group, stretch=2)

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

            # 填充输入框
            self.product_name_input.setText(info.name)
            self.product_desc_input.setPlainText(info.description)

            # 卖点用换行分隔
            points_text = "\n".join(info.selling_points)
            self.selling_points_input.setPlainText(points_text)

            # 状态提示
            texture_cn = "、".join(info.texture_keywords[:8]) if info.texture_keywords else "未检测到"
            self.status_label.setText(
                f"已选择：{info.name} | 质感关键词：{texture_cn}"
            )
        except Exception as e:
            QMessageBox.critical(self, "解析失败", f"解析商品信息失败：\n\n{e}")

    def _open_settings(self):
        """打开设置"""
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.config = load_config()
            self.status_label.setText("设置已保存")
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

        # 更新视图
        self.storyboard_view.set_frames(self.current_frames_data)
        self.storyboard_view.frame_selected.connect(self._on_frame_selected)

        # 恢复按钮
        self.generate_script_btn.setEnabled(True)
        self.generate_images_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
        self.export_md_btn.setEnabled(True)
        self.export_pkg_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"已生成 {len(storyboard.frames)} 帧分镜脚本")

    def _on_script_error(self, error: str):
        """分镜脚本生成失败"""
        self.generate_script_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("生成失败")
        QMessageBox.critical(self, "错误", f"生成分镜脚本失败：\n\n{error}")

    def _on_frame_selected(self, index: int):
        """选中某帧"""
        if 0 <= index < len(self.current_frames_data):
            frame = self.current_frames_data[index]
            self.image_prompt_edit.setText(frame.get("image_prompt", ""))
            self.camera_motion_edit.setText(frame.get("camera_motion", ""))
            self.motion_hint_edit.setText(frame.get("motion_hint", ""))
            self.generate_single_btn.setEnabled(True)
            self.storyboard_view.selected_index = index

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

        for i, idx in enumerate(indices):
            frame = self.current_storyboard.frames[idx]
            output_path = str(project_dir / f"frame_{frame.frame}.png")

            thread = QThread()
            worker = GenerateImageWorker(
                image_config=self.config["image"],
                frame_index=idx,
                prompt=frame.image_prompt,
                output_path=output_path,
            )
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(self._on_image_finished)
            worker.error.connect(self._on_image_error)
            worker.finished.connect(thread.quit)
            worker.error.connect(thread.quit)
            self.image_threads.append(thread)
            self.image_workers.append(worker)
            thread.start()

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

        # 清理线程
        self.image_threads.clear()
        self.image_workers.clear()

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
