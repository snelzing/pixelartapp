from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QListWidget, QListWidgetItem,
    QSlider, QLabel, QColorDialog, QLineEdit,
    QFrame, QScrollArea, QComboBox, QSpinBox,
    QToolButton, QSizePolicy, QStackedWidget,
)


class ColorSwatch(QFrame):
    clicked = Signal()

    def __init__(self, color: QColor, size: int = 24):
        super().__init__()
        self._color = color
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._selected = False
        self._update_style()

    def _update_style(self):
        r, g, b = self._color.red(), self._color.green(), self._color.blue()
        border = "2px solid white" if self._selected else "1px solid #666"
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            f"border: {border}; "
            f"border-radius: 2px;"
        )

    def set_selected(self, sel: bool):
        self._selected = sel
        self._update_style()

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, c: QColor):
        self._color = c
        self._update_style()

    def mousePressEvent(self, event):
        self.clicked.emit()


class ColorPalette(QWidget):
    color_changed = Signal(QColor)

    PRESETS = [
        0x000000, 0xFFFFFF, 0xFF0000, 0x00FF00, 0x0000FF,
        0xFFFF00, 0xFF00FF, 0x00FFFF, 0x800000, 0x008000,
        0x000080, 0x808000, 0x800080, 0x008080, 0x808080,
        0xC0C0C0, 0xFF8800, 0x88FF00, 0x0088FF, 0xFF0088,
        0x8800FF, 0x00FF88, 0x444444, 0xAA4444, 0x44AA44,
        0x4444AA, 0xAAAA44, 0xAA44AA, 0x44AAAA, 0xAAAAAA,
        0x663300, 0x996633, 0xCC9933, 0xFFCC66, 0xFF9966,
        0xFF6633, 0xCC3300, 0x993300, 0x660000, 0x330000,
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Palette")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._current_color_btn = QPushButton()
        self._current_color_btn.setFixedHeight(30)
        self._current_color_btn.setToolTip("Click to pick a custom color")
        self._current_color_btn.clicked.connect(self._pick_color)
        layout.addWidget(self._current_color_btn)

        grid = QGridLayout()
        grid.setSpacing(2)
        self._swatches: list[ColorSwatch] = []
        cols = 8
        for i, hex_val in enumerate(self.PRESETS):
            c = QColor(hex_val)
            sw = ColorSwatch(c)
            sw.setToolTip(f"#{c.red():02X}{c.green():02X}{c.blue():02X}")
            sw.clicked.connect(lambda checked=False, color=c: self._on_swatch_click(color))
            self._swatches.append(sw)
            grid.addWidget(sw, i // cols, i % cols)

        layout.addLayout(grid)
        layout.addStretch()
        self._update_color_btn(QColor(0, 0, 0))

    def _on_swatch_click(self, color: QColor):
        self.color_changed.emit(color)

    def _pick_color(self):
        color = QColorDialog.getColor(self._current_color)
        if color.isValid():
            self.color_changed.emit(color)

    def set_current_color(self, color: QColor):
        self._update_color_btn(color)

    def _update_color_btn(self, color: QColor):
        self._current_color = color
        r, g, b = color.red(), color.green(), color.blue()
        text_color = "white" if (r * 0.299 + g * 0.587 + b * 0.114) < 128 else "black"
        self._current_color_btn.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); color: {text_color}; "
            f"border: 1px solid #555; border-radius: 3px; font-weight: bold;"
        )
        self._current_color_btn.setText(f"#{r:02X}{g:02X}{b:02X}")


