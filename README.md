# Dungeon Crawler

**by Mark Kaminsky**

A terminal roguelike with **8-bit sound**, **joystick-style controls**, and **Tron mode**. Reach the goal, grab health and gold, and don’t let the enemies catch you.

![Python](https://img.shields.io/badge/python-3.7+-blue)  
**Play in browser:** open `index.html` in a browser, or host the folder (e.g. [GitHub Pages](https://pages.github.com/)) and share the link.

**To share:** Push this folder to a GitHub repo. Turn on Pages in the repo settings to get a public link anyone can play.

---

## How to run (terminal)

```bash
cd python-project1   # or clone the repo and cd into it
python3 main.py
```

- **Move:** Arrow keys or **W A S D**
- **Mute:** **M**
- **Quit:** **Q**

---

## Goal

- **@** = you  
- **G** = goal (reach it to finish the level)  
- **E** = enemy (stepping on one kills it but costs 1 HP)  
- **+** = health  
- **$** = gold  

Clear all 3 levels. Your best run (most gold, then fewest turns) is saved in `dungeon_highscore.txt`.

---

## Modes

1. **Classic** – No trail; enemies chase or wander.
2. **Tron** – You leave a trail (**=**). Touch the trail or a wall = crash (game over). Enemies also leave trails and can crash.

---

## Features

- 8-bit style square-wave sound effects (move, wall, pickup, kill, hurt, goal, game over, victory)
- Mute toggle (**M**) during play
- Colored terminal output (player, enemies, goal, health, gold)
- Persistent high score (best gold, then fewest turns)

---

## Making the outside world aware

- **GitHub:** Push this folder to a repo. The README and `index.html` give a clear “what it is” and “play now” for visitors.
- **GitHub Pages:** In the repo: Settings → Pages → Source = main branch, folder = root (or /docs if you put the game in `docs`). Your game will be at `https://<username>.github.io/<repo>/`.
- **itch.io:** Zip `index.html` (and any assets), upload as an HTML5 game, set “This file will be played in the browser.” Share the itch.io link.
- **Social:** Share the repo link or the GitHub Pages / itch.io link on Reddit (e.g. r/WebGames, r/IndieGaming), Twitter, or dev communities.

No server or backend required for the browser version—just open the HTML or host it anywhere static.
