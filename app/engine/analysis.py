"""把 KataGo 分析结果转成界面视图。

KataGo 的 rootInfo.winrate / rootInfo.scoreLead / moveInfos[].winrate
都以"当前行棋方"（rootInfo.currentPlayer）为视角，这里直接透传，
由调用方决定展示给谁。
"""

from ..board.go_board import gtp_to_xy


def build_view(result: dict, board_size: int) -> dict:
    root = result.get("rootInfo", {}) or {}
    wr = root.get("winrate", 0.5)
    score = root.get("scoreLead", 0.0) or 0.0

    top = []
    for mi in result.get("moveInfos", []) or []:
        gtp = mi.get("move")
        if not gtp:
            continue
        try:
            row, col = gtp_to_xy(gtp, board_size)
        except Exception:
            continue
        top.append({"row": row, "col": col,
                    "winrate": mi.get("winrate", 0.5),
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
