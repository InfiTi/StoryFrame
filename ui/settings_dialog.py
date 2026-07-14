"""设置对话框"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QGroupBox, QMessageBox,
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
        self.img_provider.addItems(["dalle", "flux", "sd"])
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

        # === 按钮 ===
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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

        self.config["storyboard"]["frame_count"] = self.sb_frames.value()
        self.config["storyboard"]["duration"] = self.sb_duration.value()

        save_config(self.config)
        self.accept()
