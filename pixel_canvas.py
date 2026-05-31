from __future__ import annotations
from enum import Enum, auto
from typing import Optional
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class Symmetry(Enum):
    NONE = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()
    BOTH = auto()


class Layer:
    def __init__(self, name: str, width: int, height: int, color: QColor = Qt.transparent):
        self.name = name
        self.image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        self.image.fill(color)
        self.visible = True
        self.opacity = 1.0
        self.locked = False

    def copy(self) -> Layer:
        layer = Layer(self.name, self.image.width(), self.image.height())
        layer.image = self.image.copy()
        layer.visible = self.visible
        layer.opacity = self.opacity
        layer.locked = self.locked
        return layer


class PixelCanvas(QWidget):
    color_changed = Signal(QColor)
    status_message = Signal(str)
    layers_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid_w = 32
        self._grid_h = 32
        self._zoom = 12
        self._show_grid = True
        self._pixel_pen_size = 1

        self._layers: list[Layer] = []
        self._active_layer_index = 0

        self._fps = 12
        self._frames: list[list[Layer]] = []
        self._active_frame = 0
        self._onion_skin = False
        self._onion_before = 1
        self._onion_after = 0
        self._playing = False
        self._play_timer = None

        self._current_color = QColor(0, 0, 0)
        self._secondary_color = QColor(255, 255, 255)
        self._symmetry = Symmetry.NONE

        self._tool = None
        self._mouse_down = False
        self._mouse_pixel = QPoint(-1, -1)
        self._snapshot = None
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 50
        self._drawing = False

        self._composite = QImage()
        self._composite_dirty = True
        self._hover_pixel = QPoint(-1, -1)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip("Canvas — scroll to zoom, click to draw")

        self.new_canvas(32, 32)

    # --- Canvas management ---

    def new_canvas(self, width: int, height: int):
        self._grid_w = width
        self._grid_h = height
        self._frames = []
        self._active_frame = 0
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._layers = [Layer("Layer 1", width, height)]
        self._active_layer_index = 0
        self._frames.append([l.copy() for l in self._layers])
        self._composite = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        self._composite_dirty = True
        self.updateGeometry()
        self.update()
        self.layers_changed.emit()

    def resize_canvas(self, new_width: int, new_height: int, anchor: str = "top-left"):
        for layer in self._layers:
            new_img = QImage(new_width, new_height, QImage.Format_ARGB32_Premultiplied)
            new_img.fill(Qt.transparent)
            painter = QPainter(new_img)
            ox = 0 if anchor in ("top-left", "bottom-left") else (new_width - self._grid_w) // 2 if "center" in anchor else new_width - self._grid_w
            oy = 0 if anchor in ("top-left", "top-right", "top-center") else (new_height - self._grid_h) // 2 if "center" in anchor or "middle" in anchor else new_height - self._grid_h
            painter.drawImage(ox, oy, layer.image)
            painter.end()
            layer.image = new_img
        self._grid_w = new_width
        self._grid_h = new_height
        self._composite = QImage(new_width, new_height, QImage.Format_ARGB32_Premultiplied)
        self._composite_dirty = True
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._save_frame_state()
        self.updateGeometry()
        self.update()
        self.layers_changed.emit()

    # --- Layer management ---

    def add_layer(self, name: str = None):
        if name is None:
            name = f"Layer {len(self._layers) + 1}"
        layer = Layer(name, self._grid_w, self._grid_h)
        self._layers.insert(self._active_layer_index + 1, layer)
        self._active_layer_index += 1
        self._composite_dirty = True
        self._save_frame_state()
        self.update()
        self.layers_changed.emit()

    def delete_layer(self, index: int = None):
        if index is None:
            index = self._active_layer_index
        if len(self._layers) <= 1:
            return
        self._layers.pop(index)
        self._active_layer_index = min(max(0, index - 1), len(self._layers) - 1)
        self._composite_dirty = True
        self._save_frame_state()
        self.update()
        self.layers_changed.emit()

    def move_layer(self, from_idx: int, to_idx: int):
        if from_idx == to_idx:
            return
        layer = self._layers.pop(from_idx)
        self._layers.insert(to_idx, layer)
        self._active_layer_index = to_idx
        self._composite_dirty = True
        self._save_frame_state()
        self.update()
        self.layers_changed.emit()

    def set_layer_visible(self, index: int, visible: bool):
        if 0 <= index < len(self._layers):
            self._layers[index].visible = visible
            self._composite_dirty = True
            self.update()
            self.layers_changed.emit()

    def set_layer_opacity(self, index: int, opacity: float):
        if 0 <= index < len(self._layers):
            self._layers[index].opacity = opacity
            self._composite_dirty = True
            self.update()
            self.layers_changed.emit()

    def set_layer_locked(self, index: int, locked: bool):
        if 0 <= index < len(self._layers):
            self._layers[index].locked = locked
            self.layers_changed.emit()

    def rename_layer(self, index: int, name: str):
        if 0 <= index < len(self._layers):
            self._layers[index].name = name
            self.layers_changed.emit()

    def merge_layer_down(self):
        if self._active_layer_index <= 0:
            return
        upper = self._active_layer_index
        lower = upper - 1
        painter = QPainter(self._layers[lower].image)
        painter.drawImage(0, 0, self._layers[upper].image)
        painter.end()
        self._layers.pop(upper)
        self._active_layer_index = lower
        self._composite_dirty = True
        self._save_frame_state()
        self.update()
        self.layers_changed.emit()

    @property
    def active_layer(self) -> Optional[Layer]:
        if 0 <= self._active_layer_index < len(self._layers):
            return self._layers[self._active_layer_index]
        return None

    @property
    def active_layer_index(self) -> int:
        return self._active_layer_index

    @active_layer_index.setter
    def active_layer_index(self, idx: int):
        self._active_layer_index = max(0, min(idx, len(self._layers) - 1))
        self.layers_changed.emit()

    @property
    def layers(self) -> list[Layer]:
        return self._layers

    # --- Animation ---

    def _save_frame_state(self):
        if self._active_frame < len(self._frames):
            self._frames[self._active_frame] = [l.copy() for l in self._layers]

    def _load_frame_state(self, frame_idx: int):
        layers = self._frames[frame_idx]
        self._layers = [l.copy() for l in layers]
        self._active_layer_index = min(self._active_layer_index, len(self._layers) - 1)
        self._composite_dirty = True
        self.layers_changed.emit()
        self.update()

    def add_frame(self):
        self._save_frame_state()
        new_idx = self._active_frame + 1
        self._frames.insert(new_idx, [l.copy() for l in self._layers])
        self._active_frame = new_idx
        self.update()

    def delete_frame(self):
        if len(self._frames) <= 1:
            return
        self._frames.pop(self._active_frame)
        self._active_frame = min(self._active_frame, len(self._frames) - 1)
        self._load_frame_state(self._active_frame)

    def duplicate_frame(self):
        self._save_frame_state()
        new_idx = self._active_frame + 1
        self._frames.insert(new_idx, [l.copy() for l in self._layers])
        self._active_frame = new_idx
        self.update()

    def goto_frame(self, idx: int):
        if idx < 0 or idx >= len(self._frames):
            return
        self._save_frame_state()
        self._active_frame = idx
        self._load_frame_state(idx)

    def next_frame(self):
        self.goto_frame((self._active_frame + 1) % len(self._frames))

    def prev_frame(self):
        self.goto_frame((self._active_frame - 1 + len(self._frames)) % len(self._frames))

    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def active_frame(self) -> int:
        return self._active_frame

    def set_fps(self, fps: int):
        self._fps = max(1, fps)

    def play_animation(self):
        if self._playing:
            self._playing = False
            if self._play_timer:
                self.killTimer(self._play_timer)
                self._play_timer = None
            return
        self._playing = True
        self._play_timer = self.startTimer(1000 // self._fps)

    @property
    def is_playing(self) -> bool:
        return self._playing

    # --- Symmetry ---

    def set_symmetry(self, mode: Symmetry):
        self._symmetry = mode

    def get_symmetric_points(self, x: int, y: int) -> list[QPoint]:
        points = [QPoint(x, y)]
        w, h = self._grid_w - 1, self._grid_h - 1
        if self._symmetry in (Symmetry.HORIZONTAL, Symmetry.BOTH):
            points.append(QPoint(w - x, y))
        if self._symmetry in (Symmetry.VERTICAL, Symmetry.BOTH):
            points.append(QPoint(x, h - y))
        if self._symmetry == Symmetry.BOTH:
            points.append(QPoint(w - x, h - y))
        return points

    # --- Composite rendering ---

    def rebuild_composite(self):
        self._composite.fill(Qt.transparent)
        for layer in self._layers:
            if layer.visible and layer.opacity > 0:
                painter = QPainter(self._composite)
                painter.setOpacity(layer.opacity)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.drawImage(0, 0, layer.image)
                painter.end()
        self._composite_dirty = False

    def get_composite(self) -> QImage:
        if self._composite_dirty:
            self.rebuild_composite()
        return self._composite

    def get_onion_composite(self) -> QImage:
        img = self.get_composite().copy()
        if not self._onion_skin:
            return img
        for offset in range(-self._onion_before, self._onion_after + 1):
            if offset == 0:
                continue
            frame_idx = self._active_frame + offset
            if 0 <= frame_idx < len(self._frames):
                painter = QPainter(img)
                painter.setOpacity(0.3)
                for layer in self._frames[frame_idx]:
                    if layer.visible:
                        painter.drawImage(0, 0, layer.image)
                painter.end()
        return img

    # --- Drawing ---

    def begin_draw(self):
        self._snapshot = self.active_layer.image.copy() if self.active_layer else None

    def end_draw(self):
        if self._snapshot is None:
            return
        after = self.active_layer.image.copy() if self.active_layer else None
        if after and self._snapshot != after:
            cmd = LayerSnapshotCommand(self._active_layer_index, self._snapshot, after, self._active_frame)
            self._undo_stack.append(cmd)
            self._redo_stack.clear()
            if len(self._undo_stack) > self._max_undo:
                self._undo_stack.pop(0)
            self._save_frame_state()
        self._snapshot = None

    def set_pixel(self, x: int, y: int, color: QColor):
        if not self.active_layer or self.active_layer.locked:
            return
        if 0 <= x < self._grid_w and 0 <= y < self._grid_h:
            self.active_layer.image.setPixelColor(x, y, color)
            self._composite_dirty = True

    def get_pixel(self, x: int, y: int) -> QColor:
        if 0 <= x < self._grid_w and 0 <= y < self._grid_h:
            return self.get_composite().pixelColor(x, y)
        return Qt.transparent

    def get_layer_pixel(self, layer_idx: int, x: int, y: int) -> QColor:
        if 0 <= layer_idx < len(self._layers) and 0 <= x < self._grid_w and 0 <= y < self._grid_h:
            return self._layers[layer_idx].image.pixelColor(x, y)
        return Qt.transparent

    def draw_pixel(self, x: int, y: int, color: QColor):
        points = self.get_symmetric_points(x, y)
        for p in points:
            self.set_pixel(p.x(), p.y(), color)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: QColor):
        points = self._bresenham_line(x0, y0, x1, y1)
        for p in points:
            self.draw_pixel(p.x(), p.y(), color)

    def draw_rect(self, x0: int, y0: int, x1: int, y1: int, color: QColor, filled: bool = False):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        if filled:
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    self.draw_pixel(x, y, color)
        else:
            for x in range(x0, x1 + 1):
                self.draw_pixel(x, y0, color)
                self.draw_pixel(x, y1, color)
            for y in range(y0, y1 + 1):
                self.draw_pixel(x0, y, color)
                self.draw_pixel(x1, y, color)

    def draw_circle(self, cx: int, cy: int, r: int, color: QColor, filled: bool = False):
        if filled:
            for x in range(-r, r + 1):
                for y in range(-r, r + 1):
                    if x * x + y * y <= r * r:
                        self.draw_pixel(cx + x, cy + y, color)
        else:
            x, y, d = 0, r, 1 - r
            while x <= y:
                for p in [(cx + x, cy + y), (cx - x, cy + y), (cx + x, cy - y), (cx - x, cy - y),
                          (cx + y, cy + x), (cx - y, cy + x), (cx + y, cy - x), (cx - y, cy - x)]:
                    self.draw_pixel(p[0], p[1], color)
                if d < 0:
                    d += 2 * x + 3
                else:
                    d += 2 * (x - y) + 5
                    y -= 1
                x += 1

    def fill_region(self, x: int, y: int, color: QColor):
        if not self.active_layer or self.active_layer.locked:
            return
        target = self.active_layer.image.pixelColor(x, y)
        if target == color:
            return
        w, h = self._grid_w, self._grid_h
        stack = [QPoint(x, y)]
        visited = set()
        while stack:
            p = stack.pop()
            key = (p.x(), p.y())
            if key in visited:
                continue
            visited.add(key)
            if not (0 <= p.x() < w and 0 <= p.y() < h):
                continue
            if self.active_layer.image.pixelColor(p.x(), p.y()) != target:
                continue
            self.active_layer.image.setPixelColor(p.x(), p.y(), color)
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                np = QPoint(p.x() + dx, p.y() + dy)
                if (np.x(), np.y()) not in visited:
                    stack.append(np)
        self._composite_dirty = True
        self._save_frame_state()

    def flip_layer_horizontal(self, layer_idx: int = None):
        if layer_idx is None:
            layer_idx = self._active_layer_index
        self._layers[layer_idx].image = self._layers[layer_idx].image.mirrored(True, False)
        self._composite_dirty = True
        self._save_frame_state()
        self.update()

    def flip_layer_vertical(self, layer_idx: int = None):
        if layer_idx is None:
            layer_idx = self._active_layer_index
        self._layers[layer_idx].image = self._layers[layer_idx].image.mirrored(False, True)
        self._composite_dirty = True
        self._save_frame_state()
        self.update()

    def clear_layer(self, layer_idx: int = None):
        if layer_idx is None:
            layer_idx = self._active_layer_index
        self._layers[layer_idx].image.fill(Qt.transparent)
        self._composite_dirty = True
        self._save_frame_state()
        self.update()

    def _bresenham_line(self, x0: int, y0: int, x1: int, y1: int) -> list[QPoint]:
        points = []
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            points.append(QPoint(x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
        return points

    # --- Undo/Redo ---

    def undo(self):
        if not self._undo_stack:
            return
        cmd = self._undo_stack.pop()
        cmd.undo(self)
        self._redo_stack.append(cmd)
        self._composite_dirty = True
        self._load_frame_state(self._active_frame)
        self.update()

    def redo(self):
        if not self._redo_stack:
            return
        cmd = self._redo_stack.pop()
        cmd.redo(self)
        self._undo_stack.append(cmd)
        self._composite_dirty = True
        self._load_frame_state(self._active_frame)
        self.update()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    # --- Zoom & Grid ---

    @property
    def zoom(self) -> int:
        return self._zoom

    @zoom.setter
    def zoom(self, z: int):
        self._zoom = max(1, min(z, 64))
        self.updateGeometry()
        self.update()

    def zoom_in(self):
        self.zoom = self._zoom * 2

    def zoom_out(self):
        self.zoom = max(1, self._zoom // 2)

    def zoom_fit(self):
        if self.parent():
            avail = self.parent().size()
            zoom_x = avail.width() // self._grid_w
            zoom_y = avail.height() // self._grid_h
            self.zoom = max(1, min(zoom_x, zoom_y))

    @property
    def show_grid(self) -> bool:
        return self._show_grid

    @show_grid.setter
    def show_grid(self, val: bool):
        self._show_grid = val
        self.update()

    # --- Colors ---

    @property
    def current_color(self) -> QColor:
        return self._current_color

    @current_color.setter
    def current_color(self, color: QColor):
        self._current_color = color
        self.color_changed.emit(color)

    @property
    def secondary_color(self) -> QColor:
        return self._secondary_color

    @secondary_color.setter
    def secondary_color(self, color: QColor):
        self._secondary_color = color

    def swap_colors(self):
        self._current_color, self._secondary_color = self._secondary_color, self._current_color
        self.color_changed.emit(self._current_color)

    # --- Canvas dimensions ---

    @property
    def grid_width(self) -> int:
        return self._grid_w

    @property
    def grid_height(self) -> int:
        return self._grid_h

    # --- Tool handling ---

    def set_tool(self, tool):
        self._tool = tool

    def mouse_pixel(self) -> QPoint:
        return self._mouse_pixel

    def set_mouse_pixel(self, p: QPoint):
        self._mouse_pixel = p

    def is_mouse_down(self) -> bool:
        return self._mouse_down

    # --- Qt events ---

    def sizeHint(self):
        return QSize(self._grid_w * self._zoom, self._grid_h * self._zoom)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        w = self._grid_w * self._zoom
        h = self._grid_h * self._zoom

        img = self.get_onion_composite()
        scaled = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        painter.drawImage(QRect(0, 0, w, h), scaled)

        if self._show_grid and self._zoom >= 4:
            painter.setPen(QPen(QColor(180, 180, 180, 120), 1))
            for x in range(self._grid_w + 1):
                painter.drawLine(x * self._zoom, 0, x * self._zoom, h)
            for y in range(self._grid_h + 1):
                painter.drawLine(0, y * self._zoom, w, y * self._zoom)

        mx, my = self._mouse_pixel.x(), self._mouse_pixel.y()
        if 0 <= mx < self._grid_w and 0 <= my < self._grid_h:
            if not self._mouse_down:
                painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
                painter.drawRect(mx * self._zoom + 1, my * self._zoom + 1, self._zoom - 2, self._zoom - 2)
                painter.setPen(QPen(QColor(0, 0, 0, 120), 1))
                painter.drawRect(mx * self._zoom, my * self._zoom, self._zoom, self._zoom)

    def mousePressEvent(self, event):
        self._mouse_pixel = self._screen_to_pixel(event.position().toPoint())
        if not self._is_valid_pixel(self._mouse_pixel):
            return

        if event.button() == Qt.LeftButton:
            self._mouse_down = True
            if self._tool:
                self._tool.mouse_press(self, self._mouse_pixel)

    def mouseMoveEvent(self, event):
        new_pixel = self._screen_to_pixel(event.position().toPoint())
        if new_pixel != self._mouse_pixel:
            self._mouse_pixel = new_pixel
            if self._mouse_down and self._tool:
                self._tool.mouse_move(self, self._mouse_pixel)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_down = False
            if self._tool:
                self._tool.mouse_release(self, self._mouse_pixel)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def timerEvent(self, event):
        if self._play_timer and event.timerId() == self._play_timer:
            self.next_frame()

    def _screen_to_pixel(self, point) -> QPoint:
        return QPoint(point.x() // self._zoom, point.y() // self._zoom)

    def _is_valid_pixel(self, pos: QPoint) -> bool:
        return 0 <= pos.x() < self._grid_w and 0 <= pos.y() < self._grid_h


class LayerSnapshotCommand:
    def __init__(self, layer_index: int, before: QImage, after: QImage, frame: int):
        self.layer_index = layer_index
        self.before = before.copy()
        self.after = after.copy()
        self.frame = frame

    def undo(self, canvas: PixelCanvas):
        while canvas._active_frame != self.frame:
            canvas.prev_frame() if canvas._active_frame > self.frame else canvas.next_frame()

        canvas._load_frame_state(self.frame)
        if self.layer_index < len(canvas._layers):
            canvas._layers[self.layer_index].image = self.before.copy()
        canvas._composite_dirty = True

    def redo(self, canvas: PixelCanvas):
        while canvas._active_frame != self.frame:
            canvas.prev_frame() if canvas._active_frame > self.frame else canvas.next_frame()

        canvas._load_frame_state(self.frame)
        if self.layer_index < len(canvas._layers):
            canvas._layers[self.layer_index].image = self.after.copy()
        canvas._composite_dirty = True
