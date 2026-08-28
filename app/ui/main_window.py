"""主窗口：对局控制 + 引擎线程 + 实时分析。"""

import json
import queue
import sys
from pathlib import Path

from PySide6.QtCore import QThread, QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout,
                               QMessageBox, QFileDialog, QInputDialog)

from ..board.go_board import EMPTY, BLACK, WHITE, OPPONENT, COLOR_NAME, xy_to_gtp
from ..board.game import Game
from ..engine.katago import KataGoEngine
from ..engine.analysis import build_view
from ..utils.sgf import write_sgf
from .board_widget import BoardWidget
from .info_panel import InfoPanel

if getattr(sys, "frozen", False):
    # onefile 打包时引擎/配置被解压到临时目录 (_MEIPASS)；onedir 时在 exe 旁
    meipass = getattr(sys, "_MEIPASS", None)
    ROOT = Path(meipass) if meipass else Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parents[2]


DEFAULT_SETTINGS = {
    "katago_path": "engine_bin/katago.exe",
    "model_path": "engine_bin/b18c384nbt-uec.bin.gz",
    "config_path": "config/analysis.cfg",
    "board_size": 19,
    "komi": 7.5,
    "human_color": "black",
    "ai_strength": "standard",
    "visits": {"fast": 200, "standard": 600, "deep": 1600},
}


def load_settings():
    path = ROOT / "config" / "settings.json"
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            s = json.load(f)
        for k, v in DEFAULT_SETTINGS.items():
            s.setdefault(k, v)
        return s
    except Exception:
        return dict(DEFAULT_SETTINGS)


