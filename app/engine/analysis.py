"""把 KataGo 分析结果转成界面视图（以当前行棋方视角）。"""

from ..board.go_board import BLACK, WHITE, gtp_to_xy


def build_view(result: dict, board_size: int, perspective_color: int) -> dict:
    root = result.get("rootInfo", {}) or {}
    wr_black = root.get("winrate", 0.5)
    wr = wr_black if perspective_color == BLACK else 1.0 - wr_black
    score_black = root.get("scoreLead", 0.0) or 0.0
    score = score_black if perspective_color == BLACK else -score_black

    top = []
    for mi in result.get("moveInfos", []) or []:
        gtp = mi.get("move")
        if not gtp:
            continue
        try:
            row, col = gtp_to_xy(gtp, board_size)
        except Exception:
            continue
        p = mi.get("winrate", 0.5)
        if perspective_color == WHITE:
            p = 1.0 - p
        top.append({"row": row, "col": col, "winrate": p,
                    "visits": mi.get("visits", 0),
                    "score_lead": mi.get("scoreLead", 0.0)})
    top.sort(key=lambda t: -t["visits"])

    return {
        "winrate": wr,
        "score_lead": score,
        "top": top,
        "best": top[0] if top else None,
        "ownership": result.get("ownership"),
        "raw": result,
    }
