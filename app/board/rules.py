"""围棋规则：落子合法性 + 位置型超劫（positional superko）。"""

import random

from .go_board import GoBoard, EMPTY, BLACK, WHITE, OPPONENT


class RulesEngine:
    def __init__(self, size: int = 19, superko: bool = True):
        self.size = size
        self.superko = superko
        rng = random.Random(20260826)
        self._z = {(r, c, color): rng.getrandbits(64)
                   for color in (BLACK, WHITE)
                   for r in range(size) for c in range(size)}
        self._turn_z = {BLACK: rng.getrandbits(64), WHITE: rng.getrandbits(64)}

    def hash_board(self, board: GoBoard, turn: int) -> int:
        """局面 + 轮到谁走的 Zobrist 哈希，用于超劫判重。"""
        h = 0
        for r in range(self.size):
            row = board.grid[r]
            for c in range(self.size):
                v = row[c]
                if v != EMPTY:
                    h ^= self._z[(r, c, v)]
        h ^= self._turn_z[turn]
        return h

    def play(self, board: GoBoard, color: int, move, seen=None):
        """尝试落子。

        成功返回 (True, 提子数, 劫点或None, None)；
        失败返回 (False, 0, None, 错误信息)，棋盘保持不变。
        """
        row, col = move
        if not board.in_bounds(row, col):
            return False, 0, None, "坐标越界"
        if board.get(row, col) != EMPTY:
            return False, 0, None, "该点已有棋子"

        board.grid[row][col] = color
        captured = []
        for nr, nc in board.neighbors(row, col):
            if board.get(nr, nc) == OPPONENT[color]:
                stones, liberties, _ = board.group(nr, nc)
                if not liberties:
                    captured.extend(stones)
        for r, c in captured:
            board.grid[r][c] = EMPTY

        if not self._has_liberty(board, row, col):
            self._rollback(board, row, col, captured, color)
            return False, 0, None, "自杀（禁着点）"

        if seen is not None and self.superko:
            h = self.hash_board(board, OPPONENT[color])
            if h in seen:
                self._rollback(board, row, col, captured, color)
                return False, 0, None, "违反打劫/循环禁手"

        ko_point = captured[0] if len(captured) == 1 else None
        return True, len(captured), ko_point, None

    def _has_liberty(self, board: GoBoard, row: int, col: int) -> bool:
        stones, liberties, _ = board.group(row, col)
        return bool(liberties)

    def _rollback(self, board, row, col, captured, color):
        board.grid[row][col] = EMPTY
        for r, c in captured:
            board.grid[r][c] = OPPONENT[color]
