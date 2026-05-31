from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QComboBox, QDialogButtonBox,
    QFormLayout, QMessageBox,
)


class NewCanvasDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Canvas")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._width_spin = QSpinBox(); self._width_spin.setRange(1, 512); self._width_spin.setValue(32)
        self._height_spin = QSpinBox(); self._height_spin.setRange(1, 512); self._height_spin.setValue(32)
        form.addRow("Width:", self._width_spin)
        form.addRow("Height:", self._height_spin)
        layout.addLayout(form)

        self._presets = QComboBox()
        self._presets.addItems([
            "Custom", "16×16", "32×32", "48×48", "64×64",
            "128×128", "256×256", "16×32", "32×64",
        ])
        self._presets.currentTextChanged.connect(self._on_preset)
        form.addRow("Preset:", self._presets)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_preset(self, text: str):
        if text == "Custom":
            return
        parts = text.split("×")
        if len(parts) == 2:
            w, h = parts[0], parts[1]
            if w.isdigit() and h.isdigit():
                self._width_spin.setValue(int(w))
                self._height_spin.setValue(int(h))

    @property
    def canvas_width(self) -> int:
        return self._width_spin.value()

    @property
    def canvas_height(self) -> int:
        return self._height_spin.value()


class ResizeDialog(QDialog):
    def __init__(self, current_w: int, current_h: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resize Canvas")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._width_spin = QSpinBox(); self._width_spin.setRange(1, 512); self._width_spin.setValue(current_w)
        self._height_spin = QSpinBox(); self._height_spin.setRange(1, 512); self._height_spin.setValue(current_h)
        form.addRow("Width:", self._width_spin)
        form.addRow("Height:", self._height_spin)

        self._anchor = QComboBox()
        self._anchor.addItems(["Top-Left", "Center", "Bottom-Right"])
        form.addRow("Anchor:", self._anchor)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def canvas_width(self) -> int:
        return self._width_spin.value()

    @property
    def canvas_height(self) -> int:
        return self._height_spin.value()

    @property
    def anchor(self) -> str:
        return self._anchor.currentText().lower()
