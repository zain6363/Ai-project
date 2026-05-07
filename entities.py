# ============================================================
#  BATTLE CITY — TANKS & AI AGENTS
#  AL2002 Artificial Intelligence Lab | Spring 2026
# ============================================================

import random
import math
from constants import *
from csp_map import bfs_path, astar_path, greedy_step


# ── Bullet ────────────────────────────────────────────────

class Bullet:
    __slots__ = ('x','y','dir','owner','speed','alive','color')

    def __init__(self, x, y, direction, owner, speed, color):
        self.x      = float(x)
        self.y      = float(y)
        self.dir    = direction
        self.owner  = owner      # 'player' | 'enemy'
        self.speed  = speed
        self.alive  = True
        self.color  = color

    def update(self):
        self.x += DX[self.dir] * self.speed
        self.y += DY[self.dir] * self.speed


# ── Explosion ─────────────────────────────────────────────

class Explosion:
    def __init__(self, cx, cy, max_r=40):
        self.cx    = cx
        self.cy    = cy
        self.max_r = max_r
        self.frame = 0
        self.total = 18
        self.alive = True

    def update(self):
        self.frame += 1
        if self.frame >= self.total:
            self.alive = False

    @property
    def progress(self):
        return self.frame / self.total


# ── Base Tank ─────────────────────────────────────────────

class Tank:
    def __init__(self, gx, gy, direction, color, body_color, speed_tps, fire_cd, hp):
        # Grid position (float for smooth movement)
        self.gx         = float(gx)
        self.gy         = float(gy)
        self.dir        = direction
        self.color      = color
        self.body_color = body_color

        # Movement
        self.speed      = speed_tps / FPS   # tiles per frame
        self.target_gx  = float(gx)
        self.target_gy  = float(gy)
        self.moving     = False

        # Combat
        self.hp         = hp
        self.max_hp     = hp
        self.fire_cd    = fire_cd
        self.fire_timer = random.randint(0, fire_cd)
        self.alive      = True

        # Pixel centre (computed in renderer)
        self._px = gx * TILE + TILE // 2 + GRID_OFFSET_X
        self._py = gy * TILE + TILE // 2 + GRID_OFFSET_Y

    def pixel_center(self):
        """Return smooth pixel position (centre of tank)."""
        if self.moving:
            from_gx = self.target_gx - DX[self.dir]
            from_gy = self.target_gy - DY[self.dir]
            frac = self._move_progress
            cgx = from_gx + DX[self.dir] * frac
            cgy = from_gy + DY[self.dir] * frac
        else:
            cgx, cgy = self.gx, self.gy
        px = cgx * TILE + TILE // 2 + GRID_OFFSET_X
        py = cgy * TILE + TILE // 2 + GRID_OFFSET_Y
        return int(px), int(py)

    def start_move(self, direction, nx, ny):
        self.dir         = direction
        self.target_gx   = float(nx)
        self.target_gy   = float(ny)
        self.moving      = True
        self._move_progress = 0.0

    def update_movement(self):
        if not self.moving:
            return
        self._move_progress += self.speed
        if self._move_progress >= 1.0:
            self.gx     = self.target_gx
            self.gy     = self.target_gy
            self.moving = False
            self._move_progress = 1.0

    def igx(self): return int(round(self.gx))
    def igy(self): return int(round(self.gy))


# ── Player Tank ───────────────────────────────────────────

class PlayerTank(Tank):
    def __init__(self, gx, gy, fire_cd, speed_tps):
        super().__init__(gx, gy, UP,
                         C["player"], C["player_body"],
                         speed_tps, fire_cd, hp=1)
        self.type  = 'player'
        self._move_progress = 0.0
        self.shoot_buf = False  # buffered shoot request


# ── Enemy Tanks ───────────────────────────────────────────