def resolve(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


class EngineWorker(QObject):
    """在后台线程里跑 KataGo，逐个处理分析请求。"""

    result_ready = Signal(dict, int)
    error = Signal(str)
    log = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self.queue = queue.Queue()
        self.engine = None
        self.settings = settings
        self.latest_seq = 0

    def start_engine_and_run(self):
        try:
            self.engine = KataGoEngine(
                str(resolve(self.settings["katago_path"])),
                str(resolve(self.settings["model_path"])),
                str(resolve(self.settings["config_path"])),
            )
            self.engine.start()
            self.log.emit("引擎已启动（GPU 预热中…）")
            self.engine.warmup()
            self.log.emit("引擎就绪 ✓")
        except Exception as e:
            self.log.emit(f"引擎启动失败：{e}")
            self.error.emit(f"引擎启动失败：{e}")
        self.run()

    def analyze_async(self, job):
        self.queue.put(job)

    def stop(self):
        self.queue.put(None)

    def run(self):
        while True:
            job = self.queue.get()
            if job is None:
                break
            seq = job.get("seq", 0)
            if seq < self.latest_seq:
                continue
            if self.engine is None:
                self.error.emit("KataGo 引擎未运行")
                continue
            try:
                params = dict(job)
                params.pop("seq", None)
                res = self.engine.analyze(**params)
                self.result_ready.emit(res, seq)
            except Exception as e:
                self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.setWindowTitle("围棋训练助手 — 人机对弈 + 实时胜率分析")
        self.resize(1240, 800)

        self.game = None
        self.human_color = BLACK if self.settings.get("human_color", "black") == "black" else WHITE
        self.visits = self.settings.get("visits", {"fast": 200, "standard": 600, "deep": 1600})
        self.current_strength = self.settings.get("ai_strength", "standard")
        self._ai_move_pending = False
        self._scoring = False
        self._analysis_seq = 0
        self.curve_data = {}

        self.worker = EngineWorker(self.settings)
        self.engine_thread = QThread(self)
        self.worker.moveToThread(self.engine_thread)
        self.engine_thread.started.connect(self.worker.start_engine_and_run)
        self.worker.result_ready.connect(self.on_analysis_result)
        self.worker.error.connect(self.on_engine_error)
        self.worker.log.connect(self.on_engine_log)

        self._build_ui()
        self.engine_thread.start()
        self.new_game()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(6, 6, 6, 6)
        self.board = BoardWidget()
        lay.addWidget(self.board, 1)
        self.panel = InfoPanel()
        lay.addWidget(self.panel)
        self.setCentralWidget(central)

        menubar = self.menuBar()
        gm = menubar.addMenu("对局")
        gm.addAction("新局（执黑）", lambda: self.new_game(BLACK))
        gm.addAction("新局（执白）", lambda: self.new_game(WHITE))
        gm.addAction("悔棋", self.on_undo, "Ctrl+Z")
        gm.addAction("停一手", self.on_pass)
        gm.addAction("认输", self.on_resign)
        gm.addAction("导出 SGF…", self.on_export_sgf, "Ctrl+S")
        sm = menubar.addMenu("设置")
        sm.addAction("棋盘 9 路", lambda: self.set_board_size(9))
        sm.addAction("棋盘 13 路", lambda: self.set_board_size(13))
        sm.addAction("棋盘 19 路", lambda: self.set_board_size(19))
        sm.addSeparator()
        sm.addAction("贴目…", self.on_set_komi)

        self.panel.new_game_black.connect(lambda: self.new_game(BLACK))
        self.panel.new_game_white.connect(lambda: self.new_game(WHITE))
        self.panel.undo_requested.connect(self.on_undo)
        self.panel.pass_requested.connect(self.on_pass)
        self.panel.resign_requested.connect(self.on_resign)
        self.panel.score_requested.connect(self.on_score_now)
        self.panel.export_sgf_requested.connect(self.on_export_sgf)
        self.panel.strength_changed.connect(self.on_strength_changed)
        self.board.move_clicked.connect(self.on_board_click)
        self.panel.set_strength(self.current_strength)

    # ---------- 对局控制 ----------
    def new_game(self, human_color=None):
        if human_color is not None:
            self.human_color = human_color
        size = self.settings.get("board_size", 19)
        self.game = Game(size=size, komi=self.settings.get("komi", 7.5))
        self._ai_move_pending = False
        self._scoring = False
        self.board.set_state(self.game.size, self.game.board.grid, None)
        self.board.set_analysis(None)
        self.board.set_clickable(True)
        self.panel.curve.clear()
        self.curve_data = {}
        self.refresh()
        self.request_analysis()

    def set_board_size(self, size):
        self.settings["board_size"] = size
        self._save_settings()
        self.new_game(self.human_color)

    def on_set_komi(self):
        """修改黑方让给白方的贴目，立即生效并重新分析。"""
        value, ok = QInputDialog.getDouble(
            self, "贴目设置",
            "黑方让给白方的贴目（目，0~15，步进 0.5）：",
            float(self.settings.get("komi", 7.5)),
            0.0, 15.0, 1, step=0.5)
        if not ok:
            return
        self.settings["komi"] = value
        self._save_settings()
        if self.game is not None:
            self.game.komi = value
            self.refresh()
            if not self.game.game_over:
                self.request_analysis()

    def _save_settings(self):
        try:
            with open(ROOT / "config" / "settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def on_board_click(self, row, col):
        if self.game is None or self.game.game_over:
            return
        if self.game.turn != self.human_color:
            self.panel.set_status("现在是 AI 思考，请稍候…")
            return
        ok, err = self.game.play(row, col)
        if not ok:
            self.panel.set_status(err)
            return
        self.after_move()

    def on_undo(self):
        if self.game is None or not self.game.history:
            return
        self.game.undo()
        self._ai_move_pending = False
        self._scoring = False
        self.board.set_analysis(None)
        self.curve_data = {k: v for k, v in self.curve_data.items()
                           if k <= self.game.move_number}
        self.panel.curve.set_data(sorted(self.curve_data.items()))
        self.refresh()
        self.request_analysis()

    def on_pass(self):
        if self.game is None or self.game.game_over:
            return
        if self.game.turn != self.human_color:
            self.panel.set_status("现在是 AI 思考，请稍候…")
            return
        self.game.pass_move()
        if self.game.game_over:
            self._scoring = True
            self.panel.set_status("对局结束，正在让 KataGo 评分…")
            self.refresh()
            self.request_analysis(force=True)
        else:
            self.after_move()

    def on_resign(self):
        if self.game is None or self.game.game_over:
            return
        text = self.game.resign(self.human_color)
        self._finish_game(text)

    def on_score_now(self):
        """主动申请点目（类似 OGS 请求终局 / Lizzie 评分）。"""
        if self.game is None or self.game.game_over or self._scoring:
            return
        self._scoring = True
        self.panel.set_status("正在申请点目…")
        self.board.set_clickable(False)
        self.request_analysis(force=True)

    def on_strength_changed(self, key):
        self.current_strength = key
        self.settings["ai_strength"] = key
        self._save_settings()
        if self.game and not self.game.game_over:
            self.request_analysis()

    # ---------- 分析与 AI ----------
    def after_move(self):
        self.refresh()
        if self._maybe_end_by_fill():
            return
        self.request_analysis()

    def _maybe_end_by_fill(self):
        """棋盘填满、双方都无点可下时自动终局。"""
        if self.game is None or self.game.game_over or self._scoring:
            return False
        if all(v != EMPTY for row in self.game.board.grid for v in row):
            self._scoring = True
            self.panel.set_status("棋盘已满，正在申请点目…")
            self.board.set_clickable(False)
            self.request_analysis(force=True)
            return True
        return False

    def refresh(self):
        if self.game is None:
            return
        self.board.set_state(self.game.size, self.game.board.grid, self.game.last_move())
        self.panel.set_rules(f"贴目：{self.game.komi:g} 目（黑贴给白）")
        if self.game.game_over:
            self.panel.set_buttons_enabled(False)
        else:
            self.panel.set_buttons_enabled(True)
            if self.game.passes == 1:
                if self.game.turn == self.human_color:
                    self.panel.set_status("对方（AI）停了一手。你停一手即终局，也可继续落子")
                else:
                    self.panel.set_status("你停了一手。AI 停一手即终局")
            else:
                me = "你" if self.game.turn == self.human_color else "AI"
                self.panel.set_status(f"第 {self.game.move_number + 1} 手 · 轮到{COLOR_NAME[self.game.turn]}（{me}）")

    def request_analysis(self, force=False):
        if self.game is None:
            return
        if self.game.game_over and not force:
            return
        self._analysis_seq += 1
        seq = self._analysis_seq
        self.worker.latest_seq = seq
        visits = self.visits.get(self.current_strength, 600)
        self.worker.analyze_async({
            "seq": seq,
            "moves": self.game.moves_for_engine(),
            "board_size": self.game.size,
            "komi": self.game.komi,
            "max_visits": visits,
            "timeout": 20.0,
        })

    def on_analysis_result(self, result, seq):
        if seq != self._analysis_seq:
            return
        if self.game is None:
            return
        view = build_view(result, self.game.size)

        if self.game.game_over or self._scoring:
            root = result.get("rootInfo", {}) or {}
            score_lead = root.get("scoreLead")
            if score_lead is not None:
                current = root.get("currentPlayer", "B")
                score_black = score_lead if current == "B" else -score_lead
                text = self.game.set_score_result(score_black)
                self._finish_game(text)
            return

        self.board.set_analysis(view)

        wr = view["winrate"]
        wr_black = wr if self.game.turn == BLACK else 1.0 - wr
        self.curve_data[self.game.move_number] = wr_black
        self.panel.curve.set_data(sorted(self.curve_data.items()))

        status = (f"第 {self.game.move_number + 1} 手 · {COLOR_NAME[self.game.turn]}方胜率 "
                  f"{wr * 100:.0f}% · 领先 {view['score_lead']:+.1f} 目")
        if view["best"]:
            b = view["best"]
            status += f"\n最佳点：{xy_to_gtp(b['row'], b['col'], self.game.size)}（{b['winrate'] * 100:.0f}%）"
        self.panel.set_status(status)

        ai = OPPONENT[self.human_color]
        if self.game.turn == ai:
            if view["best"]:
                self._schedule_ai_move(view["best"]["row"], view["best"]["col"], seq)
            else:
                self._schedule_ai_pass(seq)

    def _schedule_ai_move(self, row, col, seq):
        if self._ai_move_pending:
            return
        self._ai_move_pending = True
        self.panel.set_status("AI 思考中…")
        QTimer.singleShot(500, lambda: self._do_ai_move(row, col, seq))

    def _do_ai_move(self, row, col, seq):
        self._ai_move_pending = False
        if seq != self._analysis_seq:
            return
        if self.game is None or self.game.game_over:
            return
        ok, err = self.game.play(row, col)
        if ok:
            self.after_move()
        else:
            self.panel.set_status(f"AI 落子失败：{err}")

    def _schedule_ai_pass(self, seq):
        if self._ai_move_pending:
            return
        self._ai_move_pending = True
        self.panel.set_status("AI 停一手…")
        QTimer.singleShot(500, lambda: self._do_ai_pass(seq))

    def _do_ai_pass(self, seq):
        self._ai_move_pending = False
        if seq != self._analysis_seq:
            return
        if self.game is None or self.game.game_over:
            return
        ok, err = self.game.pass_move()
        if not ok:
            self.panel.set_status(f"AI 停一手失败：{err}")
            return
        if self.game.game_over:
            self._scoring = True
            self.panel.set_status("对局结束，正在让 KataGo 评分…")
            self.refresh()
            self.request_analysis(force=True)
        else:
            self.after_move()

    def _finish_game(self, text):
        self._scoring = False
        self.panel.set_status(text)
        self.panel.set_buttons_enabled(False)
        self.board.set_clickable(False)
        self.board.set_analysis(None)
        self.panel.curve.update()
        QMessageBox.information(self, "对局结束", text)

    # ---------- 引擎事件 ----------
    def on_engine_error(self, msg):
        self.panel.set_engine(f"引擎异常：{msg}")
        if ("未运行" not in msg and "超时" not in msg
                and "启动失败" not in msg and self.isVisible()):
            QMessageBox.warning(self, "引擎错误", msg)

    def on_engine_log(self, msg):
        self.panel.set_engine(msg)

    # ---------- SGF ----------
    def on_export_sgf(self):
        if self.game is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 SGF", "对局.sgf", "SGF 文件 (*.sgf)")
        if not path:
            return
        write_sgf(path, self.game)
        self.panel.set_status(f"已导出：{path}")

    # ---------- 关闭 ----------
    def closeEvent(self, e):
        try:
            if self.worker.engine is not None:
                self.worker.engine.stop()
            self.worker.stop()
            self.engine_thread.quit()
            if not self.engine_thread.wait(3000):
                self.engine_thread.terminate()
                self.engine_thread.wait(1000)
        except Exception:
            pass
        super().closeEvent(e)


