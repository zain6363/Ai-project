# ============================================================
#  BATTLE CITY — MAP GENERATION (CSP Module A)
#  AL2002 Artificial Intelligence Lab | Spring 2026
# ============================================================

import random
from collections import deque
from constants import *

def generate_map(level: int, difficulty: str) -> list[list[int]]:
    """
    CSP-inspired map generator.
    Constraints:
      1. Eagle surrounded by at least 1 ring of Brick
      2. Valid BFS path from every spawn to Eagle
      3. Fairness: no spawn within 10 tiles of player start
      4. Density: <= 40% wall tiles
      5. Water may not block only path to Eagle
    """
    attempts = 0
    while True:
        attempts += 1
        m = _attempt_generate(level, difficulty)
        if m is not None:
            return m
        if attempts > 20:
            return _safe_fallback(level)


def _attempt_generate(level: int, difficulty: str) -> list[list[int]] | None:
    map_ = [[EMPTY] * COLS for _ in range(ROWS)]

    # Place Eagle
    map_[24][12] = EAGLE

    # Eagle protection ring (Constraint 1)
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            ny, nx = 24 + dy, 12 + dx
            if 0 <= ny < ROWS and 0 <= nx < COLS and (ny, nx) != (24, 12):
                map_[ny][nx] = BRICK

    # Level-specific terrain density
    if level == 1:
        brick_p, steel_p, water_p, forest_p = 0.20, 0.03, 0.03, 0.07
    elif level == 2:
        brick_p, steel_p, water_p, forest_p = 0.14, 0.10, 0.03, 0.04
    else:  # Boss
        brick_p, steel_p, water_p, forest_p = 0.10, 0.08, 0.02, 0.03

    wall_count = 0
    total_fillable = 0

    for y in range(1, ROWS - 1):
        for x in range(COLS):
            if map_[y][x] != EMPTY:
                continue
            # Skip spawn clear zones (top 2 rows)
            if y < 2:
                continue
            # Skip Eagle area
            if abs(x - 12) < 3 and y > 22:
                continue
            # Skip player zone (Constraint 3)
            if x < 7 and y > 21:
                continue

            total_fillable += 1
            r = random.random()
            if r < brick_p:
                map_[y][x] = BRICK
                wall_count += 1
            elif r < brick_p + steel_p:
                map_[y][x] = STEEL
                wall_count += 1
            elif r < brick_p + steel_p + water_p:
                map_[y][x] = WATER
            elif r < brick_p + steel_p + water_p + forest_p:
                map_[y][x] = FOREST

    # Constraint 4: density check
    if total_fillable > 0 and wall_count / total_fillable > 0.40:
        return None

    # Constraint 2 + 5: reachability — ensure paths exist, clear steel/water blockers
    eagle_pos = (12, 24)
    for sx, sy in SPAWN_POINTS:
        if not _bfs_reachable(map_, (sx, sy), eagle_pos):
            _carve_path(map_, (sx, sy), eagle_pos)

    # Final reachability check
    for sx, sy in SPAWN_POINTS:
        if not _bfs_reachable(map_, (sx, sy), eagle_pos):
            return None

    return map_


def _bfs_reachable(map_, start: tuple, goal: tuple) -> bool:
    sx, sy = start
    gx, gy = goal
    visited = set()
    q = deque([(sx, sy)])
    visited.add((sx, sy))
    while q:
        x, y = q.popleft()
        if (x, y) == (gx, gy):
            return True
        for d in range(4):
            nx, ny = x + DX[d], y + DY[d]
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            if (nx, ny) in visited:
                continue
            t = map_[ny][nx]
            if t in (STEEL, WATER):
                continue
            visited.add((nx, ny))
            q.append((nx, ny))
    return False


def _carve_path(map_, start: tuple, goal: tuple):
    """Carve a guaranteed passable path from start to goal."""
    x, y = start
    gx, gy = goal
    while y != gy:
        y += 1 if y < gy else -1
        if map_[y][x] in (STEEL, WATER):
            map_[y][x] = EMPTY
    while x != gx:
        x += 1 if x < gx else -1
        if map_[y][x] in (STEEL, WATER, EAGLE):
            map_[y][x] = EMPTY


def _safe_fallback(level: int) -> list[list[int]]:
    """Minimal open map used if CSP fails repeatedly."""
    m = [[EMPTY] * COLS for _ in range(ROWS)]
    m[24][12] = EAGLE
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            ny, nx = 24 + dy, 12 + dx
            if 0 <= ny < ROWS and 0 <= nx < COLS and (ny, nx) != (24, 12):
                m[ny][nx] = BRICK
    # Scatter some bricks
    for _ in range(60):
        x, y = random.randint(0, COLS - 1), random.randint(3, 20)
        m[y][x] = BRICK
    return m


# ---- Pathfinding helpers used by AI ----

def bfs_path(map_: list[list[int]], start: tuple, goal: tuple) -> list[tuple] | None:
    """BFS: shortest hop path ignoring brick cost."""
    sx, sy = start
    gx, gy = goal
    visited = {(sx, sy): None}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        if (x, y) == (gx, gy):
            return _reconstruct(visited, start, goal)
        for d in range(4):
            nx, ny = x + DX[d], y + DY[d]
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            if (nx, ny) in visited:
                continue
            t = map_[ny][nx]
            if t in (STEEL, WATER):
                continue
            visited[(nx, ny)] = (x, y)
            q.append((nx, ny))
    return None


def astar_path(map_: list[list[int]], start: tuple, goal: tuple) -> list[tuple] | None:
    """A*: cost-aware — brick=3, steel=inf, water=inf, else=1."""
    import heapq
    cost_map = {EMPTY: 1, FOREST: 1, BRICK: 3, STEEL: 9999, WATER: 9999}
    gx, gy = goal
    sx, sy = start
    h = lambda x, y: abs(x - gx) + abs(y - gy)
    open_set = [(h(sx, sy), 0, sx, sy, [])]
    best_g = {(sx, sy): 0}
    while open_set:
        f, g, x, y, path = heapq.heappop(open_set)
        if (x, y) == (gx, gy):
            return path
        for d in range(4):
            nx, ny = x + DX[d], y + DY[d]
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            t = map_[ny][nx]
            c = cost_map.get(t, 9999)
            if c >= 9999:
                continue
            ng = g + c
            if (nx, ny) not in best_g or best_g[(nx, ny)] > ng:
                best_g[(nx, ny)] = ng
                heapq.heappush(open_set, (ng + h(nx, ny), ng, nx, ny, path + [(nx, ny)]))
    return None


def greedy_step(map_: list[list[int]], pos: tuple, goal: tuple) -> int:
    """Greedy Best-First: return direction with lowest Manhattan heuristic."""
    x, y = pos
    gx, gy = goal
    best_d, best_h = -1, float('inf')
    for d in range(4):
        nx, ny = x + DX[d], y + DY[d]
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            continue
        t = map_[ny][nx]
        if t in (STEEL, WATER):
            continue
        hv = abs(nx - gx) + abs(ny - gy)
        if hv < best_h:
            best_h, best_d = hv, d
    return best_d


def _reconstruct(visited: dict, start: tuple, goal: tuple) -> list[tuple]:
    path = []
    cur = goal
    while cur != start:
        path.append(cur)
        cur = visited[cur]
    path.reverse()
    return path