class EnemyTank(Tank):
    """Base enemy with shared movement + shoot logic."""

    def __init__(self, gx, gy, subtype, diff_cfg):
        params = _enemy_params(subtype, diff_cfg)
        super().__init__(gx, gy, DOWN,
                         params['color'], params['body_color'],
                         params['speed'], params['fire_cd'], params['hp'])
        self.subtype        = subtype
        self.type           = 'enemy'
        self._move_progress = 0.0
        self.path           = None
        self.path_timer     = 0
        self.stuck_timer    = 0
        self.hit_count      = 0
        self.retreating     = False
        self.retreat_timer  = 0
        self.flash_timer    = 0   # hit flash

    # -- AI entry point --
    def decide(self, map_, player, enemies, eagle_pos):
        """Called each frame; returns optional Bullet if shooting."""
        if not self.alive:
            return None
        if self.moving:
            return None  # finish current move first

        self.path_timer = max(0, self.path_timer - 1)

        if self.retreating:
            self.retreat_timer -= 1
            if self.retreat_timer <= 0:
                self.retreating = False
                self.path = None
            else:
                return None

        # Countdown fire
        self.fire_timer = max(0, self.fire_timer - 1)

        return self._ai_decide(map_, player, enemies, eagle_pos)

    def _ai_decide(self, map_, player, enemies, eagle_pos):
        raise NotImplementedError

    # ---- shared helpers ----
    def _try_shoot(self, map_, player, eagle_pos):
        """Shoot at player or eagle if line-of-sight exists."""
        if self.fire_timer > 0:
            return None
        if player and player.alive and self._los(map_, player.igx(), player.igy()):
            self._face_toward(player.igx(), player.igy())
            self.fire_timer = self.fire_cd
            return self._make_bullet()
        if self._los(map_, eagle_pos[0], eagle_pos[1]):
            self._face_toward(eagle_pos[0], eagle_pos[1])
            self.fire_timer = self.fire_cd
            return self._make_bullet()
        return None

    def _make_bullet(self):
        cx, cy = self.pixel_center()
        spd    = _bullet_speed_for_subtype(self.subtype)
        col    = C["bullet_enemy"]
        return Bullet(cx, cy, self.dir, 'enemy', spd, col)

    def _face_toward(self, tx, ty):
        dx = tx - self.igx(); dy = ty - self.igy()
        if abs(dx) >= abs(dy):
            self.dir = RIGHT if dx > 0 else LEFT
        else:
            self.dir = DOWN if dy > 0 else UP

    def _los(self, map_, tx, ty):
        x, y = self.igx(), self.igy()
        if x == tx:
            for sy in range(min(y, ty) + 1, max(y, ty)):
                t = map_[sy][x]
                if t in (BRICK, STEEL):
                    return False
            return True
        if y == ty:
            for sx in range(min(x, tx) + 1, max(x, tx)):
                t = map_[y][sx]
                if t in (BRICK, STEEL):
                    return False
            return True
        return False

    def _try_move_dir(self, direction, map_, enemies, player):
        nx = self.igx() + DX[direction]
        ny = self.igy() + DY[direction]
        if self._can_move(nx, ny, map_, enemies, player):
            self.start_move(direction, nx, ny)
            return True
        return False

    def _can_move(self, nx, ny, map_, enemies, player):
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            return False
        if map_[ny][nx] in (BRICK, STEEL, WATER, EAGLE):
            return False

        # Collision with other tanks
        for e in enemies:
            if e is not self and e.alive and e.igx() == nx and e.igy() == ny:
                return False
        if player and player.alive and player.igx() == nx and player.igy() == ny:
            return False
        return True

    def _random_move(self, map_, enemies, player):
        dirs = list(range(4))
        random.shuffle(dirs)
        for d in dirs:
            if self._try_move_dir(d, map_, enemies, player):
                return True
        return False

    def _shoot_brick_ahead(self, map_):
        """Shoot brick that's blocking path."""
        if self.fire_timer > 0:
            return None
        nx = self.igx() + DX[self.dir]
        ny = self.igy() + DY[self.dir]
        if 0 <= nx < COLS and 0 <= ny < ROWS and map_[ny][nx] == BRICK:
            self.fire_timer = self.fire_cd
            return self._make_bullet()
        return None


