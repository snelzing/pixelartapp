import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from app_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Pixel Art Studio")
    app.setOrganizationName("PixelArtApp")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#2D2D2D"))
    palette.setColor(QPalette.WindowText, QColor("#E0E0E0"))
    palette.setColor(QPalette.Base, QColor("#1E1E1E"))
    palette.setColor(QPalette.AlternateBase, QColor("#353535"))
    palette.setColor(QPalette.ToolTipBase, QColor("#353535"))
    palette.setColor(QPalette.ToolTipText, QColor("#E0E0E0"))
    palette.setColor(QPalette.Text, QColor("#E0E0E0"))
    palette.setColor(QPalette.Button, QColor("#353535"))
    palette.setColor(QPalette.ButtonText, QColor("#E0E0E0"))
    palette.setColor(QPalette.Highlight, QColor("#4A9"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
