import os
import random
import struct
import subprocess
import sys
import tempfile

# ---- 8-bit style sound (square wave WAV, no extra deps) ----
SAMPLE_RATE = 22050

def _make_square_wav(freq, duration_ms, volume=0.3):
    """Generate 8-bit mono WAV bytes: square wave."""
    n = int(SAMPLE_RATE * duration_ms / 1000.0)
    half_period = int(SAMPLE_RATE / (2 * freq)) or 1
    data = bytearray(n)
    for i in range(n):
        data[i] = int(127 + 127 * volume * (1 if (i // half_period) % 2 else -1))
    # WAV header (44 bytes) + data
    out = bytearray(44)
    out[0:4] = b"RIFF"
    out[4:8] = struct.pack("<I", 36 + n)
    out[8:12] = b"WAVE"
    out[12:16] = b"fmt "
    out[16:20] = struct.pack("<I", 16)
    out[20:22] = struct.pack("<H", 1)   # PCM
    out[22:24] = struct.pack("<H", 1)   # mono
    out[24:28] = struct.pack("<I", SAMPLE_RATE)
    out[28:32] = struct.pack("<I", SAMPLE_RATE)
    out[32:34] = struct.pack("<H", 1)
    out[34:36] = struct.pack("<H", 8)
    out[36:40] = b"data"
    out[40:44] = struct.pack("<I", n)
    return bytes(out) + bytes(data)

def _make_multi_note_wav(notes, volume=0.2):
    """notes = [(freq_hz, duration_ms), ...]. One WAV with all notes."""
    data = bytearray()
    for freq, duration_ms in notes:
        n = int(SAMPLE_RATE * duration_ms / 1000.0)
        half_period = int(SAMPLE_RATE / (2 * freq)) or 1
        for i in range(n):
            data.append(int(127 + 127 * volume * (1 if (i // half_period) % 2 else -1)))
    n = len(data)
    out = bytearray(44)
    out[0:4] = b"RIFF"
    out[4:8] = struct.pack("<I", 36 + n)
    out[8:12] = b"WAVE"
    out[12:16] = b"fmt "
    out[16:20] = struct.pack("<I", 16)
    out[20:22] = struct.pack("<H", 1)
    out[22:24] = struct.pack("<H", 1)
    out[24:28] = struct.pack("<I", SAMPLE_RATE)
    out[28:32] = struct.pack("<I", SAMPLE_RATE)
    out[32:34] = struct.pack("<H", 1)
    out[34:36] = struct.pack("<H", 8)
    out[36:40] = b"data"
    out[40:44] = struct.pack("<I", n)
    return bytes(out) + bytes(data)

def _play_wav_nonblocking(wav_bytes):
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            path = f.name
        if sys.platform == "darwin":
            subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        elif os.name == "nt":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            subprocess.Popen(["aplay", "-q", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        if os.name != "nt":
            try:
                os.unlink(path)
            except Exception:
                pass
    except Exception:
        pass

# Mute toggle (press m in-game)
_muted = False

def _play_sfx(sfx_func):
    if not _muted:
        sfx_func()

def sfx_move():
    _play_wav_nonblocking(_make_square_wav(440, 40, 0.15))
def sfx_wall():
    _play_wav_nonblocking(_make_square_wav(110, 80, 0.25))
def sfx_crash():
    _play_wav_nonblocking(_make_square_wav(80, 200, 0.4))
def sfx_kill():
    _play_wav_nonblocking(_make_square_wav(200, 60, 0.3))
def sfx_health():
    _play_wav_nonblocking(_make_square_wav(880, 80, 0.2))
def sfx_gold():
    _play_wav_nonblocking(_make_square_wav(660, 50, 0.2))
def sfx_hurt():
    _play_wav_nonblocking(_make_square_wav(150, 120, 0.35))
def sfx_goal():
    _play_wav_nonblocking(_make_multi_note_wav([(523, 80), (659, 80), (784, 120)]))
def sfx_gameover():
    _play_wav_nonblocking(_make_square_wav(220, 300, 0.3))
def sfx_win():
    _play_wav_nonblocking(_make_multi_note_wav([(523, 100), (659, 100), (784, 100), (1047, 200)], 0.25))

# Joystick-style: read one key (arrows, wasd, or q)
def get_key():
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"q", b"Q"):
            return "q"
        if ch in (b"m", b"M"): return "m"
        if ch in (b"w", b"W"): return "w"
        if ch in (b"a", b"A"): return "a"
        if ch in (b"s", b"S"): return "s"
        if ch in (b"d", b"D"): return "d"
        if ch == b"\xe0":  # arrow prefix on Windows
            ch2 = msvcrt.getch()
            if ch2 == b"H": return "up"
            if ch2 == b"P": return "down"
            if ch2 == b"K": return "left"
            if ch2 == b"M": return "right"
        return ""
    # Unix/macOS: arrow keys are ESC [ A/B/C/D
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        c = sys.stdin.read(1)
        if c == "\x1b":
            c2 = sys.stdin.read(1)
            if c2 == "[":
                c3 = sys.stdin.read(1)
                if c3 == "A": return "up"
                if c3 == "B": return "down"
                if c3 == "C": return "right"
                if c3 == "D": return "left"
        if c in ("q", "Q"):
            return "q"
        if c.lower() == "m":
            return "m"
        if c.lower() in ("w", "a", "s", "d"):
            return c.lower()
        return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

# . = floor, # = wall, @ = you, G = goal, E = enemy, + = health, $ = gold
LEVEL_1 = [
    "###############",
    "#...........#.#",
    "#.+.........#.#",
    "#..#######.....#",
    "#..#.....#.....#",
    "#..#.@...#.....#",
    "#..#.....#.....#",
    "#..#####.#####.#",
    "#..............#",
    "#......E....$..#",
    "#....#####.....#",
    "#....#...#.....#",
    "#....#.E.#.....#",
    "#....#...+..G..#",
    "###############",
]

LEVEL_2 = [
    "###################",
    "#.+.......$.......#",
    "#........E........#",
    "#.#####.#####.#####",
    "#.#...........#..#",
    "#.#..@.........#.#",
    "#.#.............+#",
    "#.#...E..........#",
    "#.#####.#####....#",
    "#...........#....#",
    "#.....E......#....#",
    "#....#####...#....#",
    "#....#...+.#.#....#",
    "#....#.....#.#.$..#",
    "#####.......###G###",
    "###################",
]

LEVEL_3 = [
    "#####################",
    "#.+.$.......$.......+#",
    "#.....E...E...E......#",
    "#####.#####.#####.#####",
    "#.#...........#.....#",
    "#.#...........#.....#",
    "#.#....@......#.....#",
    "#.#...........#.....#",
    "#.#...E...E....#.....#",
    "#.#####.#####.#.....#",
    "#..............$....#",
    "#......E............#",
    "#.....#####.........#",
    "#.....#...+.#.......#",
    "#.....#.....#...E...#",
    "#####.#####.#####.#####",
    "#.$.................G#",
    "#####################",
]

LEVELS = [LEVEL_1, LEVEL_2, LEVEL_3]

GOAL_CHAR = "G"
ENEMY_CHAR = "E"
HEALTH_CHAR = "+"
GOLD_CHAR = "$"
FLOOR = "."
WALL = "#"
PLAYER_CHAR = "@"
TRAIL_CHAR = "="   # Tron mode: light trail (death to touch)

# ANSI colors for grid (8-bit vibe)
_C = "\033[0m"   # reset
_P = "\033[96m"  # player cyan
_E = "\033[91m"  # enemy red
_G = "\033[92m"  # goal / health green
_Y = "\033[93m"  # gold yellow
_D = "\033[2m"   # dim (wall, trail)

def _color_cell(c):
    if c == PLAYER_CHAR: return _P + c + _C
    if c == ENEMY_CHAR: return _E + c + _C
    if c == GOAL_CHAR: return _G + c + _C
    if c == HEALTH_CHAR: return _G + c + _C
    if c == GOLD_CHAR: return _Y + c + _C
    if c == WALL: return _D + c + _C
    if c == TRAIL_CHAR: return _D + c + _C
    return c

def _draw_row(row):
    return "".join(_color_cell(c) for c in row)

# High score: best = most gold, then fewest turns
def _highscore_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "dungeon_highscore.txt")

def _load_highscore():
    try:
        p = _highscore_path()
        if os.path.isfile(p):
            with open(p) as f:
                lines = f.read().strip().splitlines()
            if len(lines) >= 2:
                return int(lines[0]), int(lines[1])
    except Exception:
        pass
    return None

def _save_highscore(gold, turns):
    try:
        with open(_highscore_path(), "w") as f:
            f.write(f"{gold}\n{turns}\n")
    except Exception:
        pass

def _is_better_run(gold, turns, best_gold, best_turns):
    if gold > best_gold: return True
    if gold == best_gold and turns < best_turns: return True
    return False

MAX_HP = 5
MODE_CLASSIC = "classic"
MODE_TRON = "tron"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def find_cells(grid, char):
    out = []
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == char:
                out.append((r, c))
    return out

def get_cell(grid, r, c):
    if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
        return grid[r][c]
    return WALL

def set_cell(grid, r, c, char):
    if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
        grid[r][c] = char

def move_enemies(grid, enemies, pr, pc, tron=False):
    """Enemies move; in Tron mode they leave trails and crash on trail/wall."""
    damage = 0
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    valid_cells = (FLOOR, GOAL_CHAR, HEALTH_CHAR, GOLD_CHAR)
    if tron:
        # In Tron, trail blocks movement; enemies leave trail when they move
        pass
    to_remove = []  # indices of enemies that crashed (Tron only)
    for i, (er, ec) in enumerate(enemies):
        if tron:
            # Enemy tries to move; if target is wall/trail they crash
            random.shuffle(dirs)
            moved = False
            for dr, dc in dirs:
                nr, nc = er + dr, ec + dc
                cell = get_cell(grid, nr, nc)
                if cell == PLAYER_CHAR:
                    damage += 1
                    moved = True
                    break
                if cell in valid_cells:
                    set_cell(grid, er, ec, TRAIL_CHAR)
                    set_cell(grid, nr, nc, ENEMY_CHAR)
                    enemies[i] = (nr, nc)
                    moved = True
                    break
                if cell in (WALL, TRAIL_CHAR):
                    to_remove.append(i)
                    set_cell(grid, er, ec, TRAIL_CHAR)
                    moved = True
                    break
            if moved:
                continue
            # No direction was player/valid/wall - stay put (shouldn't happen often)
            continue
        # Classic: 50% toward player, 50% random
        if random.random() < 0.5:
            toward = []
            if pr != er:
                toward.append((1 if pr > er else -1, 0))
            if pc != ec:
                toward.append((0, 1 if pc > ec else -1))
            random.shuffle(toward)
            for dr, dc in toward:
                nr, nc = er + dr, ec + dc
                cell = get_cell(grid, nr, nc)
                if cell == PLAYER_CHAR:
                    damage += 1
                    break
                if cell in valid_cells:
                    set_cell(grid, er, ec, FLOOR)
                    set_cell(grid, nr, nc, ENEMY_CHAR)
                    enemies[i] = (nr, nc)
                    break
            else:
                pass
            continue
        random.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = er + dr, ec + dc
            cell = get_cell(grid, nr, nc)
            if cell == PLAYER_CHAR:
                damage += 1
                break
            if cell in valid_cells:
                set_cell(grid, er, ec, FLOOR)
                set_cell(grid, nr, nc, ENEMY_CHAR)
                enemies[i] = (nr, nc)
                break
    for i in sorted(to_remove, reverse=True):
        enemies.pop(i)
    return damage

def run_level(level_num, grid, hp, score, gold, total_turns, mode=MODE_CLASSIC):
    """Run one level. Returns (hp, score, gold, total_turns, won_level)."""
    tron = mode == MODE_TRON
    start = find_cells(grid, PLAYER_CHAR)
    pr, pc = start[0] if start else (1, 1)
    goals = find_cells(grid, GOAL_CHAR)
    goal = goals[0] if goals else (len(grid) - 2, len(grid[0]) - 2)
    enemies = find_cells(grid, ENEMY_CHAR)
    turns = 0
    last_msg = ""

    while True:
        clear_screen()
        if tron:
            print(f"  TRON MODE   LEVEL {level_num + 1}/{len(LEVELS)}   = trail (don't touch!)   Reach G!")
        else:
            print(f"  CLASSIC   LEVEL {level_num + 1} / {len(LEVELS)}   Reach the G!")
        print()
        for row in grid:
            print(_draw_row(row))
        print()
        print(f"  HP: {hp}/{MAX_HP}   Kills: {score}   Gold: {gold}   Turn: {total_turns + turns}")
        if last_msg:
            print(f"  >> {last_msg}")
        print()
        print("  Move: arrows or w/a/s/d   Mute: m   Quit: q")

        if (pr, pc) == goal:
            _play_sfx(sfx_goal)
            return hp, score, gold, total_turns + turns, True

        if hp <= 0:
            return hp, score, gold, total_turns + turns, False

        move = get_key()
        if move == "q":
            return hp, score, gold, total_turns + turns, False
        if move == "m":
            global _muted
            _muted = not _muted
            last_msg = "Sound muted." if _muted else "Sound on."
            continue

        dr, dc = 0, 0
        if move in ("up", "w"): dr = -1
        elif move in ("down", "s"): dr = 1
        elif move in ("left", "a"): dc = -1
        elif move in ("right", "d"): dc = 1
        else:
            continue  # ignore other keys, just re-draw

        nr, nc = pr + dr, pc + dc
        cell = get_cell(grid, nr, nc)

        if cell == WALL:
            if tron:
                _play_sfx(sfx_crash)
                last_msg = "CRASH! Hit wall."
                hp = 0
            else:
                _play_sfx(sfx_wall)
                last_msg = "Blocked by wall."
            continue

        if tron and cell == TRAIL_CHAR:
            _play_sfx(sfx_crash)
            last_msg = "CRASH! Hit trail."
            hp = 0
            continue

        # Leave trail (Tron) or clear cell (Classic)
        if tron:
            set_cell(grid, pr, pc, TRAIL_CHAR)
        else:
            set_cell(grid, pr, pc, GOAL_CHAR if (pr, pc) == goal else FLOOR)

        if cell == ENEMY_CHAR:
            _play_sfx(sfx_kill)
            enemies = [(r, c) for (r, c) in enemies if (r, c) != (nr, nc)]
            set_cell(grid, nr, nc, FLOOR)
            score += 1
            hp -= 1
            last_msg = "You killed an enemy! (-1 HP)"
        elif cell == HEALTH_CHAR:
            _play_sfx(sfx_health)
            set_cell(grid, nr, nc, FLOOR)
            hp = min(MAX_HP, hp + 1)
            last_msg = f"Health +1 (now {hp}/{MAX_HP})"
        elif cell == GOLD_CHAR:
            _play_sfx(sfx_gold)
            set_cell(grid, nr, nc, FLOOR)
            gold += 1
            last_msg = f"Gold +1 (total {gold})"
        else:
            _play_sfx(sfx_move)
            last_msg = ""

        pr, pc = nr, nc
        set_cell(grid, pr, pc, PLAYER_CHAR)

        turns += 1
        dmg = move_enemies(grid, enemies, pr, pc, tron=tron)
        if dmg > 0:
            _play_sfx(sfx_hurt)
            hp -= dmg
            last_msg = f"Enemy hit you! (-{dmg} HP)"
        elif not last_msg:
            last_msg = "Moved." if not tron else "Moved. Trail left behind."

def run():
    clear_screen()
    print()
    print("  ╔══════════════════════════╗")
    print("  ║   DUNGEON CRAWLER        ║")
    print("  ║   Reach G. Kill E.       ║")
    print("  ║   + health   $ gold      ║")
    print("  ╚══════════════════════════╝")
    print("  by Mark Kaminsky")
    print()
    print("  1 = Classic   (no trail)")
    print("  2 = Tron     (you leave trail = ; don't crash into it!)")
    print("  3 = Blind Duel   (2-player or vs Computer — simultaneous moves!)")
    print()
    while True:
        choice = input("  Choose mode (1, 2, or 3): ").strip()
        if choice == "1":
            mode = MODE_CLASSIC
            break
        if choice == "2":
            mode = MODE_TRON
            break
        if choice == "3":
            from blind_duel import run_blind_duel
            run_blind_duel()
            return
        print("  Enter 1, 2, or 3.")
    print()
    input("  Press Enter to start...")

    hp = 4
    score = 0
    gold = 0
    total_turns = 0

    for level_num in range(len(LEVELS)):
        grid = [list(row) for row in LEVELS[level_num]]
        hp, score, gold, total_turns, won = run_level(
            level_num, grid, hp, score, gold, total_turns, mode
        )
        if not won:
            clear_screen()
            if hp <= 0:
                _play_sfx(sfx_gameover)
                print("\n  *** GAME OVER — YOU DIED ***")
                print(f"  Reached level {level_num + 1}   Kills: {score}   Gold: {gold}   Turns: {total_turns}")
            else:
                print("\n  *** QUIT ***")
                print(f"  Level {level_num + 1}   Kills: {score}   Gold: {gold}   Turns: {total_turns}")
            best = _load_highscore()
            if best:
                bg, bt = best
                print(f"  Best run: {bg} gold, {bt} turns")
                if _is_better_run(gold, total_turns, bg, bt):
                    _save_highscore(gold, total_turns)
                    print("  New best! Record saved.")
            else:
                _save_highscore(gold, total_turns)
                print("  First run saved as best.")
            print()
            return
        if level_num < len(LEVELS) - 1:
            clear_screen()
            _play_sfx(sfx_goal)
            print(f"\n  *** LEVEL {level_num + 1} CLEAR ***")
            print(f"  HP: {hp}/{MAX_HP}   Kills: {score}   Gold: {gold}")
            input("\n  Press Enter for next level...")

    clear_screen()
    _play_sfx(sfx_win)
    print("\n  *** YOU WON! ***")
    print(f"  All {len(LEVELS)} levels cleared.")
    print(f"  Final: {score} kills, {gold} gold, {total_turns} turns.")
    best = _load_highscore()
    if best:
        bg, bt = best
        print(f"  Best run: {bg} gold, {bt} turns")
        if _is_better_run(gold, total_turns, bg, bt):
            _save_highscore(gold, total_turns)
            print("  New best! Record saved.")
    else:
        _save_highscore(gold, total_turns)
        print("  First run saved as best.")
    print()

if __name__ == "__main__":
    run()
