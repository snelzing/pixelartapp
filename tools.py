from __future__ import annotations
from abc import ABC, abstractmethod
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QPen, QPixmap, QCursor
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt


class Tool(ABC):
    def __init__(self, name: str, icon_char: str = ""):
        self.name = name
        self.icon_char = icon_char
        self._start_pos = None
        self._preview = None

    @abstractmethod
    def mouse_press(self, canvas, pos: QPoint): ...
    def mouse_move(self, canvas, pos: QPoint): ...
    def mouse_release(self, canvas, pos: QPoint): ...


class PencilTool(Tool):
    def __init__(self):
        super().__init__("Pencil", "✏")

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        color = canvas.current_color
        canvas.draw_pixel(pos.x(), pos.y(), color)

    def mouse_move(self, canvas, pos: QPoint):
        if canvas.is_mouse_down():
            color = canvas.current_color
            last = canvas.mouse_pixel()
            canvas.draw_line(last.x(), last.y(), pos.x(), pos.y(), color)

    def mouse_release(self, canvas, pos: QPoint):
        canvas.end_draw()


class EraserTool(Tool):
    def __init__(self):
        super().__init__("Eraser", "⌫")

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        canvas.draw_pixel(pos.x(), pos.y(), Qt.transparent)

    def mouse_move(self, canvas, pos: QPoint):
        if canvas.is_mouse_down():
            last = canvas.mouse_pixel()
            canvas.draw_line(last.x(), last.y(), pos.x(), pos.y(), Qt.transparent)

    def mouse_release(self, canvas, pos: QPoint):
        canvas.end_draw()


class FillTool(Tool):
    def __init__(self):
        super().__init__("Fill", "🪣")

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        canvas.fill_region(pos.x(), pos.y(), canvas.current_color)

    def mouse_release(self, canvas, pos: QPoint):
        canvas.end_draw()


class EyedropperTool(Tool):
    def __init__(self):
        super().__init__("Eyedropper", "💉")

    def mouse_press(self, canvas, pos: QPoint):
        color = canvas.get_pixel(pos.x(), pos.y())
        if color.alpha() > 0:
            canvas.current_color = color

    def mouse_move(self, canvas, pos: QPoint): ...
    def mouse_release(self, canvas, pos: QPoint): ...


class LineTool(Tool):
    def __init__(self):
        super().__init__("Line", "╱")
        self._origin = None

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        self._origin = pos

    def mouse_move(self, canvas, pos: QPoint):
        if canvas.is_mouse_down() and self._origin is not None:
            pass

    def mouse_release(self, canvas, pos: QPoint):
        if self._origin:
            canvas.draw_line(self._origin.x(), self._origin.y(), pos.x(), pos.y(), canvas.current_color)
            self._origin = None
        canvas.end_draw()


class RectTool(Tool):
    def __init__(self):
        super().__init__("Rectangle", "▭")
        self._origin = None

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        self._origin = pos

    def mouse_release(self, canvas, pos: QPoint):
        if self._origin:
            canvas.draw_rect(self._origin.x(), self._origin.y(), pos.x(), pos.y(), canvas.current_color)
            self._origin = None
        canvas.end_draw()


class FilledRectTool(Tool):
    def __init__(self):
        super().__init__("Filled Rect", "▬")
        self._origin = None

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        self._origin = pos

    def mouse_release(self, canvas, pos: QPoint):
        if self._origin:
            canvas.draw_rect(self._origin.x(), self._origin.y(), pos.x(), pos.y(), canvas.current_color, filled=True)
            self._origin = None
        canvas.end_draw()


class CircleTool(Tool):
    def __init__(self):
        super().__init__("Circle", "◯")
        self._origin = None

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        self._origin = pos

    def mouse_release(self, canvas, pos: QPoint):
        if self._origin:
            dx = pos.x() - self._origin.x()
            dy = pos.y() - self._origin.y()
            r = int((dx * dx + dy * dy) ** 0.5)
            canvas.draw_circle(self._origin.x(), self._origin.y(), r, canvas.current_color)
            self._origin = None
        canvas.end_draw()


class FilledCircleTool(Tool):
    def __init__(self):
        super().__init__("Filled Circle", "⬤")
        self._origin = None

    def mouse_press(self, canvas, pos: QPoint):
        canvas.begin_draw()
        self._origin = pos

    def mouse_release(self, canvas, pos: QPoint):
        if self._origin:
            dx = pos.x() - self._origin.x()
            dy = pos.y() - self._origin.y()
            r = int((dx * dx + dy * dy) ** 0.5)
            canvas.draw_circle(self._origin.x(), self._origin.y(), r, canvas.current_color, filled=True)
            self._origin = None
        canvas.end_draw()


TOOLS = [
    PencilTool,
    EraserTool,
    FillTool,
    EyedropperTool,
    LineTool,
    RectTool,
    FilledRectTool,
    CircleTool,
    FilledCircleTool,
]
