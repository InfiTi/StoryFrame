import sys
sys.path.insert(0, ".")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from pathlib import Path

app = QApplication(sys.argv)
view = QWebEngineView()
view.setUrl(QUrl.fromLocalFile(str(Path("docs/layout_preview.html").resolve())))
view.resize(900, 1600)

def capture():
    img = view.grab()
    img.save("docs/layout_preview.png")
    print("Screenshot saved")
    app.quit()

QTimer.singleShot(2000, capture)
view.show()
app.exec()
