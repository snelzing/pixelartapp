import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from app_window import MainWindow


from themes import light_palette


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Pixel Art Studio")
    app.setOrganizationName("PixelArtApp")

    app.setPalette(light_palette())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