# ── Basic Tank (Simple Reflex + BFS) ─────────────────────

class BasicTank(EnemyTank):
    REPATH_INTERVAL = 150  # frames

    def _ai_decide(self, map_, player, enemies, eagle_pos):
        bullet = self._try_shoot(map_, player, eagle_pos)
        if bullet:
            return bullet

        # Repath periodically
        pos = (self.igx(), self.igy())
        if not self.path or self.path_timer <= 0:
            self.path = bfs_path(map_, pos, eagle_pos)
            self.path_timer = self.REPATH_INTERVAL
            self.stuck_timer = 0

        if self.path:
            nxt = self.path[0]
            dx = nxt[0] - self.igx()
            dy = nxt[1] - self.igy()
            d  = _delta_to_dir(dx, dy)

            # Brick in path? Shoot it
            b = self._shoot_brick_ahead(map_)
            if b and map_[self.igy() + DY[d]][self.igx() + DX[d]] == BRICK:
                return b

            if self._try_move_dir(d, map_, enemies, player):
                self.path.pop(0)
                self.stuck_timer = 0
            else:
                self.stuck_timer += 1
                if self.stuck_timer > 30:
                    self.path = None
        else:
            self._random_move(map_, enemies, player)
        return None


# ── Fast Tank (Goal-Based + Greedy Best-First) ────────────

class FastTank(EnemyTank):
    def _ai_decide(self, map_, player, enemies, eagle_pos):
        # Greedy: pick dir with smallest h(n) toward Eagle
        d = greedy_step(map_, (self.igx(), self.igy()), eagle_pos)
        if d >= 0:
            nx = self.igx() + DX[d]
            ny = self.igy() + DY[d]
            t  = map_[ny][nx]
            if t == BRICK:
                b = self._shoot_brick_ahead(map_)
                self.dir = d
                return b
            self._try_move_dir(d, map_, enemies, player)
        else:
            self._random_move(map_, enemies, player)

        bullet = self._try_shoot(map_, player, eagle_pos)
        return bullet


# ── Armor Tank (Model-Based Reflex + A*) ──────────────────

class ArmorTank(EnemyTank):
    REPATH_INTERVAL = 120

    def _ai_decide(self, map_, player, enemies, eagle_pos):
        # Rule: retreat on 3rd hit
        if self.retreating:
            return None

        bullet = self._try_shoot(map_, player, eagle_pos)
        if bullet:
            return bullet

        pos = (self.igx(), self.igy())
        if not self.path or self.path_timer <= 0:
            self.path = astar_path(map_, pos, eagle_pos)
            self.path_timer = self.REPATH_INTERVAL
            self.stuck_timer = 0

        if self.path:
            nxt = self.path[0]
            dx = nxt[0] - self.igx()
            dy = nxt[1] - self.igy()
            d  = _delta_to_dir(dx, dy)
            b  = self._shoot_brick_ahead(map_)
            if b:
                self.dir = d
                return b
            if self._try_move_dir(d, map_, enemies, player):
                self.path.pop(0)
                self.stuck_timer = 0
            else:
                self.stuck_timer += 1
                if self.stuck_timer > 30:
                    self.path = None
        else:
            self._random_move(map_, enemies, player)
        return None

    def on_hit(self):
        """Called when this tank takes a bullet hit."""
        self.hit_count  += 1
        self.flash_timer = 10
        if self.hit_count >= 3:
            self.retreating    = True
            self.retreat_timer = 90
            self.path          = None


# ── Power Tank (Utility-Based, BFS + aggressive fire) ─────

