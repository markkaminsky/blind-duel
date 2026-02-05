"""
Blind Duel — simultaneous "locked-in" 2-player chase game.
Hero (@) vs Warden (W). Both commit 2 moves secretly, then reveal and resolve.
Inspired by Battleship + turn-based strategy.
"""
import os
import random
import sys

# Import shared helpers from main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import (
    clear_screen, find_cells, get_cell, set_cell,
    FLOOR, WALL, GOAL_CHAR, PLAYER_CHAR, HEALTH_CHAR,
    _color_cell, _C, _P,
    sfx_move, sfx_hurt, sfx_goal, sfx_gameover, sfx_win,
    _play_sfx,
)

HERO_CHAR = "@"
WARDEN_CHAR = "W"
HEALTH_CHAR = "+"
WARDEN_COLOR = "\033[91m"  # red

# Blind Duel levels: Hero (@) reaches G; Warden (W) tries to tag. + = health, $ = gold.
# Level 1: Hero in corridor, Warden below — Hero must go R then D to reach G; choke at center.
# Level 2: Larger map; Hero top-left, Warden bottom — G near bottom; multiple paths create prediction gameplay.
# Level 3: Zelda-style with narrow choke points; Hero must out-guess Warden at intersections.
BLIND_DUEL_LEVELS = [
    [  # 16x15 - Hero in corridor, Warden below; choke at center
        "################",
        "#..............#",
        "#.+............#",
        "#..#######.....#",
        "#..#.....#.....#",
        "#..#.@...#.....#",
        "#..#.....#.....#",
        "#..#####.#####.#",
        "#..............#",
        "#......W....$..#",
        "#....#####.....#",
        "#....#...#.....#",
        "#....#...#.....#",
        "#....#.....G...#",
        "################",
    ],
    [  # 19x16 - Larger; Hero top-left, Warden bottom; G near bottom
        "###################",
        "#.+.......$.......#",
        "#.................#",
        "#.#####.#####.#####",
        "#.#...........#...#",
        "#.#..@.........#..#",
        "#.#..............+#",
        "#.#...............#",
        "#.#####.#####.....#",
        "#...........#.....#",
        "#............#....#",
        "#....#####...#....#",
        "#....#...+.#.#....#",
        "#....#.....#.#.G..#",
        "#####.......###W###",
        "###################",
    ],
    [  # 21x18 - Zelda-style; narrow choke points; Hero center, Warden mid, G bottom-right
        "#####################",
        "#.+.$......$.......+#",
        "#...................#",
        "#####.#####.#####.###",
        "#.#...........#.....#",
        "#.#...........#.....#",
        "#.#....@......#.....#",
        "#.#...........#.....#",
        "#.#.......W.........#",
        "#.#####.#####.#.....#",
        "#..............$....#",
        "#...................#",
        "#.....#####.........#",
        "#.....#...+.#.......#",
        "#.....#.....#.......#",
        "#####.#####.#####.###",
        "#.$................G#",
        "#####################",
    ],
]

MOVE_MAP = {"R": (0, 1), "L": (0, -1), "U": (-1, 0), "D": (1, 0), "W": (0, 0)}
_REV_MOVE = {(0, 1): "R", (0, -1): "L", (-1, 0): "U", (1, 0): "D", (0, 0): "W"}
MAX_HP = 5
HERO_START_HP = 4


def _parse_moves(s):
    """Parse 'RU' or 'R U' into [(dr,dc), (dr,dc)]. Invalid -> (0,0) for that slot."""
    s = s.upper().strip().replace(" ", "")[:2]
    out = []
    for c in (s[0] if len(s) > 0 else "W", s[1] if len(s) > 1 else "W"):
        out.append(MOVE_MAP.get(c, (0, 0)))
    return out


def _get_move_pair(role):
    """Get 2 moves from player. R=right, L=left, U=up, D=down, W=wait."""
    while True:
        s = input(f"  {role}: Enter 2 moves (e.g. RU, LD, WW): ").strip().upper()
        if not s:
            s = "WW"
        moves = _parse_moves(s)
        if len(moves) >= 2:
            return moves
        print("  Use R/L/U/D/W (e.g. RU or R U)")


def _try_move(grid, r, c, dr, dc):
    """Return (new_r, new_c) if valid move; else (r, c) if wall."""
    nr, nc = r + dr, c + dc
    cell = get_cell(grid, nr, nc)
    if cell == WALL:
        return r, c  # blocked, stay put
    return nr, nc


