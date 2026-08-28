"""对局状态机：落子、悔棋、认输、双pass终局、引擎落子序列。"""

from .go_board import GoBoard, EMPTY, BLACK, WHITE, OPPONENT, xy_to_gtp
from .rules import RulesEngine


class Game:
    def __init__(self, size: int = 19, komi: float = 7.5, superko: bool = True):
        self.size = size
        self.komi = komi
        self.board = GoBoard(size)
        self.rules = RulesEngine(size, superko=superko)
        self.turn = BLACK
        self.history = []          # 每手: {color,row,col,captures,ko_point,pass}
        self.captures = {BLACK: 0, WHITE: 0}
        self.passes = 0
        self.game_over = False
        self.result_code = None    # 如 "B+R" / "B+5.5"
        self.result_text = None    # 中文结果
        self.seen = set()
        self.seen.add(self.rules.hash_board(self.board, self.turn))

    # ---------- 操作 ----------
    def play(self, row: int, col: int):
        if self.game_over:
            return False, "对局已结束"
        ok, n, ko, err = self.rules.play(self.board, self.turn, (row, col), self.seen)
        if not ok:
            return False, err
        self.captures[self.turn] += n
        self.history.append({"color": self.turn, "row": row, "col": col,
                             "captures": n, "ko_point": ko, "pass": False})
        nxt = OPPONENT[self.turn]
        self.seen.add(self.rules.hash_board(self.board, nxt))
        self.turn = nxt
        self.passes = 0
        return True, None

    def pass_move(self):
        if self.game_over:
            return False, "对局已结束"
        self.history.append({"color": self.turn, "pass": True, "captures": 0,
                             "row": None, "col": None, "ko_point": None})
        self.turn = OPPONENT[self.turn]
        self.passes += 1
        if self.passes >= 2:
            self.game_over = True
        return True, None

    def resign(self, color: int):
        """color 认输，对方获胜。"""
        self.game_over = True
        winner = OPPONENT[color]
        w = "B" if winner == BLACK else "W"
        self.result_code = f"{w}+R"
        self.result_text = f"{'黑' if winner == BLACK else '白'}中盘胜"
        return self.result_text

    def set_score_result(self, score_black: float):
        """按黑方目差设置终局结果（KataGo 评分）。"""
        self.game_over = True
        if score_black > 0:
            self.result_code = f"B+{score_black:.1f}"
            self.result_text = f"黑胜 {score_black:.1f} 目（KataGo 评分）"
        else:
            self.result_code = f"W+{-score_black:.1f}"
            self.result_text = f"白胜 {-score_black:.1f} 目（KataGo 评分）"
        return self.result_text

    def undo(self, steps: int = 1) -> bool:
        if not self.history:
            return False
        for _ in range(steps):
            if not self.history:
                break
            self.history.pop()
        self._rebuild()
        return True

    # ---------- 查询 ----------
    @property
    def move_number(self) -> int:
        return len(self.history)

    def last_move(self):
        for e in reversed(self.history):
            if not e.get("pass"):
                return e["row"], e["col"]
        return None

    def moves_for_engine(self):
        """KataGo 用的落子序列（不含 pass）。"""
        return [["B" if e["color"] == BLACK else "W", xy_to_gtp(e["row"], e["col"], self.size)]
                for e in self.history if not e.get("pass")]

    # ---------- 内部 ----------
    def _rebuild(self):
        """从历史重放整个对局（悔棋/撤销时用）。"""
        self.board = GoBoard(self.size)
        self.captures = {BLACK: 0, WHITE: 0}
        self.turn = BLACK
        self.passes = 0
        self.game_over = False
        self.result_code = None
        self.result_text = None
        self.seen = set()
        self.seen.add(self.rules.hash_board(self.board, self.turn))
        for e in self.history:
            if e.get("pass"):
                self.passes += 1
                self.turn = OPPONENT[self.turn]
                continue
            ok, n, ko, err = self.rules.play(self.board, e["color"], (e["row"], e["col"]), self.seen)
            if not ok:
                raise RuntimeError(f"历史重放失败: {e} -> {err}")
            self.captures[e["color"]] += n
            nxt = OPPONENT[e["color"]]
            self.seen.add(self.rules.hash_board(self.board, nxt))
            self.turn = nxt
            self.passes = 0