class PowerTank(EnemyTank):
    REPATH_INTERVAL = 100

    def _ai_decide(self, map_, player, enemies, eagle_pos):
        bullet = self._try_shoot(map_, player, eagle_pos)
        if bullet:
            return bullet
        pos = (self.igx(), self.igy())
        if not self.path or self.path_timer <= 0:
            self.path = bfs_path(map_, pos, eagle_pos)
            self.path_timer = self.REPATH_INTERVAL
        if self.path:
            nxt = self.path[0]
            d   = _delta_to_dir(nxt[0] - self.igx(), nxt[1] - self.igy())
            if self._try_move_dir(d, map_, enemies, player):
                self.path.pop(0)
            else:
                self.path = None
        else:
            self._random_move(map_, enemies, player)
        return None


# ── Boss Tank (Adversarial Minimax + Alpha-Beta) ──────────

class BossTank(EnemyTank):

    def __init__(self, gx, gy, diff_cfg):
        super().__init__(gx, gy, 'boss', diff_cfg)
        self.phase       = 1
        self.nodes_eval  = 0

    def update_phase(self):
        frac = self.hp / self.max_hp
        if frac > 0.60:
            self.phase = 1
        elif frac > 0.20:
            self.phase = 2
        else:
            self.phase = 3
        # Speed / fireCD scale with phase
        speeds = {1: 1.0, 2: 1.6, 3: 2.4}
        self.speed = speeds[self.phase] / FPS
        fire_cds   = {1: 60, 2: 40, 3: 25}
        self.fire_cd = fire_cds[self.phase]

    def _ai_decide(self, map_, player, enemies, eagle_pos):
        self.update_phase()
        depth_map = {1: 2, 2: 3, 3: 4}
        depth = depth_map[self.phase]
        self.nodes_eval = 0

        # Run minimax to choose best action
        best_score = -math.inf
        best_action = None
        alpha, beta = -math.inf, math.inf

        state = _make_state(self, player, map_)
        for action in _get_actions(state, 'boss', map_):
            child = _apply_action(state, action, 'boss', map_)
            score = self._minimax(child, depth - 1, alpha, beta, False, map_, player)
            if score > best_score:
                best_score, best_action = score, action
            alpha = max(alpha, score)

        if best_action is None:
            self._random_move(map_, enemies, player)
            return self._try_shoot(map_, player, eagle_pos)

        # Execute best_action
        if best_action[0] == 'move':
            d, nx, ny = best_action[1], best_action[2], best_action[3]
            self._try_move_dir(d, map_, enemies, player)
        elif best_action[0] == 'shoot':
            if self.fire_timer <= 0:
                self.dir = best_action[1]
                self.fire_timer = self.fire_cd
                return self._make_bullet()

        # Always try to shoot if cooldown done
        return self._try_shoot(map_, player, eagle_pos)

    def _minimax(self, state, depth, alpha, beta, maximising, map_, player_ref):
        self.nodes_eval += 1
        if depth == 0 or state['terminal']:
            return _evaluate(state, self.phase)

        if maximising:
            val = -math.inf
            for action in _get_actions(state, 'boss', map_):
                child = _apply_action(state, action, 'boss', map_)
                val = max(val, self._minimax(child, depth - 1, alpha, beta, False, map_, player_ref))
                alpha = max(alpha, val)
                if alpha >= beta:
                    break  # β-cutoff
            return val
        else:
            val = math.inf
            for action in _get_actions(state, 'player', map_):
                child = _apply_action(state, action, 'player', map_)
                val = min(val, self._minimax(child, depth - 1, alpha, beta, True, map_, player_ref))
                beta = min(beta, val)
                if alpha >= beta:
                    break  # α-cutoff
            return val


# ── Minimax state helpers ──────────────────────────────────

def _make_state(boss, player, map_):
    px = player.igx() if player and player.alive else -1
    py = player.igy() if player and player.alive else -1
    return {
        'boss_x': boss.igx(), 'boss_y': boss.igy(),
        'boss_hp': boss.hp,
        'player_x': px, 'player_y': py,
        'terminal': False,
    }