def _ai_warden_moves(grid, hero_pos, warden_pos, goal_pos, hero_has_shield, difficulty):
    """AI Warden chooses 2 moves. Returns [(dr,dc), (dr,dc)]."""
    hr, hc = hero_pos
    wr, wc = warden_pos
    gr, gc = goal_pos

    dirs = [(0, 1), (0, -1), (-1, 0), (1, 0)]
    random.shuffle(dirs)

    def toward(a, b):
        """Step toward a from b. Returns (dr, dc)."""
        dr = 0 if a[0] == b[0] else (1 if a[0] > b[0] else -1)
        dc = 0 if a[1] == b[1] else (1 if a[1] > b[1] else -1)
        return dr, dc

    def valid_step(r, c, dr, dc):
        nr, nc = r + dr, c + dc
        return get_cell(grid, nr, nc) != WALL

    moves = []
    if difficulty == "easy":
        # Random moves
        for _ in range(2):
            random.shuffle(dirs)
            for dr, dc in dirs:
                if valid_step(warden_pos[0] + sum(m[0] for m in moves),
                             warden_pos[1] + sum(m[1] for m in moves), dr, dc):
                    moves.append((dr, dc))
                    break
            else:
                moves.append((0, 0))
    elif difficulty == "medium":
        # 50% toward hero, 50% random
        for i in range(2):
            cr = wr + sum(m[0] for m in moves)
            cc = wc + sum(m[1] for m in moves)
            if random.random() < 0.5:
                dr, dc = toward(hero_pos, (cr, cc))
                if (dr or dc) and valid_step(cr, cc, dr, dc):
                    moves.append((dr, dc))
                else:
                    for dr, dc in dirs:
                        if valid_step(cr, cc, dr, dc):
                            moves.append((dr, dc))
                            break
                    else:
                        moves.append((0, 0))
            else:
                for dr, dc in dirs:
                    if valid_step(cr, cc, dr, dc):
                        moves.append((dr, dc))
                        break
                else:
                    moves.append((0, 0))
    else:
        # Hard: pathfind toward hero, try to intercept
        for i in range(2):
            cr = wr + sum(m[0] for m in moves)
            cc = wc + sum(m[1] for m in moves)
            dr, dc = toward(hero_pos, (cr, cc))
            if (dr or dc) and valid_step(cr, cc, dr, dc):
                moves.append((dr, dc))
            else:
                for dr, dc in dirs:
                    if valid_step(cr, cc, dr, dc):
                        moves.append((dr, dc))
                        break
                else:
                    moves.append((0, 0))
    return moves[:2]


def _draw_blind_duel(grid, hero_pos, warden_pos, hero_hp, turn, last_msg,
                     hero_has_shield, warden_stunned, ping_visible):
    """Draw grid with Hero and Warden."""
    display = [list(row) for row in grid]
    hr, hc = hero_pos
    wr, wc = warden_pos
    for r, row in enumerate(display):
        for c, cell in enumerate(row):
            if (r, c) == (hr, hc):
                display[r][c] = HERO_CHAR
            elif (r, c) == (wr, wc):
                display[r][c] = WARDEN_CHAR
            elif cell in (HERO_CHAR, WARDEN_CHAR):
                display[r][c] = FLOOR
    for r, row in enumerate(display):
        line = ""
        for c, cell in enumerate(row):
            if (r, c) == (hr, hc):
                line += _P + HERO_CHAR + _C
            elif (r, c) == (wr, wc):
                line += WARDEN_COLOR + WARDEN_CHAR + _C
            else:
                line += _color_cell(cell)
        print("  " + line)
    print()
    print(f"  Hero HP: {hero_hp}/{MAX_HP}   Turn: {turn}")
    if hero_has_shield:
        print("  [Mirror Shield ready]")
    if warden_stunned:
        print("  Warden is STUNNED this turn!")
    if ping_visible:
        print("  *** PING: Hero revealed in 3x3! ***")
    if last_msg:
        print(f"  >> {last_msg}")
    print()


