"""设置对话框"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QGroupBox, QMessageBox,
    QPushButton, QHBoxLayout, QFileDialog,
)
from PySide6.QtCore import Qt
from config import load_config, save_config


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self.config = load_config()
        self._init_ui()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #1e1e2e; color: #cdd6f4; }
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
            QLineEdit, QComboBox, QSpinBox {
                padding: 5px 8px;
                border: 1px solid #45475a;
                border-radius: 4px;
                background: #11111b;
                color: #cdd6f4;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
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

        # === LLM 设置 ===
        llm_group = QGroupBox("LLM 设置（兼容 OpenAI API 格式）")
        llm_form = QFormLayout(llm_group)

        self.llm_base_url = QLineEdit(self.config["llm"]["base_url"])
        self.llm_base_url.setPlaceholderText("http://localhost:1234/v1")
        llm_form.addRow("API 地址：", self.llm_base_url)

        self.llm_api_key = QLineEdit(self.config["llm"]["api_key"])
        self.llm_api_key.setPlaceholderText("API Key（LMStudio 填 lm-studio 即可）")
        llm_form.addRow("API Key：", self.llm_api_key)

        self.llm_model = QLineEdit(self.config["llm"]["model"])
        self.llm_model.setPlaceholderText("模型名称")
        llm_form.addRow("模型名：", self.llm_model)

        layout.addWidget(llm_group)

        # === 图片生成设置 ===
        img_group = QGroupBox("图片生成设置")
        img_form = QFormLayout(img_group)

        self.img_provider = QComboBox()
        self.img_provider.addItems(["dalle", "flux", "sd", "comfyui"])
        self.img_provider.setCurrentText(self.config["image"]["provider"])
        img_form.addRow("Provider：", self.img_provider)

        self.img_base_url = QLineEdit(self.config["image"]["base_url"])
        img_form.addRow("API 地址：", self.img_base_url)

        self.img_api_key = QLineEdit(self.config["image"]["api_key"])
        self.img_api_key.setPlaceholderText("API Key（本地 SD 可不填）")
        img_form.addRow("API Key：", self.img_api_key)

        self.img_model = QLineEdit(self.config["image"]["model"])
        img_form.addRow("模型名：", self.img_model)

        self.img_size = QComboBox()
        self.img_size.addItems(["1024x1024", "1024x1792", "1792x1024", "512x512"])
        self.img_size.setCurrentText(self.config["image"]["size"])
        img_form.addRow("尺寸：", self.img_size)

        self.img_quality = QComboBox()
        self.img_quality.addItems(["standard", "hd"])
        self.img_quality.setCurrentText(self.config["image"]["quality"])
        img_form.addRow("质量：", self.img_quality)

        # ComfyUI 专属设置
        self.comfy_workflow = QLineEdit(self.config.get("image", {}).get("workflow", "workflows/flux_img2img_api.json"))
        self.comfy_workflow.setPlaceholderText("工作流 JSON 路径（相对项目目录或绝对路径）")
        img_form.addRow("ComfyUI 工作流：", self.comfy_workflow)

        self.img_denoise = QDoubleSpinBox()
        self.img_denoise.setRange(0.1, 1.0)
        self.img_denoise.setSingleStep(0.05)
        self.img_denoise.setValue(self.config.get("image", {}).get("denoise", 0.4))
        img_form.addRow("去噪强度（图生图）：", self.img_denoise)

        layout.addWidget(img_group)

        # === 分镜默认设置 ===
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

        layout.addWidget(sb_group)

        # === 商品目录设置 ===
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

        layout.addWidget(prod_group)

        # === 缓存设置 ===
        cache_group = QGroupBox("提示词缓存")
        cache_form = QFormLayout(cache_group)

        self.cache_max = QSpinBox()
        self.cache_max.setRange(1, 20)
        self.cache_max.setValue(self.config.get("cache", {}).get("max_versions", 3))
        cache_form.addRow("每个商品保留版本数：", self.cache_max)

        layout.addWidget(cache_group)

        # === 按钮 ===
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_product_dir(self):
        """选择商品目录"""
        path = QFileDialog.getExistingDirectory(self, "选择商品目录")
        if path:
            self.prod_dir.setText(path)

    def _save(self):
        """保存配置"""
        self.config["llm"]["base_url"] = self.llm_base_url.text().strip()
        self.config["llm"]["api_key"] = self.llm_api_key.text().strip()
        self.config["llm"]["model"] = self.llm_model.text().strip()

        self.config["image"]["provider"] = self.img_provider.currentText()
        self.config["image"]["base_url"] = self.img_base_url.text().strip()
        self.config["image"]["api_key"] = self.img_api_key.text().strip()
        self.config["image"]["model"] = self.img_model.text().strip()
        self.config["image"]["size"] = self.img_size.currentText()
        self.config["image"]["quality"] = self.img_quality.currentText()
        self.config["image"]["workflow"] = self.comfy_workflow.text().strip()
        self.config["image"]["denoise"] = self.img_denoise.value()

        self.config["storyboard"]["frame_count"] = self.sb_frames.value()
        self.config["storyboard"]["duration"] = self.sb_duration.value()

        if "product" not in self.config:
            self.config["product"] = {}
        self.config["product"]["directory"] = self.prod_dir.text().strip()

        if "cache" not in self.config:
            self.config["cache"] = {}
        self.config["cache"]["max_versions"] = self.cache_max.value()

        save_config(self.config)
        self.accept()
