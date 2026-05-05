# ============================================================
#  Module B — Search Algorithms
#  BFS, Greedy Best-First, A*
# ============================================================
from collections import deque
import heapq
from constants import *


def passable_for_tank(grid, x, y):
    """Can a tank stand on this tile (ignoring tanks)?"""
    if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
        return False
    return grid[y][x] in (EMPTY, FOREST, EAGLE)


def passable_astar(grid, x, y):
    """A* considers brick destructible (cost 3), steel/water = inf."""
    if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
        return False
    return ASTAR_COST.get(grid[y][x], float('inf')) < float('inf')


# ── BFS ───────────────────────────────────────────────────────
def bfs(grid, start, goal):
    """
    Shortest-hop path ignoring tile costs.
    Returns list of (x,y) from start→goal (exclusive start).
    Returns [] if no path.
    """
    sx, sy = start
    gx, gy = goal
    if (sx, sy) == (gx, gy):
        return []

    visited = {(sx, sy)}
    parent  = {(sx, sy): None}
    q = deque([(sx, sy)])

    while q:
        x, y = q.popleft()
        if (x, y) == (gx, gy):
            # Reconstruct
            path = []
            cur  = (gx, gy)
            while cur != (sx, sy):
                path.append(cur)
                cur = parent[cur]
            path.reverse()
            return path

        for dx, dy in DIRS:
            nx, ny = x+dx, y+dy
            if (nx, ny) in visited:
                continue
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                continue
            t = grid[ny][nx]
            if t in (EMPTY, FOREST, EAGLE, BRICK):
                visited.add((nx, ny))
                parent[(nx, ny)] = (x, y)
                q.append((nx, ny))
    return []


# ── Greedy Best-First ─────────────────────────────────────────
def greedy_next_step(grid, start, goal):
    """
    Single-step greedy: pick the neighbour with lowest Manhattan to goal.
    Does NOT compute full path — just next tile.
    Returns (nx, ny) or None.
    """
    sx, sy = start
    gx, gy = goal
    best_h   = float('inf')
    best_pos = None

    for dx, dy in DIRS:
        nx, ny = sx+dx, sy+dy
        if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
            continue
        t = grid[ny][nx]
        if t in (EMPTY, FOREST, EAGLE, BRICK):
            h = abs(nx - gx) + abs(ny - gy)
            if h < best_h:
                best_h   = h
                best_pos = (nx, ny)
    return best_pos


# ── A* ────────────────────────────────────────────────────────
def astar(grid, start, goal):
    """
    Cost-aware A* using ASTAR_COST table.
    Brick = 3, Steel/Water = inf.
    Returns path list (x,y) from start→goal (exclusive start).
    """
    sx, sy = start
    gx, gy = goal
    if (sx, sy) == (gx, gy):
        return []

    def h(x, y):
        return abs(x - gx) + abs(y - gy)

    open_set = []
    heapq.heappush(open_set, (h(sx, sy), 0, (sx, sy)))
    came_from = {(sx, sy): None}
    g_score   = {(sx, sy): 0}

    while open_set:
        f, g, (x, y) = heapq.heappop(open_set)

        if (x, y) == (gx, gy):
            path = []
            cur  = (gx, gy)
            while cur != (sx, sy):
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return path

        for dx, dy in DIRS:
            nx, ny = x+dx, y+dy
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                continue
            cost = ASTAR_COST.get(grid[ny][nx], float('inf'))
            if cost == float('inf'):
                continue
            new_g = g_score[(x, y)] + cost
            if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                g_score[(nx, ny)]  = new_g
                came_from[(nx, ny)] = (x, y)
                f_new = new_g + h(nx, ny)
                heapq.heappush(open_set, (f_new, new_g, (nx, ny)))
    return []


# ── Minimax + Alpha-Beta (Boss) ───────────────────────────────
class MinimaxSearch:
    """
    Minimax with Alpha-Beta pruning for the Boss Tank.
    Tracks nodes_evaluated and pruned_nodes for report metrics.
    """
    def __init__(self):
        self.nodes_no_pruning  = 0
        self.nodes_with_pruning = 0

    def evaluate(self, boss_pos, player_pos, grid, boss_hp, player_hp):
        bx, by = boss_pos
        px, py = player_pos
        score  = 0

        dist = abs(bx-px) + abs(by-py)
        if dist <= 3:
            score += 60
        score += max(0, 20 - dist)   # proximity bonus

        # Line of sight
        if bx == px:
            clear = all(
                grid[min(by,py)+i][bx] not in (BRICK, STEEL, WATER)
                for i in range(1, abs(by-py))
            )
            if clear:
                score += 50
        elif by == py:
            clear = all(
                grid[by][min(bx,px)+i] not in (BRICK, STEEL, WATER)
                for i in range(1, abs(bx-px))
            )
            if clear:
                score += 50

        # Cover check
        for dx, dy in DIRS:
            nx, ny = bx+dx, by+dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if grid[ny][nx] == STEEL:
                    score += 30
                    break

        # HP factors
        score += (10 - boss_hp)   * -40
        score += (3  - player_hp) *  20
        return score

    def get_boss_actions(self, boss_pos, grid):
        bx, by = boss_pos
        actions = []
        for dx, dy in DIRS:
            nx, ny = bx+dx, by+dy
            if passable_for_tank(grid, nx, ny):
                actions.append(('move', (nx, ny)))
        actions.append(('shoot', boss_pos))
        return actions

    def get_player_actions(self, player_pos, grid):
        px, py = player_pos
        actions = []
        for dx, dy in DIRS:
            nx, ny = px+dx, py+dy
            if passable_for_tank(grid, nx, ny):
                actions.append(('move', (nx, ny)))
        actions.append(('shoot', player_pos))
        return actions

    def minimax(self, depth, boss_pos, player_pos, grid, boss_hp, player_hp,
                alpha, beta, is_max, use_pruning=True):
        self.nodes_with_pruning += 1

        if depth == 0:
            return self.evaluate(boss_pos, player_pos, grid, boss_hp, player_hp), None

        if is_max:
            best_val = float('-inf')
            best_act = None
            for action in self.get_boss_actions(boss_pos, grid):
                new_boss = action[1] if action[0] == 'move' else boss_pos
                val, _   = self.minimax(depth-1, new_boss, player_pos, grid,
                                        boss_hp, player_hp, alpha, beta,
                                        False, use_pruning)
                if val > best_val:
                    best_val = val
                    best_act = action
                if use_pruning:
                    alpha = max(alpha, val)
                    if alpha >= beta:
                        break
            return best_val, best_act
        else:
            best_val = float('inf')
            best_act = None
            for action in self.get_player_actions(player_pos, grid):
                new_player = action[1] if action[0] == 'move' else player_pos
                val, _     = self.minimax(depth-1, boss_pos, new_player, grid,
                                          boss_hp, player_hp, alpha, beta,
                                          True, use_pruning)
                if val < best_val:
                    best_val = val
                    best_act = action
                if use_pruning:
                    beta = min(beta, val)
                    if alpha >= beta:
                        break
            return best_val, best_act

    def best_action(self, boss_pos, player_pos, grid, boss_hp, player_hp, depth):
        self.nodes_with_pruning = 0
        val, action = self.minimax(depth, boss_pos, player_pos, grid,
                                   boss_hp, player_hp,
                                   float('-inf'), float('inf'), True)
        return action, self.nodes_with_pruning