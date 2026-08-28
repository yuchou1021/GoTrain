"""棋盘状态与坐标转换。"""

EMPTY = 0
BLACK = 1
WHITE = 2

OPPONENT = {BLACK: WHITE, WHITE: BLACK, EMPTY: EMPTY}
COLOR_NAME = {BLACK: "黑", WHITE: "白"}

_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"  # GTP 坐标字母，跳过 I


def gtp_to_xy(gtp: str, size: int):
    """GTP 坐标(如 Q16) -> (row, col)，0 基，row 0 为棋盘顶部。"""
    gtp = gtp.strip().upper()
    col = _LETTERS.index(gtp[0])
    row = size - int(gtp[1:])
    return row, col


def xy_to_gtp(row: int, col: int, size: int) -> str:
    return _LETTERS[col] + str(size - row)


class GoBoard:
    """只负责棋盘网格状态，不含规则。"""

    def __init__(self, size: int = 19):
        self.size = size
        self.grid = [[EMPTY] * size for _ in range(size)]

    def clone(self):
        b = GoBoard(self.size)
        b.grid = [row[:] for row in self.grid]
        return b

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    def get(self, row: int, col: int) -> int:
        return self.grid[row][col]

    def neighbors(self, row: int, col: int):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            r, c = row + dr, col + dc
            if self.in_bounds(r, c):
                yield r, c

    def group(self, row: int, col: int):
        """返回 (棋子集合, 气集合, 颜色)。"""
        color = self.grid[row][col]
        if color == EMPTY:
            return set(), set(), EMPTY
        stones, liberties = set(), set()
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if (r, c) in stones:
                continue
            stones.add((r, c))
            for nr, nc in self.neighbors(r, c):
                if self.grid[nr][nc] == EMPTY:
                    liberties.add((nr, nc))
                elif self.grid[nr][nc] == color and (nr, nc) not in stones:
                    stack.append((nr, nc))
        return stones, liberties, color

    def remove_stones(self, stones):
        for r, c in stones:
            self.grid[r][c] = EMPTY

    def stone_count(self, color: int) -> int:
        return sum(1 for row in self.grid for v in row if v == color)
