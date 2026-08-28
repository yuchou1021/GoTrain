"""规则引擎单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.board.go_board import GoBoard, EMPTY, BLACK, WHITE, gtp_to_xy, xy_to_gtp
from app.board.rules import RulesEngine
from app.board.game import Game


def make(size=19):
    return GoBoard(size), RulesEngine(size)


def test_gtp_roundtrip():
    assert gtp_to_xy("Q16", 19) == (3, 15)
    assert xy_to_gtp(3, 15, 19) == "Q16"
    assert gtp_to_xy("A1", 19) == (18, 0)
    assert gtp_to_xy("T19", 19) == (0, 18)
    assert xy_to_gtp(0, 18, 19) == "T19"


def test_occupied_illegal():
    b, r = make()
    b.grid[9][9] = BLACK
    ok, n, ko, err = r.play(b, WHITE, (9, 9))
    assert not ok
    assert "已有" in err


def test_out_of_bounds():
    b, r = make()
    ok, n, ko, err = r.play(b, BLACK, (19, 19))
    assert not ok


def test_capture():
    b, r = make()
    b.grid[9][9] = BLACK
    b.grid[8][9] = WHITE
    b.grid[10][9] = WHITE
    b.grid[9][8] = WHITE
    ok, n, ko, err = r.play(b, WHITE, (9, 10))
    assert ok
    assert n == 1
    assert b.grid[9][9] == EMPTY
    assert b.grid[9][10] == WHITE


def test_suicide_illegal():
    b, r = make()
    b.grid[0][1] = WHITE
    b.grid[1][0] = WHITE
    ok, n, ko, err = r.play(b, BLACK, (0, 0))
    assert not ok
    assert "自杀" in err
    assert b.grid[0][0] == EMPTY


def test_capture_releases_suicide():
    """提子后自己仍有气，不算自杀。"""
    b, r = make()
    # 白棋三面包围黑单子，黑从最后一口气提回
    b.grid[9][9] = WHITE
    b.grid[8][9] = BLACK
    b.grid[10][9] = BLACK
    b.grid[9][8] = BLACK
    # 黑在 (9,10) 提白
    ok, n, ko, err = r.play(b, BLACK, (9, 10))
    assert ok
    assert n == 1


def test_basic_ko():
    b, r = make()
    for (rr, cc, color) in [(0, 1, BLACK), (1, 0, BLACK), (1, 2, BLACK),
                            (1, 1, WHITE), (2, 0, WHITE), (2, 2, WHITE), (3, 1, WHITE)]:
        b.grid[rr][cc] = color
    seen = set()
    seen.add(r.hash_board(b, BLACK))
    ok, n, ko, err = r.play(b, BLACK, (2, 1), seen)
    assert ok and n == 1 and ko == (1, 1)
    seen.add(r.hash_board(b, WHITE))
    ok2, n2, ko2, err2 = r.play(b, WHITE, (1, 1), seen)
    assert not ok2
    assert "劫" in err2


def test_ko_allowed_after_elsewhere():
    """先在外面下一手（pass 用别的点代替）后，可以回提。"""
    b, r = make()
    for (rr, cc, color) in [(0, 1, BLACK), (1, 0, BLACK), (1, 2, BLACK),
                            (1, 1, WHITE), (2, 0, WHITE), (2, 2, WHITE), (3, 1, WHITE)]:
        b.grid[rr][cc] = color
    seen = set()
    seen.add(r.hash_board(b, BLACK))
    ok, n, ko, _ = r.play(b, BLACK, (2, 1), seen)
    seen.add(r.hash_board(b, WHITE))
    # 白在外面(9,9)下一手（假想）
    ok, _, _, _ = r.play(b, WHITE, (9, 9), seen)
    seen.add(r.hash_board(b, BLACK))
    # 黑也外面下一手，然后白回提劫（此时应合法）
    ok, _, _, _ = r.play(b, BLACK, (9, 10), seen)
    seen.add(r.hash_board(b, WHITE))
    ok4, n4, ko4, err4 = r.play(b, WHITE, (1, 1), seen)
    assert ok4 and n4 == 1


def test_game_basic():
    g = Game(size=9)
    ok, err = g.play(4, 4)
    assert ok
    assert g.turn == WHITE
    assert g.moves_for_engine() == [["B", "E5"]]
    ok, _ = g.play(0, 0)
    assert ok
    assert g.move_number == 2
    assert g.undo()
    assert g.move_number == 1
    assert g.turn == WHITE
    assert g.board.get(0, 0) == EMPTY


def test_double_pass_ends_game():
    g = Game(size=9)
    g.play(4, 4)
    g.pass_move()
    assert not g.game_over
    g.pass_move()
    assert g.game_over


def test_resign():
    g = Game(size=9)
    g.resign(BLACK)
    assert g.game_over
    assert g.result_code == "W+R"