def _resolve_turn(grid, hero_pos, warden_pos, hero_moves, warden_moves,
                  hero_hp, hero_has_shield, warden_stunned):
    """
    Execute both move sequences. Return (hero_pos, warden_pos, hero_hp,
    hero_used_shield, warden_stunned_next, msg).
    - Tag: Warden lands on Hero. Hero -1 HP (or Mirror Shield blocks).
    - Clash: Both land on same square. Hero -1 HP, Warden pushed back 2.
    - Mirror Shield: If Hero uses and Warden would hit, Warden stunned 1 turn.
    """
    hr, hc = hero_pos
    wr, wc = warden_pos
    used_shield = False
    warden_stunned_next = False

    for i in range(2):
        hdr, hdc = hero_moves[i]
        wdr, wdc = warden_moves[i]
        if warden_stunned and i == 0:
            wdr, wdc = 0, 0  # Warden skips first move when stunned

        nhr, nhc = _try_move(grid, hr, hc, hdr, hdc)
        nwr, nwc = _try_move(grid, wr, wc, wdr, wdc)

        # Collision: same final square (Clash)
        if (nhr, nhc) == (nwr, nwc):
            if hero_has_shield and not used_shield:
                used_shield = True
                warden_stunned_next = True
                nwr, nwc = wr, wc  # Warden stays put
                return (nhr, nhc), (nwr, nwc), hero_hp, True, True, "Mirror Shield! Warden stunned!"
            hero_hp -= 1
            back_dr = -wdr * 2 if wdr else 0
            back_dc = -wdc * 2 if wdc else 0
            nwr2 = nwr + back_dr
            nwc2 = nwc + back_dc
            if 0 <= nwr2 < len(grid) and 0 <= nwc2 < len(grid[0]) and get_cell(grid, nwr2, nwc2) != WALL:
                nwr, nwc = nwr2, nwc2
            _play_sfx(sfx_hurt)
            return (nhr, nhc), (nwr, nwc), hero_hp, used_shield, False, "CLASH! Hero -1 HP, Warden pushed back!"

        # Tag: Warden landed on Hero's previous square (Hero moved away)
        if (nwr, nwc) == (hr, hc) and (nhr, nhc) != (hr, hc):
            if hero_has_shield and not used_shield:
                used_shield = True
                warden_stunned_next = True
                nwr, nwc = wr, wc
                return (nhr, nhc), (nwr, nwc), hero_hp, True, True, "Mirror Shield! Warden predicted wrong!"
            hero_hp -= 1
            _play_sfx(sfx_hurt)
            return (nhr, nhc), (nwr, nwc), hero_hp, used_shield, False, "TAG! Warden predicted your move. Hero -1 HP!"

        # Tag: Hero stayed, Warden moved onto Hero
        if (nwr, nwc) == (hr, hc) and (hdr, hdc) == (0, 0):
            if hero_has_shield and not used_shield:
                used_shield = True
                warden_stunned_next = True
                nwr, nwc = wr, wc
                return (nhr, nhc), (nwr, nwc), hero_hp, True, True, "Mirror Shield! Warden's tag blocked!"
            hero_hp -= 1
            _play_sfx(sfx_hurt)
            return (nhr, nhc), (nwr, nwc), hero_hp, used_shield, False, "TAG! Warden caught you. Hero -1 HP!"

        hr, hc = nhr, nhc
        wr, wc = nwr, nwc

    return (hr, hc), (wr, wc), hero_hp, used_shield, False, "Moves resolved."