def _get_actions(state, who, map_):
    actions = []
    if who == 'boss':
        x, y = state['boss_x'], state['boss_y']
    else:
        x, y = state['player_x'], state['player_y']

    for d in range(4):
        nx, ny = x + DX[d], y + DY[d]
        if 0 <= nx < COLS and 0 <= ny < ROWS:
            t = map_[ny][nx]
            if t not in (STEEL, WATER, EAGLE):
                actions.append(('move', d, nx, ny))
    # Shoot in each direction
    for d in range(4):
        actions.append(('shoot', d))
    return actions


def _apply_action(state, action, who, map_):
    s = dict(state)
    if who == 'boss':
        if action[0] == 'move':
            s['boss_x'], s['boss_y'] = action[2], action[3]
        elif action[0] == 'shoot':
            # Simulate bullet hitting player
            d = action[1]
            bx, by = s['boss_x'], s['boss_y']
            while 0 <= bx < COLS and 0 <= by < ROWS:
                bx += DX[d]; by += DY[d]
                if map_[by][bx] if (0 <= by < ROWS and 0 <= bx < COLS) else True:
                    t = map_[by][bx] if (0 <= by < ROWS and 0 <= bx < COLS) else STEEL
                    if t in (STEEL, WATER):
                        break
                    if bx == s['player_x'] and by == s['player_y']:
                        s['terminal'] = True
                        break
                    break
    else:
        if action[0] == 'move':
            s['player_x'], s['player_y'] = action[2], action[3]
    return s


def _evaluate(state, phase):
    """Boss evaluation heuristic."""
    bx, by = state['boss_x'], state['boss_y']
    px, py = state['player_x'], state['player_y']
    if px == -1:
        return 500  # player dead

    dist  = abs(bx - px) + abs(by - py)
    score = 0

    if dist <= 3:  score += 60
    if dist <= 6:  score += 30
    score -= dist * 3

    # Phase modifiers
    if phase == 3:
        score += 40  # aggression

    score -= (10 - state['boss_hp']) * 40
    return score


# ── Factory helpers ───────────────────────────────────────

def _enemy_params(subtype, diff_cfg):
    base_spd  = diff_cfg['enemy_speed']
    base_fcd  = diff_cfg['enemy_fire_cd']
    base_bspd = diff_cfg['bullet_speed']
    p = {
        'basic': dict(color=C["basic"],  body_color=C["basic_body"],  speed=base_spd,       fire_cd=base_fcd,        hp=1),
        'fast':  dict(color=C["fast"],   body_color=C["fast_body"],   speed=base_spd*2.0,   fire_cd=int(base_fcd*.6),hp=1),
        'armor': dict(color=C["armor"],  body_color=C["armor_body"],  speed=base_spd*0.7,   fire_cd=int(base_fcd*1.2),hp=diff_cfg['armor_hp']),
        'power': dict(color=C["power"],  body_color=C["power_body"],  speed=base_spd*1.1,   fire_cd=int(base_fcd*.8),hp=2),
        'boss':  dict(color=C["boss"],   body_color=C["boss_body"],   speed=base_spd*0.6,   fire_cd=60,              hp=10),
    }
    return p.get(subtype, p['basic'])


def _bullet_speed_for_subtype(subtype):
    speeds = {'basic': 7, 'fast': 9, 'armor': 8, 'power': 9, 'boss': 11}
    return speeds.get(subtype, 7)


def make_enemy(gx, gy, subtype, diff_cfg):
    cls_map = {
        'basic': BasicTank,
        'fast':  FastTank,
        'armor': ArmorTank,
        'power': PowerTank,
        'boss':  BossTank,
    }
    cls = cls_map.get(subtype, BasicTank)
    if subtype == 'boss':
        return cls(gx, gy, diff_cfg)
    return cls(gx, gy, subtype, diff_cfg)


def _delta_to_dir(dx, dy):
    if dx == 1:  return RIGHT
    if dx == -1: return LEFT
    if dy == 1:  return DOWN
    return UP