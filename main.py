"""StoryFrame - 分镜图生成器入口"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor
from PySide6.QtCore import Qt
from ui.main_window import MainWindow
from config import load_config, OUTPUT_DIR


def create_splash():
    """创建启动画面"""
    splash = QSplashScreen()
    splash.setStyleSheet("""
        QSplashScreen {
            background: #2c3e50;
        }
    """)
    # 绘制文字
    painter = QPainter(splash)
    painter.setPen(QColor("#ecf0f1"))
    font = QFont("Arial", 24, QFont.Bold)
    painter.setFont(font)
    painter.drawText(splash.rect(), Qt.AlignCenter, "StoryFrame\n分镜图生成器")
    painter.end()
    splash.show()
    return splash


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("StoryFrame")

    # 启动画面
    splash = create_splash()
    app.processEvents()

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 主窗口
    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
