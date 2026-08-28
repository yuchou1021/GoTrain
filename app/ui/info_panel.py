"""右侧信息面板：状态、胜率曲线、按钮。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QGroupBox, QFrame)
from .winrate_curve import WinrateCurveWidget


class InfoPanel(QWidget):
    new_game_black = Signal()
    new_game_white = Signal()
    undo_requested = Signal()
    pass_requested = Signal()
    resign_requested = Signal()
    export_sgf_requested = Signal()
    strength_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(330)
        lay = QVBoxLayout(self)

        self.status_label = QLabel("准备开始…")
        self.status_label.setWordWrap(True)
        f = self.status_label.font()
        f.setPointSize(11)
        f.setBold(True)
        self.status_label.setFont(f)
        self.status_label.setMinimumHeight(64)

        self.curve = WinrateCurveWidget()

        box = QGroupBox("分析")
        blay = QVBoxLayout(box)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("AI 强度："))
        self.combo_strength = QComboBox()
        self.combo_strength.addItem("快速", "fast")
        self.combo_strength.addItem("标准", "standard")
        self.combo_strength.addItem("深度", "deep")
        self.combo_strength.currentIndexChanged.connect(
            lambda i: self.strength_changed.emit(self.combo_strength.currentData()))
        row1.addWidget(self.combo_strength, 1)
        blay.addLayout(row1)

        btn = QHBoxLayout()
        self.btn_undo = QPushButton("悔棋")
        self.btn_pass = QPushButton("停一手")
        self.btn_resign = QPushButton("认输")
        btn.addWidget(self.btn_undo)
        btn.addWidget(self.btn_pass)
        btn.addWidget(self.btn_resign)
        blay.addLayout(btn)

        btn2 = QHBoxLayout()
        self.btn_new_black = QPushButton("新局·执黑")
        self.btn_new_white = QPushButton("新局·执白")
        btn2.addWidget(self.btn_new_black)
        btn2.addWidget(self.btn_new_white)
        blay.addLayout(btn2)

        self.btn_export = QPushButton("导出 SGF…")
        blay.addWidget(self.btn_export)

        self.engine_label = QLabel("引擎：未启动")
        self.engine_label.setStyleSheet("color:#888;")
        self.engine_label.setWordWrap(True)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        lay.addWidget(self.status_label)
        lay.addWidget(line)
        lay.addWidget(self.curve, 1)
        lay.addWidget(box)
        lay.addWidget(self.engine_label)

        self.btn_undo.clicked.connect(self.undo_requested.emit)
        self.btn_pass.clicked.connect(self.pass_requested.emit)
        self.btn_resign.clicked.connect(self.resign_requested.emit)
        self.btn_new_black.clicked.connect(self.new_game_black.emit)
        self.btn_new_white.clicked.connect(self.new_game_white.emit)
        self.btn_export.clicked.connect(self.export_sgf_requested.emit)

    def set_status(self, text: str):
        self.status_label.setText(text)

    def set_engine(self, text: str):
        self.engine_label.setText(text)

    def set_strength(self, key: str):
        idx = self.combo_strength.findData(key)
        if idx >= 0:
            self.combo_strength.setCurrentIndex(idx)

    def set_buttons_enabled(self, ok: bool):
        for b in (self.btn_undo, self.btn_pass, self.btn_resign, self.btn_export):
            b.setEnabled(ok)
