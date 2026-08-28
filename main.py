"""围棋训练助手 — 程序入口。"""

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("围棋训练助手")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
