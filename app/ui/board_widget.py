"""棋盘绘制 + 鼠标落子 + 实时分析叠加层。"""

import math

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QFont,
                           QRadialGradient, QLinearGradient)
from PySide6.QtWidgets import QWidget, QSizePolicy

from ..board.go_board import EMPTY, BLACK, WHITE

_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"

_COL_WOOD_TOP = QColor(224, 186, 138)
_COL_WOOD_BOTTOM = QColor(202, 152, 98)
_COL_LINE = QColor(80, 48, 24)
_COL_LABEL = QColor(90, 60, 30)


class BoardWidget(QWidget):
    move_clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.board_size = 19
        self.grid = None
        self.last_move = None
        self.analysis = None
        self.hover = None
        self.clickable = True
        self.setMouseTracking(True)
        self.setMinimumSize(420, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ---------- 对外接口 ----------
    def set_state(self, board_size, grid, last_move):
        self.board_size = board_size
        self.grid = grid
        self.last_move = last_move
        self.update()

    def set_analysis(self, analysis):
        self.analysis = analysis
        self.update()

    def set_clickable(self, ok: bool):
        self.clickable = ok

    # ---------- 几何 ----------
    def _origin(self):
        side = min(self.width(), self.height())
        cell = side / (self.board_size + 1.6)
        span = (self.board_size - 1) * cell
        x0 = (self.width() - span) / 2
        y0 = (self.height() - span) / 2
        return x0, y0, cell

    def _point(self, row, col):
        x0, y0, cell = self._origin()
        return QPointF(x0 + col * cell, y0 + row * cell)

    def _nearest(self, pos):
        x0, y0, cell = self._origin()
        col = round((pos.x() - x0) / cell)
        row = round((pos.y() - y0) / cell)
        if not (0 <= row < self.board_size and 0 <= col < self.board_size):
            return None
        pt = self._point(row, col)
        if math.hypot(pos.x() - pt.x(), pos.y() - pt.y()) > cell * 0.55:
            return None
        return row, col

    # ---------- 鼠标 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.clickable and self.grid:
            hit = self._nearest(e.position())
            if hit:
                self.move_clicked.emit(hit[0], hit[1])

    def mouseMoveEvent(self, e):
        if not self.clickable or not self.grid:
            return
        hit = self._nearest(e.position())
        if hit != self.hover:
            self.hover = hit
            self.update()

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._paint_board(p)
        self._paint_stones(p)
        self._paint_analysis(p)
        self._paint_hover(p)

    def _paint_board(self, p):
        x0, y0, cell = self._origin()
        span = (self.board_size - 1) * cell
        rect = QRectF(x0 - cell * 0.9, y0 - cell * 0.9, span + 1.8 * cell, span + 1.8 * cell)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, _COL_WOOD_TOP)
        grad.setColorAt(1.0, _COL_WOOD_BOTTOM)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, 8, 8)

        pen = QPen(_COL_LINE, max(1.0, cell * 0.04))
        p.setPen(pen)
        for i in range(self.board_size):
            p.drawLine(self._point(i, 0), self._point(i, self.board_size - 1))
            p.drawLine(self._point(0, i), self._point(self.board_size - 1, i))

        p.setBrush(QBrush(_COL_LINE))
        p.setPen(Qt.NoPen)
        for r, c in self._star_points():
            pt = self._point(r, c)
            p.drawEllipse(pt, cell * 0.11, cell * 0.11)

        font = QFont("Microsoft YaHei", max(7, int(cell * 0.26)))
        p.setFont(font)
        p.setPen(_COL_LABEL)
        for i in range(self.board_size):
            pt = self._point(i, self.board_size - 1)
            p.drawText(QRectF(pt.x() + cell * 0.22, pt.y() - cell * 0.35, cell * 1.2, cell * 0.7),
                       Qt.AlignLeft | Qt.AlignVCenter, _LETTERS[i])
            pt = self._point(self.board_size - 1, i)
            p.drawText(QRectF(pt.x() - cell * 0.6, pt.y() + cell * 0.18, cell * 1.2, cell * 0.7),
                       Qt.AlignHCenter | Qt.AlignTop, str(self.board_size - i))

    def _star_points(self):
        n = self.board_size
        if n == 19:
            return [(3, 3), (3, 9), (3, 15), (9, 3), (9, 9), (9, 15),
                    (15, 3), (15, 9), (15, 15)]
        if n == 13:
            return [(3, 3), (3, 9), (9, 3), (9, 9), (6, 6)]
        return [(2, 2), (2, 6), (6, 2), (6, 6), (4, 4)]

    def _paint_stones(self, p):
        if not self.grid:
            return
        cell = self._cell()
        for r in range(self.board_size):
            row = self.grid[r]
            for c in range(self.board_size):
                v = row[c]
                if v == EMPTY:
                    continue
                pt = self._point(r, c)
                self._paint_stone(p, pt, cell, v)
                if self.last_move == (r, c):
                    mark = QColor(255, 70, 70) if v == BLACK else QColor(70, 130, 255)
                    p.setPen(QPen(mark, max(1.5, cell * 0.08)))
                    p.setBrush(Qt.NoBrush)
                    p.drawEllipse(pt, cell * 0.3, cell * 0.3)

    def _cell(self):
        side = min(self.width(), self.height())
        return side / (self.board_size + 1.6)

    def _paint_stone(self, p, pt, cell, color):
        radius = cell * 0.46
        if color == BLACK:
            grad = QRadialGradient(pt.x() - radius * 0.35, pt.y() - radius * 0.35, radius * 1.3)
            grad.setColorAt(0.0, QColor(96, 96, 96))
            grad.setColorAt(0.6, QColor(38, 38, 38))
            grad.setColorAt(1.0, QColor(8, 8, 8))
        else:
            grad = QRadialGradient(pt.x() - radius * 0.35, pt.y() - radius * 0.35, radius * 1.3)
            grad.setColorAt(0.0, QColor(255, 255, 255))
            grad.setColorAt(0.7, QColor(238, 238, 238))
            grad.setColorAt(1.0, QColor(176, 176, 176))
        p.setPen(QPen(QColor(70, 46, 22), max(1.0, cell * 0.03)))
        p.setBrush(QBrush(grad))
        p.drawEllipse(pt, radius, radius)

    def _paint_analysis(self, p):
        if not self.analysis:
            return
        cell = self._cell()
        top = self.analysis.get("top") or []
        if not top:
            return
        best = top[0]
        pt = self._point(best["row"], best["col"])
        p.setPen(QPen(QColor(255, 200, 40), max(2.0, cell * 0.12)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(pt, cell * 0.52, cell * 0.52)

        font = QFont("Microsoft YaHei", max(8, int(cell * 0.28)), QFont.Bold)
        p.setFont(font)
        used = []
        self._label_rects = []
        for t in top[:5]:
            used = self._paint_winrate_label(p, t, cell, used)

    def _winrate_color(self, wr):
        """按胜率着色：0% 红 -> 50% 黄绿 -> 100% 绿。"""
        wr = max(0.0, min(1.0, wr))
        c = QColor()
        c.setHsl(int(120.0 * wr), 200, 110)
        return c

    def _paint_winrate_label(self, p, t, cell, used):
        pt = self._point(t["row"], t["col"])
        text = f"{t['winrate'] * 100:.0f}%"
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        bw, bh = tw + 8, th + 3

        # 候选点上的同色小圆点，与标签颜色一一对应
        wr = t.get("winrate", 0.5)
        mark = self._winrate_color(wr)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(mark))
        p.drawEllipse(pt, cell * 0.11, cell * 0.11)

        # 标签默认放在点位右侧、垂直居中；贴右边缘时改放左侧
        x0, y0, _ = self._origin()
        right = x0 + (self.board_size - 1) * cell
        dx = cell * 0.42
        rect = QRectF(pt.x() + dx, pt.y() - bh / 2, bw, bh)
        on_left = False
        if rect.right() > right:
            rect.moveLeft(pt.x() - dx - rect.width())
            on_left = True

        # 简单避让：与已放置的标签重叠时上下错开
        shift, step, n = 0.0, bh + 2, 0
        while n < 8:
            if not any(rect.translated(0, shift).intersects(r) for r in used):
                break
            n += 1
            sign = 1 if n % 2 == 1 else -1
            shift = sign * ((n + 1) // 2) * step
        rect = rect.translated(0, shift)
        used.append(rect)
        self._label_rects.append(rect)

        # 连接线：从点位到标签边缘，建立明确的对应关系
        p.setPen(QPen(mark, max(1.0, cell * 0.05)))
        anchor = rect.right() if on_left else rect.left()
        p.drawLine(QPointF(pt.x(), pt.y()),
                   QPointF(anchor, rect.center().y()))

        # 标签底色沿用胜率色（半透明），文字按亮度取黑/白
        bg = QColor(mark)
        bg.setAlpha(215)
        fg = QColor(20, 20, 20) if mark.lightness() >= 150 else QColor(255, 255, 255)
        p.setPen(QPen(mark.darker(125), max(1.0, cell * 0.03)))
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(rect, 3, 3)
        p.setPen(fg)
        p.drawText(rect, Qt.AlignCenter, text)
        return used

    def _paint_hover(self, p):
        if not self.clickable or self.hover is None or not self.grid:
            return
        r, c = self.hover
        if not (0 <= r < self.board_size and 0 <= c < self.board_size):
            return
        if self.grid[r][c] != EMPTY:
            return
        cell = self._cell()
        pt = self._point(r, c)
        p.setPen(QPen(QColor(70, 170, 70, 230), max(1.5, cell * 0.06)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(pt, cell * 0.42, cell * 0.42)
