from PySide6.QtGui import QColor, QPalette


def light_palette():
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#FFFFFF"))
    p.setColor(QPalette.WindowText, QColor("#000000"))
    p.setColor(QPalette.Base, QColor("#F0F0F0"))
    p.setColor(QPalette.AlternateBase, QColor("#E0E0E0"))
    p.setColor(QPalette.ToolTipBase, QColor("#FFFFDC"))
    p.setColor(QPalette.ToolTipText, QColor("#000000"))
    p.setColor(QPalette.Text, QColor("#000000"))
    p.setColor(QPalette.Button, QColor("#E0E0E0"))
    p.setColor(QPalette.ButtonText, QColor("#000000"))
    p.setColor(QPalette.Highlight, QColor("#4A9"))
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    return p


def dark_palette():
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#2D2D2D"))
    p.setColor(QPalette.WindowText, QColor("#E0E0E0"))
    p.setColor(QPalette.Base, QColor("#1E1E1E"))
    p.setColor(QPalette.AlternateBase, QColor("#353535"))
    p.setColor(QPalette.ToolTipBase, QColor("#353535"))
    p.setColor(QPalette.ToolTipText, QColor("#E0E0E0"))
    p.setColor(QPalette.Text, QColor("#E0E0E0"))
    p.setColor(QPalette.Button, QColor("#353535"))
    p.setColor(QPalette.ButtonText, QColor("#E0E0E0"))
    p.setColor(QPalette.Highlight, QColor("#4A9"))
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    return p
