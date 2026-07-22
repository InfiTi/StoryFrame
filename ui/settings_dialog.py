"""设置对话框 — 分页式"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QGroupBox, QMessageBox,
    QPushButton, QHBoxLayout, QFileDialog, QLabel,
    QTabWidget, QWidget, QStackedWidget,
)
from PySide6.QtCore import Qt
from config import load_config, save_config, get_llm_config


# Provider 分类
API_PROVIDERS = {"dalle", "flux", "agnes"}
LOCAL_PROVIDERS = {"comfyui", "kontext", "sd"}


class SettingsDialog(QDialog):
    """设置对话框 — 分页式"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(520)
        self.config = load_config()
        self._init_ui()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #1e1e2e; color: #cdd6f4; }
            QTabWidget::pane {
                border: 1px solid #45475a;
                border-radius: 6px;
                background: #181825;
            }
            QTabBar::tab {
                background: #313244;
                color: #a6adc8;
                padding: 6px 16px;
                border: 1px solid #45475a;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #181825;
                color: #89b4fa;
                border-bottom: 2px solid #89b4fa;
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
            QLabel { color: #cdd6f4; }
            QPushButton {
                padding: 6px 14px;
                border-radius: 4px;
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
            }
            QPushButton:hover { background: #45475a; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                padding: 5px 8px;
                border: 1px solid #45475a;
                border-radius: 4px;
                background: #11111b;
                color: #cdd6f4;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #89b4fa;
            }
            QComboBox QAbstractItemView {
                background: #1e1e2e;
                color: #cdd6f4;
                selection-background-color: #313244;
                border: 1px solid #45475a;
            }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # === Tab 容器 ===
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Tab 1: LLM ---
        self.tabs.addTab(self._build_llm_tab(), "💬 LLM")

        # --- Tab 2: 图片生成 ---
        self.img_tab = self._build_image_tab()
        self.tabs.addTab(self.img_tab, "🖼 图片生成")

        # --- Tab 3: 视频生成 ---
        self.tabs.addTab(self._build_video_tab(), "🎬 视频生成")

        # --- Tab 4: 分镜 & 商品 ---
        self.tabs.addTab(self._build_misc_tab(), "📦 分镜 & 商品")

        # --- Tab 5: 风格模板 ---
        self.tabs.addTab(self._build_templates_tab(), "🎨 风格模板")

        # === 按钮 ===
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ==================== Tab: LLM ====================

    def _build_llm_tab(self) -> QWidget:
        tab = QWidget()
        vlayout = QVBoxLayout(tab)

        llm_group = QGroupBox("LLM 设置（兼容 OpenAI API 格式）")
        llm_layout = QVBoxLayout(llm_group)

        # 模型选择器
        model_selector_layout = QHBoxLayout()
        model_selector_layout.addWidget(QLabel("当前模型："))
        self.llm_provider_combo = QComboBox()
        self._refresh_provider_combo()
        self.llm_provider_combo.currentTextChanged.connect(self._on_provider_switch)
        model_selector_layout.addWidget(self.llm_provider_combo, 1)

        self.add_provider_btn = QPushButton("➕ 新增")
        self.add_provider_btn.clicked.connect(self._add_provider)
        model_selector_layout.addWidget(self.add_provider_btn)

        self.del_provider_btn = QPushButton("🗑 删除")
        self.del_provider_btn.clicked.connect(self._del_provider)
        model_selector_layout.addWidget(self.del_provider_btn)

        llm_layout.addLayout(model_selector_layout)

        llm_form = QFormLayout()
        llm_layout.addLayout(llm_form)

        self.llm_base_url = QLineEdit()
        self.llm_base_url.setPlaceholderText("http://localhost:1234/v1")
        llm_form.addRow("API 地址：", self.llm_base_url)

        self.llm_api_key = QLineEdit()
        self.llm_api_key.setPlaceholderText("API Key（LMStudio 填 lm-studio 即可）")
        llm_form.addRow("API Key：", self.llm_api_key)

        self.llm_model = QLineEdit()
        self.llm_model.setPlaceholderText("模型名称")
        llm_form.addRow("模型名：", self.llm_model)

        self._load_provider_values()

        vlayout.addWidget(llm_group)
        vlayout.addStretch()
        return tab

    # ==================== Tab: 图片生成 ====================

    def _build_image_tab(self) -> QWidget:
        tab = QWidget()
        vlayout = QVBoxLayout(tab)

        img_group = QGroupBox("图片生成设置")
        img_form = QFormLayout(img_group)

        # Provider 选择
        self.img_provider = QComboBox()
        self.img_provider.addItems(["comfyui", "kontext", "sd", "dalle", "flux", "agnes"])
        self.img_provider.setCurrentText(self.config["image"]["provider"])
        self.img_provider.currentTextChanged.connect(self._on_image_provider_changed)
        img_form.addRow("Provider：", self.img_provider)

        # --- 通用字段（所有 provider 都需要）---
        self.img_base_url = QLineEdit(self.config["image"]["base_url"])
        img_form.addRow("API 地址：", self.img_base_url)

        self.img_api_key = QLineEdit(self.config["image"]["api_key"])
        self.img_api_key.setPlaceholderText("本地服务可不填")
        img_form.addRow("API Key：", self.img_api_key)

        self.img_model = QLineEdit(self.config["image"]["model"])
        img_form.addRow("模型名：", self.img_model)

        # --- API 类字段（dalle/flux/agnes）---
        self.img_size = QComboBox()
        self.img_size.addItems(["1024x1024", "1024x1792", "1792x1024", "512x512"])
        self.img_size.setCurrentText(self.config["image"]["size"])
        self.img_size_row = img_form.addRow("尺寸：", self.img_size)

        self.img_quality = QComboBox()
        self.img_quality.addItems(["standard", "hd"])
        self.img_quality.setCurrentText(self.config["image"]["quality"])
        self.img_quality_row = img_form.addRow("质量：", self.img_quality)

        # --- 本地类字段（comfyui/kontext）---
        self.comfy_workflow = QLineEdit(
            self.config.get("image", {}).get("workflow", "workflows/flux_kontext_api.json")
        )
        self.comfy_workflow.setPlaceholderText("工作流 JSON 路径")
        self.comfy_workflow_row = img_form.addRow("工作流文件：", self.comfy_workflow)

        self.img_denoise = QDoubleSpinBox()
        self.img_denoise.setRange(0.1, 1.0)
        self.img_denoise.setSingleStep(0.05)
        self.img_denoise.setValue(self.config.get("image", {}).get("denoise", 0.6))
        self.img_denoise_row = img_form.addRow("去噪强度（img2img）：", self.img_denoise)

        # 测试按钮
        self.img_test_btn = QPushButton("测试连接")
        self.img_test_btn.clicked.connect(self._test_image_connection)
        img_form.addRow("", self.img_test_btn)

        # 保存行索引以便动态显隐
        # QFormLayout 的行索引: 0=provider, 1=base_url, 2=api_key, 3=model, 4=size, 5=quality, 6=workflow, 7=denoise, 8=test
        self._img_rows = {
            "size": 4,
            "quality": 5,
            "workflow": 6,
            "denoise": 7,
        }

        # 保存 img_form 引用供 _on_image_provider_changed 使用
        self._img_form = img_form

        vlayout.addWidget(img_group)
        vlayout.addStretch()

        # 初始化显隐
        self._on_image_provider_changed(self.img_provider.currentText())

        return tab

    def _on_image_provider_changed(self, provider: str):
        """根据 provider 类型动态显示/隐藏字段"""
        if not hasattr(self, '_img_form'):
            return  # 构建中，尚未初始化
        is_api = provider in API_PROVIDERS
        is_local = provider in LOCAL_PROVIDERS

        img_form = self._img_form
        # size 和 quality 仅 API 类显示
        for key in ("size", "quality"):
            row = self._img_rows[key]
            self._set_form_row_visible(img_form, row, is_api)

        # workflow 和 denoise 仅本地类显示
        for key in ("workflow", "denoise"):
            row = self._img_rows[key]
            self._set_form_row_visible(img_form, row, is_local)

        # 更新 placeholder 提示
        if is_api:
            self.img_base_url.setPlaceholderText("https://api.example.com/v1")
            if provider == "agnes":
                self.img_model.setPlaceholderText("agnes-image-2.1-flash")
            elif provider == "dalle":
                self.img_model.setPlaceholderText("dall-e-3")
            elif provider == "flux":
                self.img_model.setPlaceholderText("flux-pro")
        else:
            self.img_base_url.setPlaceholderText("http://127.0.0.1:8188")
            self.img_model.setPlaceholderText("模型名（可选）")

    @staticmethod
    def _set_form_row_visible(form: QFormLayout, row: int, visible: bool):
        """显示/隐藏 QFormLayout 的某一行"""
        item_role = form.itemAt(row, QFormLayout.LabelRole)
        field_role = form.itemAt(row, QFormLayout.FieldRole)
        for item in (item_role, field_role):
            if item and item.widget():
                item.widget().setVisible(visible)
            elif item and item.layout():
                for i in range(item.layout().count()):
                    sub = item.layout().itemAt(i)
                    if sub and sub.widget():
                        sub.widget().setVisible(visible)

    # ==================== Tab: 视频生成 ====================

    def _build_video_tab(self) -> QWidget:
        tab = QWidget()
        vlayout = QVBoxLayout(tab)

        vid_group = QGroupBox("视频生成设置")
        vid_form = QFormLayout(vid_group)

        self.vid_provider = QComboBox()
        self.vid_provider.addItems(["agnes"])
        self.vid_provider.setCurrentText(self.config.get("video", {}).get("provider", "agnes"))
        vid_form.addRow("Provider：", self.vid_provider)

        self.vid_base_url = QLineEdit(
            self.config.get("video", {}).get("base_url", "https://apihub.agnes-ai.com/v1")
        )
        vid_form.addRow("API 地址：", self.vid_base_url)

        self.vid_api_key = QLineEdit(self.config.get("video", {}).get("api_key", ""))
        self.vid_api_key.setPlaceholderText("sk-xxx")
        vid_form.addRow("API Key：", self.vid_api_key)

        self.vid_model = QLineEdit(self.config.get("video", {}).get("model", "agnes-video-v2.0"))
        vid_form.addRow("视频模型：", self.vid_model)

        self.vid_image_model = QLineEdit(
            self.config.get("video", {}).get("image_model", "agnes-image-2.1-flash")
        )
        self.vid_image_model.setPlaceholderText("agnes-image-2.1-flash")
        vid_form.addRow("图片模型（图生视频用）：", self.vid_image_model)

        # 尺寸预设
        self.vid_size = QComboBox()
        self.vid_size.addItems([
            "1024x1024 (1:1)", "1152x768 (3:2)", "768x1152 (2:3)",
            "1280x720 (16:9)", "720x1280 (9:16)"
        ])
        cur_w = self.config.get("video", {}).get("width", 1024)
        cur_h = self.config.get("video", {}).get("height", 1024)
        cur_size = f"{cur_w}x{cur_h}"
        for i in range(self.vid_size.count()):
            if cur_size in self.vid_size.itemText(i):
                self.vid_size.setCurrentIndex(i)
                break
        vid_form.addRow("视频尺寸：", self.vid_size)

        self.vid_num_frames = QSpinBox()
        self.vid_num_frames.setRange(9, 441)
        self.vid_num_frames.setSingleStep(8)
        self.vid_num_frames.setValue(self.config.get("video", {}).get("num_frames", 121))
        self.vid_num_frames.setSuffix(" 帧")
        vid_form.addRow("帧数（8n+1）：", self.vid_num_frames)

        self.vid_frame_rate = QSpinBox()
        self.vid_frame_rate.setRange(1, 60)
        self.vid_frame_rate.setValue(self.config.get("video", {}).get("frame_rate", 24))
        self.vid_frame_rate.setSuffix(" fps")
        vid_form.addRow("帧率：", self.vid_frame_rate)

        self.vid_negative = QLineEdit(self.config.get("video", {}).get("negative_prompt", ""))
        self.vid_negative.setPlaceholderText("负面提示词（可选）")
        vid_form.addRow("负面提示词：", self.vid_negative)

        self.vid_poll = QSpinBox()
        self.vid_poll.setRange(2, 30)
        self.vid_poll.setValue(self.config.get("video", {}).get("poll_interval", 5))
        self.vid_poll.setSuffix(" 秒")
        vid_form.addRow("轮询间隔：", self.vid_poll)

        self.vid_timeout = QSpinBox()
        self.vid_timeout.setRange(60, 1800)
        self.vid_timeout.setSingleStep(60)
        self.vid_timeout.setValue(self.config.get("video", {}).get("timeout", 600))
        self.vid_timeout.setSuffix(" 秒")
        vid_form.addRow("超时时间：", self.vid_timeout)

        self.vid_test_btn = QPushButton("测试连接")
        self.vid_test_btn.clicked.connect(self._test_video_connection)
        vid_form.addRow("", self.vid_test_btn)

        vlayout.addWidget(vid_group)
        vlayout.addStretch()
        return tab

    # ==================== Tab: 分镜 & 商品 ====================

    def _build_misc_tab(self) -> QWidget:
        tab = QWidget()
        vlayout = QVBoxLayout(tab)

        # 分镜默认设置
        sb_group = QGroupBox("分镜默认设置")
        sb_form = QFormLayout(sb_group)

        self.sb_frames = QSpinBox()
        self.sb_frames.setRange(3, 10)
        self.sb_frames.setValue(self.config["storyboard"]["frame_count"])
        sb_form.addRow("默认分镜数：", self.sb_frames)

        self.sb_duration = QSpinBox()
        self.sb_duration.setRange(5, 60)
        self.sb_duration.setValue(self.config["storyboard"]["duration"])
        sb_form.addRow("默认总时长（秒）：", self.sb_duration)

        vlayout.addWidget(sb_group)

        # 商品目录
        prod_group = QGroupBox("商品目录")
        prod_form = QFormLayout(prod_group)

        self.prod_dir = QLineEdit(self.config.get("product", {}).get("directory", ""))
        self.prod_dir.setPlaceholderText("如：F:\\Obsidian\\带货\\商品图")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_product_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.prod_dir)
        dir_layout.addWidget(browse_btn)
        prod_form.addRow("商品目录：", dir_layout)

        vlayout.addWidget(prod_group)

        # 缓存设置
        cache_group = QGroupBox("提示词缓存")
        cache_form = QFormLayout(cache_group)

        self.cache_max = QSpinBox()
        self.cache_max.setRange(1, 20)
        self.cache_max.setValue(self.config.get("cache", {}).get("max_versions", 3))
        cache_form.addRow("每个商品保留版本数：", self.cache_max)

        vlayout.addWidget(cache_group)

        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_form = QFormLayout(ui_group)

        self.ui_font_size = QSpinBox()
        self.ui_font_size.setRange(10, 24)
        self.ui_font_size.setValue(self.config.get("ui", {}).get("font_size", 13))
        self.ui_font_size.setSuffix(" px")
        ui_form.addRow("字体大小：", self.ui_font_size)

        vlayout.addWidget(ui_group)
        vlayout.addStretch()
        return tab

    # ==================== 保存 ====================

    def _save(self):
        """保存配置"""
        # 先保存当前 LLM provider 的编辑值
        self._save_current_provider_values()

        # 图片
        self.config["image"]["provider"] = self.img_provider.currentText()
        self.config["image"]["base_url"] = self.img_base_url.text().strip()
        self.config["image"]["api_key"] = self.img_api_key.text().strip()
        self.config["image"]["model"] = self.img_model.text().strip()
        self.config["image"]["size"] = self.img_size.currentText()
        self.config["image"]["quality"] = self.img_quality.currentText()
        self.config["image"]["workflow"] = self.comfy_workflow.text().strip()
        self.config["image"]["denoise"] = self.img_denoise.value()

        # 视频
        import re
        size_text = self.vid_size.currentText()
        size_match = re.match(r'(\d+)x(\d+)', size_text)
        if size_match:
            vid_w = int(size_match.group(1))
            vid_h = int(size_match.group(2))
        else:
            vid_w = 1024
            vid_h = 1024

        self.config.setdefault("video", {})
        self.config["video"]["provider"] = self.vid_provider.currentText()
        self.config["video"]["base_url"] = self.vid_base_url.text().strip()
        self.config["video"]["api_key"] = self.vid_api_key.text().strip()
        self.config["video"]["model"] = self.vid_model.text().strip()
        self.config["video"]["image_model"] = self.vid_image_model.text().strip()
        self.config["video"]["width"] = vid_w
        self.config["video"]["height"] = vid_h
        self.config["video"]["num_frames"] = self.vid_num_frames.value()
        self.config["video"]["frame_rate"] = self.vid_frame_rate.value()
        self.config["video"]["negative_prompt"] = self.vid_negative.text().strip()
        self.config["video"]["poll_interval"] = self.vid_poll.value()
        self.config["video"]["timeout"] = self.vid_timeout.value()

        # 分镜
        self.config["storyboard"]["frame_count"] = self.sb_frames.value()
        self.config["storyboard"]["duration"] = self.sb_duration.value()

        # 商品
        self.config.setdefault("product", {})
        self.config["product"]["directory"] = self.prod_dir.text().strip()

        # 缓存
        self.config.setdefault("cache", {})
        self.config["cache"]["max_versions"] = self.cache_max.value()

        # 界面
        self.config.setdefault("ui", {})
        self.config["ui"]["font_size"] = self.ui_font_size.value()

        save_config(self.config)
        self.accept()

    # ==================== LLM 多模型管理 ====================

    def _refresh_provider_combo(self):
        self.llm_provider_combo.blockSignals(True)
        self.llm_provider_combo.clear()
        providers = self.config.get("llm", {}).get("providers", {})
        for name in providers:
            self.llm_provider_combo.addItem(name)
        current = self.config.get("llm", {}).get("current", "default")
        if current in providers:
            self.llm_provider_combo.setCurrentText(current)
        self.llm_provider_combo.blockSignals(False)

    def _load_provider_values(self):
        cfg = get_llm_config(self.config)
        self.llm_base_url.setText(cfg.get("base_url", ""))
        self.llm_api_key.setText(cfg.get("api_key", ""))
        self.llm_model.setText(cfg.get("model", ""))

    def _save_current_provider_values(self):
        current = self.config.get("llm", {}).get("current", "default")
        self.config.setdefault("llm", {}).setdefault("providers", {})
        self.config["llm"]["providers"][current] = {
            "base_url": self.llm_base_url.text().strip(),
            "api_key": self.llm_api_key.text().strip(),
            "model": self.llm_model.text().strip(),
        }

    def _on_provider_switch(self, name: str):
        if not name:
            return
        self._save_current_provider_values()
        self.config["llm"]["current"] = name
        self._load_provider_values()

    def _add_provider(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "新增模型配置", "配置名称（如 codex / qwen / glm）：")
        if not ok or not name.strip():
            return
        name = name.strip()
        providers = self.config.setdefault("llm", {}).setdefault("providers", {})
        if name in providers:
            QMessageBox.warning(self, "重复", f"配置 '{name}' 已存在")
            return
        providers[name] = {
            "base_url": "http://localhost:1234/v1",
            "api_key": "",
            "model": "",
        }
        self._save_current_provider_values()
        self.config["llm"]["current"] = name
        self._refresh_provider_combo()
        self._load_provider_values()

    def _del_provider(self):
        providers = self.config.get("llm", {}).get("providers", {})
        if len(providers) <= 1:
            QMessageBox.warning(self, "无法删除", "至少需要保留一个模型配置")
            return
        current = self.config.get("llm", {}).get("current", "default")
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除配置 '{current}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        del providers[current]
        self.config["llm"]["current"] = next(iter(providers))
        self._refresh_provider_combo()
        self._load_provider_values()

    # ==================== 测试连接 ====================

    def _test_image_connection(self):
        from core.generation_manager import GenerationManager
        self._save()
        mgr = GenerationManager(self.config)
        ok, msg = mgr.test_image_connection()
        mgr.close()
        if ok:
            QMessageBox.information(self, "连接成功", msg)
        else:
            QMessageBox.warning(self, "连接失败", msg)

    def _test_video_connection(self):
        from core.generation_manager import GenerationManager
        self._save()
        mgr = GenerationManager(self.config)
        ok, msg = mgr.test_video_connection()
        mgr.close()
        if ok:
            QMessageBox.information(self, "连接成功", msg)
        else:
            QMessageBox.warning(self, "连接失败", msg)

    def _browse_product_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择商品目录")
        if path:
            self.prod_dir.setText(path)

    # ==================== Tab: 风格模板管理 ====================

    def _build_templates_tab(self) -> QWidget:
        from core.templates import TEMPLATES, StyleTemplate
        tab = QWidget()
        vlayout = QVBoxLayout(tab)

        # 模板列表
        list_group = QGroupBox("已有模板")
        list_layout = QVBoxLayout(list_group)

        self.tmpl_list = QComboBox()
        for t in TEMPLATES:
            self.tmpl_list.addItem(f"{t.name} ({t.key})", t.key)
        self.tmpl_list.currentIndexChanged.connect(self._on_tmpl_selected)
        list_layout.addWidget(self.tmpl_list)

        # 按钮行
        btn_row = QHBoxLayout()
        self.tmpl_add_btn = QPushButton("➕ 新增")
        self.tmpl_add_btn.clicked.connect(self._tmpl_add)
        btn_row.addWidget(self.tmpl_add_btn)

        self.tmpl_del_btn = QPushButton("🗑 删除")
        self.tmpl_del_btn.clicked.connect(self._tmpl_delete)
        btn_row.addWidget(self.tmpl_del_btn)

        self.tmpl_dup_btn = QPushButton("📋 复制")
        self.tmpl_dup_btn.clicked.connect(self._tmpl_duplicate)
        btn_row.addWidget(self.tmpl_dup_btn)

        btn_row.addStretch()
        list_layout.addLayout(btn_row)
        vlayout.addWidget(list_group)

        # 编辑区
        edit_group = QGroupBox("编辑")
        edit_form = QFormLayout(edit_group)

        self.tmpl_name = QLineEdit()
        self.tmpl_name.setPlaceholderText("如：赛博朋克")
        edit_form.addRow("名称：", self.tmpl_name)

        self.tmpl_key = QLineEdit()
        self.tmpl_key.setPlaceholderText("如：cyberpunk（英文唯一标识）")
        edit_form.addRow("Key：", self.tmpl_key)

        self.tmpl_desc = QLineEdit()
        self.tmpl_desc.setPlaceholderText("简短描述")
        edit_form.addRow("描述：", self.tmpl_desc)

        self.tmpl_style_words = QLineEdit()
        self.tmpl_style_words.setPlaceholderText("英文，逗号分隔，如: neon, cyberpunk, dark")
        edit_form.addRow("图片风格词：", self.tmpl_style_words)

        self.tmpl_camera_words = QLineEdit()
        self.tmpl_camera_words.setPlaceholderText("英文，逗号分隔，如: fast pan, zoom in")
        edit_form.addRow("镜头风格词：", self.tmpl_camera_words)

        self.tmpl_pacing = QComboBox()
        self.tmpl_pacing.addItems(["very_slow", "slow", "normal", "fast", "dramatic"])
        edit_form.addRow("节奏：", self.tmpl_pacing)

        self.tmpl_frames = QSpinBox()
        self.tmpl_frames.setRange(3, 10)
        edit_form.addRow("推荐帧数：", self.tmpl_frames)

        self.tmpl_bgm = QComboBox()
        self.tmpl_bgm.addItems(["古典", "冲击感", "轻柔", "清新", "国潮", "动感", "温暖", "欢快", "悬疑", "电子"])
        edit_form.addRow("背景音乐：", self.tmpl_bgm)

        self.tmpl_impact = QComboBox()
        self.tmpl_impact.addItems(["低", "中", "高"])
        edit_form.addRow("冲击强度：", self.tmpl_impact)

        self.tmpl_strategy = QComboBox()
        self.tmpl_strategy.addItems(["均匀分配", "前紧后松", "慢开场快结尾"])
        edit_form.addRow("节奏策略：", self.tmpl_strategy)

        self.tmpl_negative = QLineEdit()
        self.tmpl_negative.setPlaceholderText("负向词，默认: no text, no words, no logo...")
        edit_form.addRow("负向词：", self.tmpl_negative)

        # 保存按钮
        self.tmpl_save_btn = QPushButton("💾 保存修改")
        self.tmpl_save_btn.clicked.connect(self._tmpl_save)
        edit_form.addRow("", self.tmpl_save_btn)

        vlayout.addWidget(edit_group)
        vlayout.addStretch()

        # 初始化：加载第一个模板
        self._on_tmpl_selected(0)
        return tab

    def _on_tmpl_selected(self, index: int):
        """选中模板时加载到编辑区"""
        from core.templates import TEMPLATES
        if not TEMPLATES or index < 0 or index >= len(TEMPLATES):
            return
        t = TEMPLATES[index]
        self.tmpl_name.setText(t.name)
        self.tmpl_key.setText(t.key)
        self.tmpl_key.setReadOnly(True)  # key 不可改（用作唯一标识）
        self.tmpl_desc.setText(t.description)
        self.tmpl_style_words.setText(", ".join(t.image_style_words))
        self.tmpl_camera_words.setText(", ".join(t.camera_style_words))
        self.tmpl_pacing.setCurrentText(t.pacing)
        self.tmpl_frames.setValue(t.recommended_frames)
        self.tmpl_bgm.setCurrentText(t.bgm) if t.bgm in [self.tmpl_bgm.itemText(i) for i in range(self.tmpl_bgm.count())] else None
        self.tmpl_impact.setCurrentText(t.impact_level)
        self.tmpl_strategy.setCurrentText(t.pacing_strategy)
        self.tmpl_negative.setText(t.negative_words)

    def _tmpl_collect(self) -> 'StyleTemplate':
        """从编辑区收集数据构建 StyleTemplate"""
        from core.templates import StyleTemplate
        return StyleTemplate(
            name=self.tmpl_name.text().strip(),
            key=self.tmpl_key.text().strip(),
            description=self.tmpl_desc.text().strip(),
            image_style_words=[w.strip() for w in self.tmpl_style_words.text().split(",") if w.strip()],
            camera_style_words=[w.strip() for w in self.tmpl_camera_words.text().split(",") if w.strip()],
            pacing=self.tmpl_pacing.currentText(),
            recommended_frames=self.tmpl_frames.value(),
            bgm=self.tmpl_bgm.currentText(),
            impact_level=self.tmpl_impact.currentText(),
            pacing_strategy=self.tmpl_strategy.currentText(),
            negative_words=self.tmpl_negative.text().strip() or "no text, no words, no letters, no logo, no watermark, no label, no hands, no people",
        )

    def _tmpl_save(self):
        """保存当前编辑的模板"""
        from core.templates import TEMPLATES, save_templates
        key = self.tmpl_key.text().strip()
        if not key or not self.tmpl_name.text().strip():
            QMessageBox.warning(self, "提示", "名称和 Key 不能为空")
            return
        tmpl = self._tmpl_collect()
        # 找到并替换
        found = False
        for i, t in enumerate(TEMPLATES):
            if t.key == key:
                TEMPLATES[i] = tmpl
                found = True
                break
        if not found:
            TEMPLATES.append(tmpl)
        save_templates(TEMPLATES)
        # 刷新列表
        self._tmpl_refresh_list(key)
        QMessageBox.information(self, "已保存", f"模板 '{tmpl.name}' 已保存")

    def _tmpl_add(self):
        """新增模板：清空编辑区，Key 可编辑"""
        self.tmpl_name.clear()
        self.tmpl_key.clear()
        self.tmpl_key.setReadOnly(False)
        self.tmpl_desc.clear()
        self.tmpl_style_words.clear()
        self.tmpl_camera_words.clear()
        self.tmpl_pacing.setCurrentIndex(2)  # normal
        self.tmpl_frames.setValue(5)
        self.tmpl_bgm.setCurrentIndex(0)
        self.tmpl_impact.setCurrentIndex(1)  # 中
        self.tmpl_strategy.setCurrentIndex(0)  # 均匀分配
        self.tmpl_negative.clear()
        self.tmpl_name.setFocus()

    def _tmpl_duplicate(self):
        """复制当前模板为新模板"""
        from core.templates import TEMPLATES
        idx = self.tmpl_list.currentIndex()
        if idx < 0 or idx >= len(TEMPLATES):
            return
        t = TEMPLATES[idx]
        self.tmpl_name.setText(t.name + "_副本")
        self.tmpl_key.setText(t.key + "_copy")
        self.tmpl_key.setReadOnly(False)  # 新 key 可编辑
        self.tmpl_name.setFocus()

    def _tmpl_delete(self):
        """删除当前选中的模板"""
        from core.templates import TEMPLATES, remove_template
        idx = self.tmpl_list.currentIndex()
        if idx < 0 or idx >= len(TEMPLATES):
            return
        t = TEMPLATES[idx]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{t.name}' ({t.key}) 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            remove_template(t.key)
        except ValueError as e:
            QMessageBox.warning(self, "无法删除", str(e))
            return
        self._tmpl_refresh_list()
        QMessageBox.information(self, "已删除", f"模板 '{t.name}' 已删除")

    def _tmpl_refresh_list(self, select_key: str = None):
        """刷新模板下拉列表"""
        from core.templates import TEMPLATES
        self.tmpl_list.blockSignals(True)
        self.tmpl_list.clear()
        for t in TEMPLATES:
            self.tmpl_list.addItem(f"{t.name} ({t.key})", t.key)
        if select_key:
            for i in range(self.tmpl_list.count()):
                if self.tmpl_list.itemData(i) == select_key:
                    self.tmpl_list.setCurrentIndex(i)
                    break
        else:
            self.tmpl_list.setCurrentIndex(0)
        self.tmpl_list.blockSignals(False)
        self._on_tmpl_selected(self.tmpl_list.currentIndex())