def _run_blind_duel_level(level_num, grid, hero_hp, hero_has_shield, two_player, difficulty):
    """Run one Blind Duel level. Returns (hero_hp, hero_has_shield, won_level)."""
    grid = [list(row) for row in grid]
    hero_pos = find_cells(grid, HERO_CHAR)[0]
    warden_pos = find_cells(grid, WARDEN_CHAR)[0]
    goals = find_cells(grid, GOAL_CHAR)
    goal = goals[0] if goals else (len(grid) - 2, len(grid[0]) - 2)

    set_cell(grid, hero_pos[0], hero_pos[1], FLOOR)
    set_cell(grid, warden_pos[0], warden_pos[1], FLOOR)

    turn = 0
    warden_stunned = False
    last_msg = ""
    ping_visible = False
    ping_cooldown = 0

    while True:
        clear_screen()
        print(f"  BLIND DUEL — Level {level_num + 1}")
        print("  Hero (@) vs Warden (W). Both lock in 2 moves. R/L/U/D/W")
        print()
        _draw_blind_duel(grid, hero_pos, warden_pos, hero_hp, turn,
                         last_msg, hero_has_shield, warden_stunned, ping_visible)

        if hero_pos == goal:
            _play_sfx(sfx_goal)
            return hero_hp, hero_has_shield, True

        if hero_hp <= 0:
            return hero_hp, hero_has_shield, False

        # Ping: every 3 turns, Warden can ping (2-player: Warden chooses; vs AI: AI pings on hard)
        can_ping = turn > 0 and turn % 3 == 0 and ping_cooldown <= 0
        if can_ping and two_player:
            p = input("  Warden: Ping to reveal Hero in 3x3? (y/n): ").strip().lower()
            if p == "y":
                ping_visible = True
                ping_cooldown = 3
        elif can_ping and not two_player and difficulty == "hard":
            ping_visible = True
            ping_cooldown = 3

        # Commit phase
        if two_player:
            print("  Hero: enter moves (Warden look away)")
            hero_moves = _get_move_pair("Hero")
            print()
            print("  Warden: enter moves (Hero look away)")
            warden_moves = _get_move_pair("Warden")
        else:
            hero_moves = _get_move_pair("Hero")
            warden_moves = _ai_warden_moves(
                grid, hero_pos, warden_pos, goal,
                hero_has_shield, difficulty
            )
            s = "".join(_REV_MOVE.get(m, "W") for m in warden_moves)
            print(f"  Warden (AI) chose: {s}")

        # Reveal
        input("\n  Press Enter to REVEAL...")
        hero_pos, warden_pos, hero_hp, used_shield, warden_stunned_next, last_msg = _resolve_turn(
            grid, hero_pos, warden_pos, hero_moves, warden_moves,
            hero_hp, hero_has_shield, warden_stunned
        )
        if used_shield:
            hero_has_shield = False
        warden_stunned = warden_stunned_next

        # Pickups: Hero grabs + (health) or $ (gold)
        cell = get_cell(grid, hero_pos[0], hero_pos[1])
        if cell == HEALTH_CHAR:
            hero_hp = min(MAX_HP, hero_hp + 1)
            set_cell(grid, hero_pos[0], hero_pos[1], FLOOR)
            last_msg = f"Health +1 (now {hero_hp}/{MAX_HP})"
            _play_sfx(sfx_move)  # pickup sound
        elif cell == GOAL_CHAR:
            pass  # Win handled at start of next loop

        turn += 1
        if ping_cooldown > 0:
            ping_cooldown -= 1
        if ping_visible and ping_cooldown < 2:
            ping_visible = False


def run_blind_duel():
    """Main entry: menu for 2-player or vs Computer."""
    clear_screen()
    print()
    print("  ╔══════════════════════════════════╗")
    print("  ║   BLIND DUEL — The Locked-In     ║")
    print("  ║   Hero (@) vs Warden (W)         ║")
    print("  ║   Both commit 2 moves. Reveal!   ║")
    print("  ╚══════════════════════════════════╝")
    print()
    print("  1 = 2 Player   (Hero vs Warden on same keyboard)")
    print("  2 = vs Computer   (Hero vs AI Warden)")
    print()
    while True:
        choice = input("  Choose (1 or 2): ").strip()
        if choice == "1":
            two_player = True
            difficulty = "medium"
            break
        if choice == "2":
            two_player = False
            print()
            print("  Easy / Medium / Hard?")
            d = input("  Difficulty (e/m/h): ").strip().lower()
            difficulty = "easy" if d == "e" else ("hard" if d == "h" else "medium")
            break
        print("  Enter 1 or 2.")
    print()
    input("  Press Enter to start...")

    hero_hp = HERO_START_HP
    hero_has_shield = True  # 1-time Mirror Shield

    for level_num in range(len(BLIND_DUEL_LEVELS)):
        grid = BLIND_DUEL_LEVELS[level_num]
        hero_hp, hero_has_shield, won = _run_blind_duel_level(
            level_num, grid, hero_hp, hero_has_shield, two_player, difficulty
        )
        if not won:
            clear_screen()
            if hero_hp <= 0:
                _play_sfx(sfx_gameover)
                print("\n  *** WARDEN WINS — HERO FELL ***")
            else:
                print("\n  *** QUIT ***")
            print(f"  Reached level {level_num + 1}")
            print()
            return
        if level_num < len(BLIND_DUEL_LEVELS) - 1:
            clear_screen()
            _play_sfx(sfx_goal)
            print(f"\n  *** LEVEL {level_num + 1} CLEAR ***")
            print(f"  Hero HP: {hero_hp}/{MAX_HP}")
            input("\n  Press Enter for next level...")

    clear_screen()
    _play_sfx(sfx_win)
    print("\n  *** HERO WINS! ***")
    print("  All levels cleared. You out-predicted the Warden.")
    print()
