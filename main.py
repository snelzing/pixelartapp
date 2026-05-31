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
    palette.setColor(QPalette.Window, QColor("#FFFFFF"))
    palette.setColor(QPalette.WindowText, QColor("#000000"))
    palette.setColor(QPalette.Base, QColor("#F0F0F0"))
    palette.setColor(QPalette.AlternateBase, QColor("#E0E0E0"))
    palette.setColor(QPalette.ToolTipBase, QColor("#FFFFDC"))
    palette.setColor(QPalette.ToolTipText, QColor("#000000"))
    palette.setColor(QPalette.Text, QColor("#000000"))
    palette.setColor(QPalette.Button, QColor("#E0E0E0"))
    palette.setColor(QPalette.ButtonText, QColor("#000000"))
    palette.setColor(QPalette.Highlight, QColor("#4A9"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
