import os
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QByteArray
from PySide6.QtGui import (
    QAction, QColor, QImage, QKeySequence, QPixmap,
    QIcon, QPainter, QFont, QPen, QActionGroup,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QToolBar, QMenuBar, QMenu, QFileDialog,
    QMessageBox, QLabel, QScrollArea, QFrame, QSizePolicy,
    QToolButton, QButtonGroup, QApplication, QStatusBar,
    QSplitter, QDockWidget, QStackedWidget,
)
from PySide6.QtGui import QActionGroup
from pixel_canvas import PixelCanvas, Symmetry
from tools import TOOLS, Tool
from widgets import ColorPalette, LayerPanel, AnimationPanel
from dialogs import NewCanvasDialog, ResizeDialog
import updater


class ToolButton(QToolButton):
    def __init__(self, tool_cls, parent=None):
        super().__init__(parent)
        self.tool_cls = tool_cls
        tool = tool_cls()
        self.setText(tool.icon_char)
        self.setToolTip(tool.name)
        self.setCheckable(True)
        self.setFixedSize(32, 32)
        font = self.font()
        font.setPointSize(14)
        self.setFont(font)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pixel Art Studio")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        self._canvas = PixelCanvas()
        self._current_tool_index = 0
        self._file_path = None
        self._modified = False

        self._setup_tools()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_docks()
        self._setup_central()
        self._setup_statusbar()

        self._connect_signals()
        self._update_title()
        self._update_tool_buttons()
        self._update_color_indicator(QColor(0, 0, 0))
        self._update_layer_panel()
        self._update_frame_panel()

    def _setup_tools(self):
        self._tools = [cls() for cls in TOOLS]
        self._canvas.set_tool(self._tools[0])

    def _setup_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._act_new = QAction("&New...", self, shortcut=QKeySequence.New, triggered=self._on_new)
        self._act_open = QAction("&Open...", self, shortcut=QKeySequence.Open, triggered=self._on_open)
        self._act_save = QAction("&Save", self, shortcut=QKeySequence.Save, triggered=self._on_save)
        self._act_save_as = QAction("Save &As...", self, shortcut=QKeySequence.SaveAs, triggered=self._on_save_as)
        self._act_export = QAction("&Export PNG...", self, shortcut="Ctrl+Shift+E", triggered=self._on_export)
        file_menu.addActions([self._act_new, self._act_open, self._act_save, self._act_save_as, self._act_export])

        edit_menu = menubar.addMenu("&Edit")
        self._act_undo = QAction("&Undo", self, shortcut=QKeySequence.Undo, triggered=self._canvas.undo)
        self._act_redo = QAction("&Redo", self, shortcut=QKeySequence.Redo, triggered=self._canvas.redo)
        edit_menu.addActions([self._act_undo, self._act_redo])

        layer_menu = menubar.addMenu("&Layer")
        layer_menu.addAction("Add Layer", self._canvas.add_layer, shortcut="Ctrl+Shift+N")
        layer_menu.addAction("Duplicate Layer", self._canvas.duplicate_frame, shortcut="Ctrl+Shift+D")
        layer_menu.addAction("Merge Down", self._canvas.merge_layer_down, shortcut="Ctrl+Shift+M")
        layer_menu.addAction("Clear Layer", self._canvas.clear_layer, shortcut="Ctrl+Shift+C")
        layer_menu.addSeparator()
        layer_menu.addAction("Flip Horizontal", lambda: self._canvas.flip_layer_horizontal())
        layer_menu.addAction("Flip Vertical", lambda: self._canvas.flip_layer_vertical())

        canvas_menu = menubar.addMenu("&Canvas")
        canvas_menu.addAction("&Resize...", self._on_resize, shortcut="Ctrl+Alt+R")
        canvas_menu.addSeparator()
        self._act_grid = QAction("Show &Grid", self, checkable=True, shortcut="Ctrl+G")
        self._act_grid.setChecked(True)
        self._act_grid.toggled.connect(lambda v: setattr(self._canvas, 'show_grid', v))
        canvas_menu.addAction(self._act_grid)

        sym_menu = menubar.addMenu("S&ymmetry")
        sym_group = QActionGroup(self)
        sym_modes = [("None", Symmetry.NONE), ("Horizontal", Symmetry.HORIZONTAL),
                     ("Vertical", Symmetry.VERTICAL), ("Both", Symmetry.BOTH)]
        self._sym_actions = {}
        for name, mode in sym_modes:
            act = QAction(name, self, checkable=True)
            if mode == Symmetry.NONE:
                act.setChecked(True)
            act.triggered.connect(lambda checked=False, m=mode: self._canvas.set_symmetry(m))
            sym_group.addAction(act)
            sym_menu.addAction(act)
            self._sym_actions[mode] = act

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Zoom &In", self._canvas.zoom_in, shortcut=QKeySequence.ZoomIn)
        view_menu.addAction("Zoom &Out", self._canvas.zoom_out, shortcut=QKeySequence.ZoomOut)
        view_menu.addAction("Zoom to &Fit", self._canvas.zoom_fit, shortcut="Ctrl+0")

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&Check for Updates", self._on_check_updates)
        help_menu.addAction("&About", self._on_about)

    def _setup_toolbar(self):
        toolbar = QToolBar("Tools")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_buttons = []
        for i, tool_cls in enumerate(TOOLS):
            btn = ToolButton(tool_cls)
            btn.clicked.connect(lambda checked=False, idx=i: self._on_tool_select(idx))
            self._tool_group.addButton(btn, i)
            self._tool_buttons.append(btn)
            toolbar.addWidget(btn)

        toolbar.addSeparator()
        self._swap_btn = QToolButton()
        self._swap_btn.setText("⇄")
        self._swap_btn.setToolTip("Swap Colors")
        self._swap_btn.setFixedSize(32, 32)
        self._swap_btn.clicked.connect(self._canvas.swap_colors)
        toolbar.addWidget(self._swap_btn)

        self._color_indicator = QFrame()
        self._color_indicator.setFixedSize(32, 32)
        self._color_indicator.setStyleSheet("background-color: #000000; border: 2px solid #888; border-radius: 3px;")
        toolbar.addWidget(self._color_indicator)

    def _setup_docks(self):
        self._palette = ColorPalette()
        pal_dock = QDockWidget("Palette", self)
        pal_dock.setWidget(self._palette)
        self.addDockWidget(Qt.RightDockWidgetArea, pal_dock)

        self._layer_panel = LayerPanel()
        layer_dock = QDockWidget("Layers", self)
        layer_dock.setWidget(self._layer_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, layer_dock)

        self._anim_panel = AnimationPanel()
        anim_dock = QDockWidget("Animation", self)
        anim_dock.setWidget(self._anim_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, anim_dock)

    def _setup_central(self):
        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("QScrollArea { background-color: #1E1E1E; border: none; }")
        self._canvas.setStyleSheet("background-color: #2D2D2D;")
        self.setCentralWidget(scroll)

    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self._status_label = QLabel("Ready")
        self._statusbar.addWidget(self._status_label)
        self._pos_label = QLabel("")
        self._statusbar.addPermanentWidget(self._pos_label)
        self._size_label = QLabel("32×32")
        self._statusbar.addPermanentWidget(self._size_label)
        self._version_label = QLabel(f"v{updater.get_current_version()}")
        self._version_label.setStyleSheet("padding: 0 8px; color: #888;")
        self._statusbar.addPermanentWidget(self._version_label)
        self.setStatusBar(self._statusbar)

    def _connect_signals(self):
        self._palette.color_changed.connect(lambda c: setattr(self._canvas, 'current_color', c))
        self._canvas.color_changed.connect(self._palette.set_current_color)
        self._canvas.color_changed.connect(self._update_color_indicator)

        self._layer_panel.add_requested.connect(self._canvas.add_layer)
        self._layer_panel.delete_requested.connect(lambda: self._canvas.delete_layer())
        self._layer_panel.merge_down_requested.connect(self._canvas.merge_layer_down)
        self._layer_panel.duplicate_requested.connect(self._canvas.duplicate_frame)
        self._layer_panel.layer_selected.connect(self._on_layer_selected)
        self._layer_panel.opacity_changed.connect(self._canvas.set_layer_opacity)
        self._layer_panel.layer_renamed.connect(self._canvas.rename_layer)
        self._layer_panel.move_up_requested.connect(self._on_layer_move_up)
        self._layer_panel.move_down_requested.connect(self._on_layer_move_down)
        self._canvas.layers_changed.connect(self._update_layer_panel)

        self._anim_panel.goto_frame_requested.connect(self._canvas.goto_frame)
        self._anim_panel.add_frame_requested.connect(self._canvas.add_frame)
        self._anim_panel.delete_frame_requested.connect(self._canvas.delete_frame)
        self._anim_panel.duplicate_frame_requested.connect(self._canvas.duplicate_frame)
        self._anim_panel.play_toggled.connect(self._on_play_toggle)
        self._anim_panel._fps_spin.valueChanged.connect(self._canvas.set_fps)
        self._anim_panel._onion_cb.currentIndexChanged.connect(self._update_onion)

        self._canvas.layers_changed.connect(self._update_frame_panel)
        self._canvas.layers_changed.connect(self._on_modified)

    def _on_tool_select(self, idx: int):
        self._current_tool_index = idx
        self._canvas.set_tool(self._tools[idx])

    def _update_tool_buttons(self):
        if self._tool_buttons:
            self._tool_buttons[self._current_tool_index].setChecked(True)

    def _update_color_indicator(self, color: QColor):
        r, g, b = color.red(), color.green(), color.blue()
        self._color_indicator.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 2px solid #888; border-radius: 3px;"
        )

    def _update_layer_panel(self):
        self._layer_panel.update_layers(self._canvas.layers, self._canvas.active_layer_index)

    def _update_frame_panel(self):
        canvas = self._canvas
        saved_frame = canvas._active_frame
        saved_layers = [l.copy() for l in canvas._layers]

        def get_thumb(idx):
            if idx < len(canvas._frames):
                layers = canvas._frames[idx]
                img = QImage(canvas.grid_width, canvas.grid_height, QImage.Format_ARGB32_Premultiplied)
                img.fill(Qt.transparent)
                for layer in layers:
                    if layer.visible:
                        p = QPainter(img)
                        p.setOpacity(layer.opacity)
                        p.drawImage(0, 0, layer.image)
                        p.end()
                return QPixmap.fromImage(img)
            return QPixmap(canvas.grid_width, canvas.grid_height)

        self._anim_panel.update_frames(canvas.frame_count(), saved_frame, get_thumb)

        canvas._layers = saved_layers
        canvas._composite_dirty = True
        canvas._active_frame = saved_frame
        canvas.update()
        self._size_label.setText(f"{canvas.grid_width}×{canvas.grid_height}")

    def _update_onion(self):
        on, before, after = self._anim_panel.onion_mode()
        self._canvas._onion_skin = on
        self._canvas._onion_before = before
        self._canvas._onion_after = after
        self._canvas.update()

    def _on_layer_move_up(self):
        idx = self._canvas.active_layer_index
        if idx < len(self._canvas.layers) - 1:
            self._canvas.move_layer(idx, idx + 1)

    def _on_layer_move_down(self):
        idx = self._canvas.active_layer_index
        if idx > 0:
            self._canvas.move_layer(idx, idx - 1)

    def _on_play_toggle(self):
        self._canvas.play_animation()
        self._anim_panel.set_playing(self._canvas.is_playing)

    def _on_layer_selected(self, idx: int):
        self._canvas.active_layer_index = idx

    def _on_modified(self):
        self._modified = True
        self._update_title()

    def _update_title(self):
        name = self._file_path or "Untitled"
        modified = " *" if self._modified else ""
        self.setWindowTitle(f"Pixel Art Studio - {name}{modified}")

    def _on_new(self):
        dlg = NewCanvasDialog(self)
        if dlg.exec():
            self._canvas.new_canvas(dlg.canvas_width, dlg.canvas_height)
            self._file_path = None
            self._modified = False
            self._update_title()
            self._update_layer_panel()
            self._update_frame_panel()

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp);;All Files (*)")
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, "Error", "Could not load image.")
            return
        self._canvas.new_canvas(img.width(), img.height())
        self._canvas.layers[0].image = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        self._canvas._composite_dirty = True
        self._canvas.update()
        self._canvas._save_frame_state()
        self._file_path = path
        self._modified = False
        self._update_title()
        self._update_layer_panel()
        self._update_frame_panel()

    def _on_save(self):
        if self._file_path:
            self._export_png(self._file_path)
            self._modified = False
            self._update_title()
        else:
            self._on_save_as()

    def _on_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG (*.png);;All Files (*)")
        if not path:
            return
        self._file_path = path
        self._on_save()

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "", "PNG (*.png)")
        if not path:
            return
        self._export_png(path)

    def _export_png(self, path: str):
        img = self._canvas.get_composite()
        img.save(path, "PNG")

    def _on_resize(self):
        dlg = ResizeDialog(self._canvas.grid_width, self._canvas.grid_height, self)
        if dlg.exec():
            self._canvas.resize_canvas(dlg.canvas_width, dlg.canvas_height, dlg.anchor)

    def _on_check_updates(self):
        current = updater.get_current_version()
        remote = updater.check_remote_version("BrockCade", "pixelartapp")
        if remote is None:
            QMessageBox.information(self, "Check for Updates",
                                    f"Current version: v{current}\n\nCould not check for updates. "
                                    "Make sure you have an internet connection and gh CLI installed.")
            return

        if remote == current:
            QMessageBox.information(self, "Check for Updates",
                                    f"Current version: v{current}\n\nYou're up to date!")
            return

        result = QMessageBox.question(
            self, "Update Available",
            f"Current version: v{current}\nLatest version: v{remote}\n\nUpdate now?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if result == QMessageBox.Yes:
            status = updater.apply_update()
            if status and status.get("success"):
                QMessageBox.information(self, "Update Complete",
                                        f"Updated to v{status.get('version', remote)}. Restarting...")
                updater.restart_app()
            else:
                QMessageBox.warning(self, "Update Failed",
                                    f"Could not apply update.\n{status.get('error', 'Unknown error')}")

    def _on_about(self):
        QMessageBox.about(self, "About Pixel Art Studio",
                          f"<b>Pixel Art Studio</b> v{updater.get_current_version()}<br><br>"
                          "A pixel art painting tool built with PySide6.<br><br>"
                          "Features: layers, animation, symmetry, onion skinning, and more.")

    def closeEvent(self, event):
        if self._modified:
            result = QMessageBox.question(
                self, "Unsaved Changes",
                "Save changes before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if result == QMessageBox.Save:
                self._on_save()
                event.accept()
            elif result == QMessageBox.Cancel:
                event.ignore()
            else:
                event.accept()
        else:
            event.accept()