class LayerPanel(QWidget):
    add_requested = Signal()
    delete_requested = Signal()
    merge_down_requested = Signal()
    duplicate_requested = Signal()
    move_up_requested = Signal()
    move_down_requested = Signal()
    visibility_toggled = Signal(int, bool)
    opacity_changed = Signal(int, float)
    layer_selected = Signal(int)
    layer_renamed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Layers")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QHBoxLayout()
        self._btn_add = QToolButton(); self._btn_add.setText("+"); self._btn_add.setToolTip("Add layer"); self._btn_add.clicked.connect(self.add_requested)
        self._btn_dup = QToolButton(); self._btn_dup.setText("⧉"); self._btn_dup.setToolTip("Duplicate layer"); self._btn_dup.clicked.connect(self.duplicate_requested)
        self._btn_del = QToolButton(); self._btn_del.setText("−"); self._btn_del.setToolTip("Delete layer"); self._btn_del.clicked.connect(self.delete_requested)
        self._btn_merge = QToolButton(); self._btn_merge.setText("⇣"); self._btn_merge.setToolTip("Merge down"); self._btn_merge.clicked.connect(self.merge_down_requested)
        self._btn_up = QToolButton(); self._btn_up.setText("↑"); self._btn_up.setToolTip("Move layer up"); self._btn_up.clicked.connect(self.move_up_requested)
        self._btn_down = QToolButton(); self._btn_down.setText("↓"); self._btn_down.setToolTip("Move layer down"); self._btn_down.clicked.connect(self.move_down_requested)
        for btn in [self._btn_add, self._btn_dup, self._btn_del, self._btn_merge, self._btn_up, self._btn_down]:
            btn.setFixedSize(26, 26)
            toolbar.addWidget(btn)

        layout.addLayout(toolbar)

        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.InternalMove)
        self._list.setToolTip("Drag to reorder layers. [V] = visible, [L] = locked")
        self._list.currentRowChanged.connect(self._on_selection)
        self._list.model().rowsMoved.connect(self._on_reorder)
        layout.addWidget(self._list)

        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.setToolTip("Layer opacity")
        self._opacity_slider.valueChanged.connect(self._on_opacity)
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        opacity_layout.addWidget(self._opacity_slider)
        layout.addLayout(opacity_layout)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Layer name")
        self._name_edit.setToolTip("Rename selected layer")
        self._name_edit.editingFinished.connect(self._on_rename)
        layout.addWidget(self._name_edit)

        self._items_by_index: dict[int, QListWidgetItem] = {}

    def _on_selection(self, row: int):
        if row >= 0:
            self.layer_selected.emit(row)
            self._update_name_edit(row)

    def _on_reorder(self):
        self.move_up_requested.emit()

    def _on_opacity(self, val: int):
        row = self._list.currentRow()
        if row >= 0:
            self.opacity_changed.emit(len(self._items_by_index) - 1 - row, val / 100.0)

    def _on_rename(self):
        row = self._list.currentRow()
        if row >= 0:
            self.layer_renamed.emit(len(self._items_by_index) - 1 - row, self._name_edit.text())

    def _update_name_edit(self, row: int):
        item = self._list.item(row)
        if item:
            self._name_edit.setText(item.text())

    def update_layers(self, layers: list, active_idx: int):
        self._list.blockSignals(True)
        self._list.clear()
        self._items_by_index.clear()

        displayed = list(reversed(layers))
        for i, layer in enumerate(displayed):
            item = QListWidgetItem(layer.name)
            flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled
            item.setFlags(flags)
            vis = "V" if layer.visible else " "
            lock = "L" if layer.locked else " "
            item.setText(f"[{vis}] [{lock}] {layer.name}")
            self._list.addItem(item)
            self._items_by_index[len(layers) - 1 - i] = item

        rev_idx = len(layers) - 1 - active_idx
        if 0 <= rev_idx < self._list.count():
            self._list.setCurrentRow(rev_idx)

        self._list.blockSignals(False)
        self._update_name_edit(rev_idx)

    def set_opacity(self, opacity: float):
        self._opacity_slider.blockSignals(True)
        self._opacity_slider.setValue(int(opacity * 100))
        self._opacity_slider.blockSignals(False)


