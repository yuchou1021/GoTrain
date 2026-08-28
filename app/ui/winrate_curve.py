"""黑方胜率曲线控件。"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import QWidget, QSizePolicy


class WinrateCurveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # [(move_no, winrate_black)]
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, data):
        self.data = list(data)
        self.update()

    def add_point(self, move_no, wr):
        self.data.append((move_no, wr))
        self.update()

    def clear(self):
        self.data = []
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m = 34
        plot = QRectF(m, 6, w - m - 10, h - m - 10)
        if plot.width() <= 1 or plot.height() <= 1:
            return

        p.fillRect(plot, QColor(252, 250, 246))
        mid_y = plot.top() + plot.height() * 0.5
        p.setPen(QPen(QColor(205, 195, 175), 1, Qt.DashLine))
        p.drawLine(QPointF(plot.left(), mid_y), QPointF(plot.right(), mid_y))
        p.setPen(QPen(QColor(150, 140, 120), 1))
        p.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))
        p.drawLine(QPointF(plot.left(), plot.top()), QPointF(plot.left(), plot.bottom()))

        p.setFont(QFont("Microsoft YaHei", 8))
        p.setPen(QColor(120, 110, 95))
        for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            y = plot.top() + plot.height() * (1 - frac)
            p.drawText(QRectF(0, y - 8, m - 4, 16), Qt.AlignRight | Qt.AlignVCenter, label)

        if not self.data:
            p.setPen(QColor(160, 150, 135))
            p.drawText(plot, Qt.AlignCenter, "对局开始后显示胜率曲线")
            return

        max_x = max(x for x, _ in self.data) or 1
        pts = [QPointF(plot.left() + plot.width() * (x / max_x),
                       plot.top() + plot.height() * (1 - wr))
               for x, wr in self.data]
        path = QPainterPath()
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        path.lineTo(pts[-1].x(), plot.bottom())
        path.lineTo(pts[0].x(), plot.bottom())
        path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(66, 133, 244, 55))
        p.drawPath(path)

        p.setPen(QPen(QColor(40, 100, 220), 2))
        p.setBrush(Qt.NoBrush)
        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])
        p.setBrush(QColor(220, 60, 60))
        p.setPen(Qt.NoPen)
        p.drawEllipse(pts[-1], 3.5, 3.5)

        p.setPen(QColor(120, 110, 95))
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(QRectF(plot.left(), plot.bottom() + 3, plot.width(), 16),
                   Qt.AlignRight, f"第 {max_x} 手")
