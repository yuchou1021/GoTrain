"""SGF 棋谱导出。"""

from pathlib import Path

from ..board.go_board import BLACK, WHITE, xy_to_gtp

_SGF_LETTERS = "abcdefghijklmnopqrstuvwxyz"
_GTP_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def gtp_to_sgf_point(gtp: str, size: int) -> str:
    col = _GTP_LETTERS.index(gtp[0])
    row_from_top = size - int(gtp[1:])
    return _SGF_LETTERS[col] + _SGF_LETTERS[row_from_top]


def write_sgf(path, game, players=("玩家", "KataGo")):
    header = (f"(;GM[1]FF[4]CA[UTF-8]AP[go-trainer]SZ[{game.size}]KM[{game.komi}]"
              f"PB[{players[0]}]PW[{players[1]}]")
    if game.result_code:
        header += f"RE[{game.result_code}]"
    moves = []
    for e in game.history:
        c = "B" if e["color"] == BLACK else "W"
        if e.get("pass"):
            moves.append(f";{c}[tt]")
        else:
            gtp = xy_to_gtp(e["row"], e["col"], game.size)
            moves.append(f";{c}[{gtp_to_sgf_point(gtp, game.size)}]")
    Path(path).write_text(header + "".join(moves) + ")", encoding="utf-8")
