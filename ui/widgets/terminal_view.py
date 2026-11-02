"""Qt widget that renders a :class:`TerminalSession` pyte screen and forwards
keyboard input to the PTY. Repaints are coalesced on a timer so a chatty tool
doesn't flood the UI thread."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from core.terminal_manager import TerminalSession

# pyte colour name -> hex (ANSI). 'default' handled separately.
_ANSI = {
    "black": "#1a1f22", "red": "#ff5f6e", "green": "#27e0a1", "brown": "#ffd23f",
    "blue": "#4dabf7", "magenta": "#c38cff", "cyan": "#13c2c2", "white": "#d6e4e6",
    "brightblack": "#56696d", "brightred": "#ff8c9a", "brightgreen": "#5affc0",
    "brightbrown": "#ffe27a", "brightblue": "#79c6ff", "brightmagenta": "#d7b3ff",
    "brightcyan": "#5ce1e6", "brightwhite": "#ffffff",
}


class TerminalView(QWidget):
    exited = Signal(int)
    title_changed = Signal(str)

    def __init__(self, session: TerminalSession, font_family="DejaVu Sans Mono",
                 font_size=11, parent=None):
        super().__init__(parent)
        self.session = session
        self.setObjectName("TermView")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.IBeamCursor)
        self._fg_default = QColor("#d6e4e6")
        self._bg_default = QColor("#05080a")
        self._font = QFont(font_family, font_size)
        self._font.setStyleHint(QFont.Monospace)
        self._metrics = QFontMetricsF(self._font)
        self._char_w = max(1.0, self._metrics.horizontalAdvance("M"))
        self._char_h = max(1.0, self._metrics.height())
        self._dirty = False
        self._cursor_on = True
        self._pad_x = 8
        self._pad_y = 5
        self._scrolled = False

        self.session.set_callbacks(on_update=self._mark_dirty, on_exit=self._on_exit)

        self._repaint_timer = QTimer(self)
        self._repaint_timer.setInterval(40)
        self._repaint_timer.timeout.connect(self._maybe_repaint)
        self._repaint_timer.start()
        self._blink = QTimer(self)
        self._blink.setInterval(530)
        self._blink.timeout.connect(self._toggle_cursor)
        self._blink.start()

    # --------------------------------------------------------------- sizing
    def cols_rows(self) -> tuple[int, int]:
        cols = max(10, int((self.width() - 2 * self._pad_x) / self._char_w))
        rows = max(4, int((self.height() - 2 * self._pad_y) / self._char_h))
        return cols, rows

    def wheelEvent(self, event):  # noqa: N802
        if event.angleDelta().y() > 0:
            self.session.scroll_up(1)
            self._scrolled = True
        else:
            self.session.scroll_down(1)
        self.update()

    def resizeEvent(self, event):  # noqa: N802
        cols, rows = self.cols_rows()
        self.session.resize(cols, rows)
        super().resizeEvent(event)

    def set_font(self, family: str, size: int) -> None:
        self._font = QFont(family, size)
        self._font.setStyleHint(QFont.Monospace)
        self._metrics = QFontMetricsF(self._font)
        self._char_w = max(1.0, self._metrics.horizontalAdvance("M"))
        self._char_h = max(1.0, self._metrics.height())
        cols, rows = self.cols_rows()
        self.session.resize(cols, rows)
        self.update()

    # --------------------------------------------------------------- paint
    def _mark_dirty(self) -> None:
        self._dirty = True

    def _maybe_repaint(self) -> None:
        if self._dirty:
            self._dirty = False
            self.update()

    def _toggle_cursor(self) -> None:
        self._cursor_on = not self._cursor_on
        self.update()

    def _resolve(self, name: str, default: QColor) -> QColor:
        if name == "default":
            return default
        if name in _ANSI:
            return QColor(_ANSI[name])
        if len(name) == 6:
            try:
                return QColor("#" + name)
            except ValueError:
                return default
        return default

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, self.height()))
        grad.setColorAt(0.0, QColor("#0a1013"))
        grad.setColorAt(1.0, self._bg_default)
        painter.fillRect(self.rect(), grad)
        painter.setFont(self._font)
        screen = self.session.buffer_snapshot()
        ascent = self._metrics.ascent()
        try:
            buffer = screen.buffer
            cursor = screen.cursor
            columns = screen.columns
            lines = screen.lines
        except AttributeError:
            painter.end()
            return

        for row in range(lines):
            line = buffer.get(row, {})
            y = row * self._char_h + self._pad_y
            for col in range(columns):
                char = line.get(col)
                if char is None:
                    continue
                data = char.data or " "
                fg = self._resolve(char.fg, self._fg_default)
                bg = self._resolve(char.bg, self._bg_default)
                if char.reverse:
                    fg, bg = bg, fg
                x = col * self._char_w + self._pad_x
                if bg != self._bg_default:
                    painter.fillRect(int(x), int(y), int(self._char_w) + 1,
                                     int(self._char_h) + 1, bg)
                if data != " ":
                    font = painter.font()
                    font.setBold(bool(char.bold))
                    font.setItalic(bool(char.italics))
                    font.setUnderline(bool(char.underscore))
                    painter.setFont(font)
                    painter.setPen(fg)
                    painter.drawText(int(x), int(y + ascent), data)

        # cursor (only when live, i.e. not scrolled back)
        if self._cursor_on and self.session.is_alive() and not self._scrolled:
            cx = cursor.x * self._char_w + self._pad_x
            cy = cursor.y * self._char_h + self._pad_y
            painter.fillRect(int(cx), int(cy), int(self._char_w),
                             int(self._char_h), QColor("#27e0a1"))
            glyph = " "
            try:
                glyph = buffer.get(cursor.y, {}).get(cursor.x).data or " "
            except AttributeError:
                pass
            painter.setPen(self._bg_default)
            painter.drawText(int(cx), int(cy + ascent), glyph)

        # scrollback indicator (shown while scrolled up into history)
        if self._scrolled:
            tag = "  ⇡ history — scroll down or type to return  "
            fm = self._metrics
            tw = int(fm.horizontalAdvance(tag))
            bx = self.width() - tw - 12
            painter.fillRect(bx, 6, tw, int(self._char_h) + 6, QColor(10, 26, 24, 230))
            painter.setPen(QColor("#27e0a1"))
            painter.drawText(bx, int(6 + ascent + 3), tag)
        painter.end()

    # --------------------------------------------------------------- input
    def keyPressEvent(self, event):  # noqa: N802
        if not self.session.is_alive():
            return
        key = event.key()
        mods = event.modifiers()
        text = event.text()

        # Shift+PageUp / Shift+PageDown scroll the history without sending keys
        if mods & Qt.ShiftModifier and key in (Qt.Key_PageUp, Qt.Key_PageDown):
            if key == Qt.Key_PageUp:
                self.session.scroll_up(1)
                self._scrolled = True
            else:
                self.session.scroll_down(1)
            self.update()
            return
        # any real input returns to the live (bottom) view
        if self._scrolled:
            self.session.scroll_to_bottom()
            self._scrolled = False

        if mods & Qt.ControlModifier and key == Qt.Key_C and self.selectedText_available():
            return  # allow copy via shortcut handler elsewhere
        mapping = {
            Qt.Key_Return: "\r", Qt.Key_Enter: "\r", Qt.Key_Backspace: "\x7f",
            Qt.Key_Tab: "\t", Qt.Key_Escape: "\x1b",
            Qt.Key_Up: "\x1b[A", Qt.Key_Down: "\x1b[B",
            Qt.Key_Right: "\x1b[C", Qt.Key_Left: "\x1b[D",
            Qt.Key_Home: "\x1b[H", Qt.Key_End: "\x1b[F",
            Qt.Key_PageUp: "\x1b[5~", Qt.Key_PageDown: "\x1b[6~",
            Qt.Key_Delete: "\x1b[3~",
        }
        if (mods & Qt.ControlModifier) and Qt.Key_A <= key <= Qt.Key_Z:
            self.session.write(bytes([key - Qt.Key_A + 1]))
            return
        if key in mapping:
            self.session.write(mapping[key])
            return
        if text:
            self.session.write(text)

    def selectedText_available(self) -> bool:  # noqa: N802
        return False

    def paste_text(self, text: str) -> None:
        self.session.write(text)

    def closeEvent(self, event):  # noqa: N802
        self._repaint_timer.stop()
        self._blink.stop()
        super().closeEvent(event)

    def _on_exit(self, code: int) -> None:
        self.exited.emit(code)