class FrameThumbnail(QFrame):
    clicked = Signal(int)
    def __init__(self, index: int, pixmap: QPixmap):
        super().__init__()
        self.index = index
        self._selected = False
        self.setToolTip(f"Frame {index + 1}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self._label = QLabel()
        self._label.setFixedSize(48, 48)
        self._label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.FastTransformation))
        self._label.setAlignment(Qt.AlignCenter)
        self._index_label = QLabel(str(index + 1))
        self._index_label.setAlignment(Qt.AlignCenter)
        self._index_label.setStyleSheet("font-size: 9px; color: #888;")
        layout.addWidget(self._label)
        layout.addWidget(self._index_label)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(60)

    def set_selected(self, sel: bool):
        self._selected = sel
        border = "2px solid #4A9" if sel else "1px solid #444"
        self.setStyleSheet(f"background: #2A2A2A; border: {border}; border-radius: 3px;")

    def update_pixmap(self, pixmap: QPixmap):
        self._label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.FastTransformation))

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)


class AnimationPanel(QWidget):
    goto_frame_requested = Signal(int)
    add_frame_requested = Signal()
    delete_frame_requested = Signal()
    duplicate_frame_requested = Signal()
    play_toggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Animation")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QHBoxLayout()
        self._btn_add = QToolButton(); self._btn_add.setText("+"); self._btn_add.setToolTip("Add frame"); self._btn_add.clicked.connect(self.add_frame_requested)
        self._btn_dup = QToolButton(); self._btn_dup.setText("⧉"); self._btn_dup.setToolTip("Duplicate frame"); self._btn_dup.clicked.connect(self.duplicate_frame_requested)
        self._btn_del = QToolButton(); self._btn_del.setText("−"); self._btn_del.setToolTip("Delete frame"); self._btn_del.clicked.connect(self.delete_frame_requested)
        self._btn_play = QToolButton(); self._btn_play.setText("▶"); self._btn_play.setCheckable(True); self._btn_play.setToolTip("Play / Stop"); self._btn_play.clicked.connect(self._on_play)
        for btn in [self._btn_add, self._btn_dup, self._btn_del, self._btn_play]:
            btn.setFixedSize(26, 26)
            toolbar.addWidget(btn)

        toolbar.addWidget(QLabel("FPS:"))
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 60)
        self._fps_spin.setValue(12)
        self._fps_spin.setToolTip("Frames per second")
        toolbar.addWidget(self._fps_spin)

        self._onion_cb = QComboBox()
        self._onion_cb.addItems(["Off", "1 Before", "2 Before", "1+1", "1 Before+After"])
        self._onion_cb.currentIndexChanged.connect(self._on_onion_change)
        self._onion_cb.setToolTip("Onion skinning: show previous/next frames as overlay")
        toolbar.addWidget(QLabel("Onion:"))
        toolbar.addWidget(self._onion_cb)

        layout.addLayout(toolbar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setMaximumHeight(100)

        self._frames_widget = QWidget()
        self._frames_layout = QHBoxLayout(self._frames_widget)
        self._frames_layout.setContentsMargins(4, 4, 4, 4)
        self._frames_layout.setSpacing(4)
        self._frames_layout.addStretch()
        self._scroll.setWidget(self._frames_widget)
        layout.addWidget(self._scroll)

        self._thumbnails: list[FrameThumbnail] = []

    def _on_play(self):
        self.play_toggled.emit()

    def set_playing(self, playing: bool):
        self._btn_play.setChecked(playing)
        self._btn_play.setText("⏹" if playing else "▶")

    def _on_onion_change(self, idx: int):
        pass  # handled by main window

    def onion_mode(self) -> tuple:
        idx = self._onion_cb.currentIndex()
        return {
            0: (False, 0, 0),
            1: (True, 1, 0),
            2: (True, 2, 0),
            3: (True, 1, 0),
            4: (True, 1, 1),
        }.get(idx, (False, 0, 0))

    def update_frames(self, frames_count: int, active_frame: int, get_thumb_fn):
        self._thumbnails.clear()
        while self._frames_layout.count():
            item = self._frames_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for i in range(frames_count):
            thumb = get_thumb_fn(i)
            ft = FrameThumbnail(i, thumb)
            ft.clicked.connect(lambda idx, i=i: self.goto_frame_requested.emit(i))
            ft.set_selected(i == active_frame)
            self._thumbnails.append(ft)
            self._frames_layout.addWidget(ft)

        self._frames_layout.addStretch()
