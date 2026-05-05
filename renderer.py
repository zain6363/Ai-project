# ============================================================
#  BATTLE CITY — RENDERER
#  AL2002 Artificial Intelligence Lab | Spring 2026
# ============================================================

import pygame
import math
import os
from constants import *


def _load_font(name, size):
    try:
        return pygame.font.SysFont(name, size, bold=False)
    except Exception:
        return pygame.font.Font(None, size)


class Renderer:

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._init_fonts()
        self._build_tile_surfaces()
        self._anim_tick = 0

    def _init_fonts(self):
        # Try to find a nice pixel/retro font on the system
        candidates = ['couriernew', 'lucidaconsole', 'consolas', 'dejavusansmono', 'monospace']
        mono = None
        for c in candidates:
            f = pygame.font.match_font(c)
            if f:
                mono = f
                break

        self.font_huge   = pygame.font.Font(mono, 52)
        self.font_big    = pygame.font.Font(mono, 32)
        self.font_med    = pygame.font.Font(mono, 20)
        self.font_small  = pygame.font.Font(mono, 14)
        self.font_tiny   = pygame.font.Font(mono, 11)
        self.font_title  = pygame.font.Font(mono, 64)

    # ── Tile surface cache ────────────────────────────────

    def _build_tile_surfaces(self):
        T = TILE
        self._tiles = {}

        # EMPTY
        s = pygame.Surface((T, T))
        s.fill(C["empty"])
        # Subtle grid dot
        pygame.draw.circle(s, (22, 22, 32), (T // 2, T // 2), 1)
        self._tiles[EMPTY] = s

        # BRICK
        s = pygame.Surface((T, T))
        s.fill(C["brick_dark"])
        hw = T // 2 - 1
        rects = [(1, 1, hw, hw), (hw + 2, hw + 2, hw, hw),
                 (hw + 2, 1, hw, hw), (1, hw + 2, hw, hw)]
        cols  = [C["brick_light"], C["brick_light"],
                 (200, 70, 50), (200, 70, 50)]
        for r, col in zip(rects, cols):
            pygame.draw.rect(s, col, r)
        # mortar lines
        pygame.draw.line(s, C["brick_dark"], (0, T//2), (T, T//2), 1)
        pygame.draw.line(s, C["brick_dark"], (T//2, 0), (T//2, T), 1)
        self._tiles[BRICK] = s

        # STEEL
        s = pygame.Surface((T, T))
        s.fill(C["steel_dark"])
        pygame.draw.rect(s, C["steel_light"], (2, 2, T - 4, T - 4))
        pygame.draw.line(s, (180, 200, 220), (2, 2), (T - 2, 2), 2)
        pygame.draw.line(s, (180, 200, 220), (2, 2), (2, T - 2), 2)
        pygame.draw.line(s, (30, 40, 55), (T - 3, 2), (T - 3, T - 3), 1)
        pygame.draw.line(s, (30, 40, 55), (2, T - 3), (T - 3, T - 3), 1)
        pygame.draw.circle(s, (200, 220, 240), (T // 2, T // 2), 3)
        self._tiles[STEEL] = s

        # WATER (animated — store base + alt)
        for variant in (0, 1):
            s = pygame.Surface((T, T))
            s.fill(C["water_b"])
            offset = 4 if variant == 0 else 0
            for row in range(3):
                y = 4 + row * 8 + offset // 2
                pygame.draw.line(s, C["water_a"], (2, y), (T - 2, y), 2)
            self._tiles[(WATER, variant)] = s

        # FOREST
        s = pygame.Surface((T, T), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, C["forest_b"], (0, 0, T, T))
        for cx, cy, r in [(6, 6, 5), (T-6, 6, 5), (T//2, T//2-3, 6),
                           (4, T-6, 4), (T-4, T-6, 4)]:
            pygame.draw.circle(s, C["forest_a"], (cx, cy), r)
        for cx, cy, r in [(7, 7, 3), (T-7, 7, 3), (T//2, T//2-3, 4)]:
            pygame.draw.circle(s, C["forest_c"], (cx, cy), r)
        self._tiles[FOREST] = s

        # FOREST overlay (semi-transparent to hide tanks)
        so = pygame.Surface((T, T), pygame.SRCALPHA)
        so.fill((0, 0, 0, 0))
        pygame.draw.rect(so, (*C["forest_b"], 200), (0, 0, T, T))
        for cx, cy, r in [(6, 6, 5), (T-6, 6, 5), (T//2, T//2-3, 6),
                           (4, T-6, 4), (T-4, T-6, 4)]:
            pygame.draw.circle(so, (*C["forest_a"], 220), (cx, cy), r)
        self._tiles['forest_overlay'] = so

        # EAGLE (normal)
        s = pygame.Surface((T, T))
        s.fill(C["empty"])
        self._draw_eagle_on(s, alive=True)
        self._tiles[EAGLE] = s

        # EAGLE (destroyed)
        sd = pygame.Surface((T, T))
        sd.fill(C["empty"])
        self._draw_eagle_on(sd, alive=False)
        self._tiles['eagle_dead'] = sd

    def _draw_eagle_on(self, surf, alive):
        T = TILE
        if alive:
            # Eagle body (bold geometric design)
            pygame.draw.polygon(surf, C["eagle_gold"],
                [(T//2, 3), (T-4, T-4), (T//2, T-8), (4, T-4)])
            pygame.draw.polygon(surf, C["eagle_dark"],
                [(T//2, 6), (T-7, T-6), (T//2, T-10), (7, T-6)])
            pygame.draw.circle(surf, C["eagle_gold"], (T//2, T//2), 4)
        else:
            pygame.draw.line(surf, C["hud_red"], (4, 4), (T-4, T-4), 3)
            pygame.draw.line(surf, C["hud_red"], (T-4, 4), (4, T-4), 3)

    # ── Tick ─────────────────────────────────────────────

    def tick(self):
        self._anim_tick += 1

    # ── Map drawing ───────────────────────────────────────

    def draw_map(self, map_, eagle_alive):
        water_v = (self._anim_tick // 20) % 2
        for y in range(ROWS):
            for x in range(COLS):
                t = map_[y][x]
                px = GRID_OFFSET_X + x * TILE
                py = GRID_OFFSET_Y + y * TILE
                if t == WATER:
                    self.screen.blit(self._tiles[(WATER, water_v)], (px, py))
                elif t == EAGLE:
                    key = EAGLE if eagle_alive else 'eagle_dead'
                    self.screen.blit(self._tiles[key], (px, py))
                elif t == FOREST:
                    self.screen.blit(self._tiles[EMPTY], (px, py))  # ground under forest
                else:
                    surf = self._tiles.get(t)
                    if surf:
                        self.screen.blit(surf, (px, py))
                    else:
                        pygame.draw.rect(self.screen, C["empty"], (px, py, TILE, TILE))

    def draw_forest_overlay(self, map_):
        """Call AFTER drawing tanks so forest hides them."""
        for y in range(ROWS):
            for x in range(COLS):
                if map_[y][x] == FOREST:
                    px = GRID_OFFSET_X + x * TILE
                    py = GRID_OFFSET_Y + y * TILE
                    self.screen.blit(self._tiles['forest_overlay'], (px, py))

    # ── Tank drawing ──────────────────────────────────────

    def draw_tank(self, tank, flash=False):
        if not tank.alive:
            return
        cx, cy = tank.pixel_center()
        T = TILE
        hs = T // 2

        col  = tank.color
        bcol = tank.body_color
        if flash and (self._anim_tick % 4 < 2):
            col  = C["white"]
            bcol = C["white"]

        surf = pygame.Surface((T, T), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Draw based on direction
        d = tank.dir
        # Tread positions
        if d in (UP, DOWN):
            # Treads left/right
            pygame.draw.rect(surf, bcol, (0,      2, 4, T - 4))
            pygame.draw.rect(surf, bcol, (T - 4,  2, 4, T - 4))
            # Tread details
            for i in range(3):
                yy = 4 + i * (T - 10) // 3
                pygame.draw.rect(surf, _lighten(bcol, 40), (1, yy, 2, 4))
                pygame.draw.rect(surf, _lighten(bcol, 40), (T-3, yy, 2, 4))
        else:
            # Treads top/bottom
            pygame.draw.rect(surf, bcol, (2, 0,     T - 4, 4))
            pygame.draw.rect(surf, bcol, (2, T - 4, T - 4, 4))
            for i in range(3):
                xx = 4 + i * (T - 10) // 3
                pygame.draw.rect(surf, _lighten(bcol, 40), (xx, 1, 4, 2))
                pygame.draw.rect(surf, _lighten(bcol, 40), (xx, T-3, 4, 2))

        # Body
        pygame.draw.rect(surf, col,  (4, 4, T - 8, T - 8))
        pygame.draw.rect(surf, _lighten(col, 30), (5, 5, T-10, 4))  # highlight

        # Turret (circle)
        pygame.draw.circle(surf, _darken(col, 30), (hs, hs), 6)
        pygame.draw.circle(surf, col, (hs, hs), 5)

        # Barrel
        barrel_w, barrel_h = 3, hs - 2
        if d == UP:
            pygame.draw.rect(surf, _darken(col, 20), (hs - 1, 2, barrel_w, hs - 2))
        elif d == DOWN:
            pygame.draw.rect(surf, _darken(col, 20), (hs - 1, hs + 2, barrel_w, hs - 2))
        elif d == LEFT:
            pygame.draw.rect(surf, _darken(col, 20), (2, hs - 1, hs - 2, barrel_w))
        elif d == RIGHT:
            pygame.draw.rect(surf, _darken(col, 20), (hs + 2, hs - 1, hs - 2, barrel_w))

        # Star / symbol for player
        if hasattr(tank, 'type') and tank.type == 'player':
            pygame.draw.polygon(surf, C["white"],
                _star_points(hs, hs, 4, 2, 5))

        self.screen.blit(surf, (cx - hs, cy - hs))

        # HP bar for multi-HP tanks
        if tank.hp > 1 and tank.max_hp > 1:
            bw = T - 4
            frac = tank.hp / tank.max_hp
            pygame.draw.rect(self.screen, (30, 30, 30), (cx - bw//2, cy + hs + 2, bw, 4))
            bar_col = C["hud_green"] if frac > 0.6 else C["hud_orange"] if frac > 0.3 else C["hud_red"]
            pygame.draw.rect(self.screen, bar_col, (cx - bw//2, cy + hs + 2, int(bw * frac), 4))

    # ── Bullet drawing ────────────────────────────────────

    def draw_bullet(self, b):
        col = b.color
        # Trail
        tx = b.x - DX[b.dir] * 6
        ty = b.y - DY[b.dir] * 6
        pygame.draw.circle(self.screen, _fade(col, 80), (int(tx), int(ty)), 2)
        pygame.draw.circle(self.screen, _fade(col, 140), (int(b.x - DX[b.dir]*3), int(b.y - DY[b.dir]*3)), 2)
        # Core
        pygame.draw.circle(self.screen, col, (int(b.x), int(b.y)), 4)
        pygame.draw.circle(self.screen, C["white"], (int(b.x), int(b.y)), 2)

    # ── Explosion ─────────────────────────────────────────

    def draw_explosion(self, ex):
        t  = ex.progress
        r  = ex.max_r * t * (1 - t * 0.3) * 2
        ri = ex.max_r * t * 0.6
        a1 = int(255 * (1 - t))
        a2 = int(200 * (1 - t))
        a3 = int(255 * (1 - t * 1.5))

        # Outer glow
        if a1 > 0:
            gs = pygame.Surface((int(r * 2 + 4), int(r * 2 + 4)), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*C["exp_outer"], a1 // 2),
                               (int(r + 2), int(r + 2)), max(1, int(r)))
            self.screen.blit(gs, (int(ex.cx - r - 2), int(ex.cy - r - 2)))

        # Middle ring
        if a2 > 0 and ri > 1:
            ms = pygame.Surface((int(ri * 2 + 4), int(ri * 2 + 4)), pygame.SRCALPHA)
            pygame.draw.circle(ms, (*C["exp_inner"], a2),
                               (int(ri + 2), int(ri + 2)), max(1, int(ri)))
            self.screen.blit(ms, (int(ex.cx - ri - 2), int(ex.cy - ri - 2)))

        # Core flash
        core_r = int(ex.max_r * 0.4 * (1 - t))
        if a3 > 0 and core_r > 0:
            pygame.draw.circle(self.screen, C["exp_core"], (int(ex.cx), int(ex.cy)), core_r)

        # Sparks
        rng = ex.frame * 47 % 360
        for i in range(6):
            ang   = math.radians(rng + i * 60)
            dist  = ex.max_r * t * 1.2
            sx    = int(ex.cx + math.cos(ang) * dist)
            sy    = int(ex.cy + math.sin(ang) * dist)
            alpha = int(255 * (1 - t))
            if alpha > 20:
                pygame.draw.circle(self.screen, C["spark"], (sx, sy), 2)

    # ── HUD ───────────────────────────────────────────────

    def draw_hud(self, state):
        x0  = GRID_W + GRID_OFFSET_X + 10
        y0  = GRID_OFFSET_Y + 10
        w   = HUD_W - 20

        # HUD background
        hud_rect = pygame.Rect(GRID_W + GRID_OFFSET_X, 0, HUD_W, WIN_H)
        pygame.draw.rect(self.screen, C["panel"], hud_rect)
        pygame.draw.line(self.screen, C["panel_border"],
                         (GRID_W + GRID_OFFSET_X, 0),
                         (GRID_W + GRID_OFFSET_X, WIN_H), 2)

        y = y0

        # Title
        self._hud_label(x0, y, "BATTLE CITY", C["hud_gold"], self.font_med)
        y += 28
        pygame.draw.line(self.screen, C["panel_border"], (x0, y), (x0 + w, y), 1)
        y += 10

        # Difficulty badge
        diff = state.get('difficulty', 'easy')
        dbg  = C[f"{diff}_bg"]
        dfg  = C[f"{diff}_fg"]
        badge_rect = pygame.Rect(x0, y, w, 24)
        pygame.draw.rect(self.screen, dbg, badge_rect, border_radius=4)
        pygame.draw.rect(self.screen, dfg, badge_rect, 1, border_radius=4)
        txt = self.font_small.render(diff.upper(), True, dfg)
        self.screen.blit(txt, txt.get_rect(center=badge_rect.center))
        y += 34

        # Level
        self._hud_kv(x0, y, w, "LEVEL",
                     "BOSS" if state['level'] == 3 else str(state['level']),
                     C["hud_gold"])
        y += 32

        # Level name
        lvl_name = {1: "Brick Maze", 2: "Steel Fortress", 3: "Boss Battle"}
        self._hud_label(x0, y, lvl_name.get(state['level'], ''), C["hud_dim"], self.font_tiny)
        y += 22
        pygame.draw.line(self.screen, C["panel_border"], (x0, y), (x0 + w, y), 1)
        y += 10

        # Score
        self._hud_kv(x0, y, w, "SCORE", str(state['score']), C["hud_green"])
        y += 32
        pygame.draw.line(self.screen, C["panel_border"], (x0, y), (x0 + w, y), 1)
        y += 10

        # Lives
        self._hud_label(x0, y, "LIVES", C["hud_dim"], self.font_tiny)
        y += 16
        lives = state.get('lives', 0)
        for i in range(min(lives, 10)):
            lx = x0 + 2 + (i % 5) * 20
            ly = y + (i // 5) * 18
            self._draw_life_icon(lx, ly)
        y += 40

        pygame.draw.line(self.screen, C["panel_border"], (x0, y), (x0 + w, y), 1)
        y += 10

        # Enemy pool
        self._hud_label(x0, y, "ENEMIES", C["hud_dim"], self.font_tiny)
        y += 16
        pool  = state.get('pool_remaining', 0)
        alive = state.get('enemies_alive', 0)
        total = state.get('pool_total', 20)
        dead  = total - pool - alive
        for i in range(total):
            ex2 = x0 + 2 + (i % 5) * 20
            ey  = y + (i // 5) * 18
            if i < dead:
                col = (40, 40, 55)
            elif i < dead + alive:
                col = C["hud_red"]
            else:
                col = (80, 80, 100)
            pygame.draw.rect(self.screen, col, (ex2, ey, 14, 12), border_radius=2)
        y += ((total - 1) // 5 + 1) * 18 + 6

        pygame.draw.line(self.screen, C["panel_border"], (x0, y), (x0 + w, y), 1)
        y += 10

        # Boss HP bar
        if state.get('boss_hp') is not None:
            boss_hp  = state['boss_hp']
            boss_max = state['boss_max_hp']
            phase    = state.get('boss_phase', 1)
            self._hud_label(x0, y, "BOSS", C["hud_purple"], self.font_tiny)
            y += 16
            self._hud_label(x0, y, f"Phase {phase}  HP {boss_hp}/{boss_max}", C["hud_red"], self.font_tiny)
            y += 14
            bw = w
            pygame.draw.rect(self.screen, (40, 10, 10), (x0, y, bw, 10), border_radius=3)
            frac = boss_hp / boss_max
            fc   = (int(255 * (1-frac)), int(40 + 200 * frac), 40)
            pygame.draw.rect(self.screen, fc, (x0, y, int(bw * frac), 10), border_radius=3)
            pygame.draw.rect(self.screen, C["hud_purple"], (x0, y, bw, 10), 1, border_radius=3)
            y += 20

        # Legend
        y = WIN_H - 130
        pygame.draw.line(self.screen, C["panel_border"], (x0, y), (x0 + w, y), 1)
        y += 8
        self._hud_label(x0, y, "LEGEND", C["hud_dim"], self.font_tiny)
        y += 14
        legend = [
            (C["player"],   "Player (You)"),
            (C["basic"],    "Basic  — BFS"),
            (C["fast"],     "Fast   — Greedy"),
            (C["armor"],    "Armor  — A*"),
            (C["boss"],     "Boss   — Minimax"),
        ]
        for col, label in legend:
            pygame.draw.rect(self.screen, col, (x0, y + 2, 10, 10), border_radius=2)
            txt = self.font_tiny.render(label, True, C["hud_dim"])
            self.screen.blit(txt, (x0 + 14, y))
            y += 16

        # Controls
        y = WIN_H - 50
        self._hud_label(x0, y, "WASD/↑↓←→ MOVE", C["hud_dim"], self.font_tiny)
        y += 14
        self._hud_label(x0, y, "SPACE SHOOT  P PAUSE", C["hud_dim"], self.font_tiny)

    def _hud_label(self, x, y, text, color, font):
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _hud_kv(self, x, y, w, key, val, val_col):
        ks = self.font_tiny.render(key, True, C["hud_dim"])
        vs = self.font_med.render(val, True, val_col)
        self.screen.blit(ks, (x, y + 4))
        self.screen.blit(vs, (x + w - vs.get_width(), y))

    def _draw_life_icon(self, x, y):
        pygame.draw.polygon(self.screen, C["player"],
                            [(x + 7, y), (x, y + 14), (x + 14, y + 14)])
        pygame.draw.polygon(self.screen, C["player_body"],
                            [(x + 7, y + 4), (x + 3, y + 12), (x + 11, y + 12)])

    # ── Top bar ───────────────────────────────────────────

    def draw_topbar(self, state):
        pygame.draw.rect(self.screen, C["topbar"], (0, 0, WIN_W, GRID_OFFSET_Y))
        pygame.draw.line(self.screen, C["topbar_line"], (0, GRID_OFFSET_Y - 1), (WIN_W, GRID_OFFSET_Y - 1), 2)

        title_surf = self.font_med.render("BATTLE CITY  |  TANK 1990", True, C["topbar_line"])
        self.screen.blit(title_surf, (12, (GRID_OFFSET_Y - title_surf.get_height()) // 2))

        info = f"AL2002 AI LAB  |  SPRING 2026"
        info_surf = self.font_tiny.render(info, True, C["hud_dim"])
        self.screen.blit(info_surf, (WIN_W - info_surf.get_width() - 12,
                                     (GRID_OFFSET_Y - info_surf.get_height()) // 2))

    # ── Grid border ───────────────────────────────────────

    def draw_grid_border(self):
        r = pygame.Rect(GRID_OFFSET_X - 2, GRID_OFFSET_Y - 2,
                        GRID_W + 4, GRID_H + 4)
        pygame.draw.rect(self.screen, C["panel_border"], r, 2)

    # ── Title Screen ──────────────────────────────────────

    def draw_title_screen(self, menu_sel, show_diff):
        self.screen.fill(C["bg"])
        self._draw_scanlines()

        # Animated background grid dots
        tick = self._anim_tick
        for i in range(0, WIN_W, 40):
            for j in range(0, WIN_H, 40):
                alpha = int(30 + 20 * math.sin((i + j + tick * 2) * 0.05))
                pygame.draw.circle(self.screen, (20, 24, alpha), (i, j), 1)

        # Large title
        title_x = WIN_W // 2
        title_y = 90

        # Shadow layers
        for off, col in [((4, 6), (80, 40, 0)), ((2, 3), (140, 80, 0))]:
            ts = self.font_title.render("BATTLE CITY", True, col)
            self.screen.blit(ts, ts.get_rect(centerx=title_x + off[0], centery=title_y + off[1]))
        # Main
        ts = self.font_title.render("BATTLE CITY", True, C["hud_gold"])
        self.screen.blit(ts, ts.get_rect(centerx=title_x, centery=title_y))

        # Sub
        sub = self.font_big.render("TANK  1990", True, C["hud_orange"])
        self.screen.blit(sub, sub.get_rect(centerx=title_x, centery=title_y + 62))

        # Divider
        dy = title_y + 95
        pygame.draw.line(self.screen, C["hud_gold"], (WIN_W//2 - 200, dy), (WIN_W//2 + 200, dy), 2)

        # Animated tank parade
        self._draw_title_tanks(tick)

        # Menu box
        mx, my = WIN_W // 2, 320
        menu_w, menu_h = 340, 54
        items = ["START GAME", "HOW TO PLAY", "QUIT"]

        for i, item in enumerate(items):
            iy = my + i * (menu_h + 8)
            rect = pygame.Rect(mx - menu_w//2, iy - menu_h//2, menu_w, menu_h)

            if i == menu_sel:
                pygame.draw.rect(self.screen, (30, 26, 8), rect, border_radius=6)
                pygame.draw.rect(self.screen, C["hud_gold"], rect, 2, border_radius=6)
                col = C["hud_gold"]
                prefix = "► "
            else:
                pygame.draw.rect(self.screen, (18, 20, 30), rect, border_radius=6)
                pygame.draw.rect(self.screen, C["panel_border"], rect, 1, border_radius=6)
                col = C["hud_text"]
                prefix = "  "

            txt = self.font_med.render(prefix + item, True, col)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

        # Difficulty panel
        if show_diff:
            self._draw_diff_panel(mx)

        # Bottom credits
        cr = self.font_tiny.render("© 2026  AL2002 ARTIFICIAL INTELLIGENCE LAB  |  SPRING 2026", True, (50, 55, 80))
        self.screen.blit(cr, cr.get_rect(centerx=WIN_W//2, y=WIN_H - 22))

    def _draw_title_tanks(self, tick):
        """Simple marching tank icons on title screen."""
        tank_data = [
            (C["player"],   C["player_body"]),
            (C["basic"],    C["basic_body"]),
            (C["fast"],     C["fast_body"]),
            (C["armor"],    C["armor_body"]),
            (C["boss"],     C["boss_body"]),
        ]
        y0 = 195
        spacing = WIN_W // (len(tank_data) + 1)
        for i, (col, bcol) in enumerate(tank_data):
            sx = (i + 1) * spacing
            bob = int(3 * math.sin(tick * 0.06 + i * 1.2))
            self._draw_mini_tank(sx, y0 + bob, col, bcol, DOWN)

    def _draw_mini_tank(self, cx, cy, col, bcol, direction):
        T = 30
        hs = T // 2
        surf = pygame.Surface((T, T), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        pygame.draw.rect(surf, bcol, (0, 3, 4, T - 6))
        pygame.draw.rect(surf, bcol, (T-4, 3, 4, T - 6))
        pygame.draw.rect(surf, col, (4, 4, T - 8, T - 8))
        pygame.draw.circle(surf, _darken(col, 30), (hs, hs), 6)
        pygame.draw.rect(surf, _darken(col, 20), (hs - 1, T - 2, 3, T//2))
        self.screen.blit(surf, (cx - hs, cy - hs))

    def _draw_diff_panel(self, cx):
        pw, ph = 360, 180
        rect = pygame.Rect(cx - pw//2, 500, pw, ph)
        pygame.draw.rect(self.screen, (10, 12, 20), rect, border_radius=8)
        pygame.draw.rect(self.screen, C["hud_orange"], rect, 2, border_radius=8)

        lbl = self.font_small.render("SELECT DIFFICULTY", True, C["hud_orange"])
        self.screen.blit(lbl, lbl.get_rect(centerx=cx, y=508))

        diffs = [
            ("E  EASY",    C["easy_bg"],   C["easy_fg"],   "Perfect for learning"),
            ("M  MEDIUM",  C["medium_bg"], C["medium_fg"], "Balanced challenge"),
            ("H  HARD",    C["hard_bg"],   C["hard_fg"],   "True AI gauntlet"),
        ]
        for i, (label, bg, fg, sub) in enumerate(diffs):
            bx = cx - pw//2 + 14 + i * (pw//3)
            by = 532
            br = pygame.Rect(bx, by, pw//3 - 10, 60)
            pygame.draw.rect(self.screen, bg, br, border_radius=5)
            tl = self.font_small.render(label, True, fg)
            ts = self.font_tiny.render(sub, True, _darken(fg, 40))
            self.screen.blit(tl, tl.get_rect(centerx=br.centerx, y=br.y + 8))
            self.screen.blit(ts, ts.get_rect(centerx=br.centerx, y=br.y + 34))

        hint = self.font_tiny.render("Press E / M / H to select", True, C["hud_dim"])
        self.screen.blit(hint, hint.get_rect(centerx=cx, y=610))

    def _draw_scanlines(self):
        """Subtle CRT scanlines."""
        sl = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        for y in range(0, WIN_H, 3):
            pygame.draw.line(sl, (0, 0, 0, 18), (0, y), (WIN_W, y))
        self.screen.blit(sl, (0, 0))

    # ── Pause / Overlay screens ────────────────────────────

    def draw_pause(self):
        self._draw_dim_overlay()
        cx, cy = WIN_W // 2, WIN_H // 2
        self._draw_centered_box(cx, cy, 320, 140, "PAUSED",
                                "Press P to resume  |  ESC for menu",
                                C["hud_gold"])

    def draw_game_over(self, score, won):
        self._draw_dim_overlay()
        cx, cy = WIN_W // 2, WIN_H // 2
        if won:
            title = "VICTORY!"
            sub   = f"Score: {score}    Well done, Commander!"
            col   = C["hud_green"]
        else:
            title = "GAME OVER"
            sub   = f"Final Score: {score}"
            col   = C["hud_red"]
        self._draw_centered_box(cx, cy, 420, 150, title, sub, col)
        hint = self.font_small.render("ENTER — Play Again    ESC — Main Menu", True, C["hud_dim"])
        self.screen.blit(hint, hint.get_rect(centerx=cx, y=cy + 90))

    def draw_level_banner(self, level, name, alpha):
        surf = pygame.Surface((400, 100), pygame.SRCALPHA)
        pygame.draw.rect(surf, (8, 8, 14, int(220 * alpha)), (0, 0, 400, 100), border_radius=8)
        pygame.draw.rect(surf, (*C["hud_gold"], int(255 * alpha)), (0, 0, 400, 100), 2, border_radius=8)
        if level == 3:
            lbl = "BOSS  LEVEL"
        else:
            lbl = f"LEVEL  {level}"
        lt = self.font_big.render(lbl, True, (*C["hud_gold"], int(255 * alpha)))
        nt = self.font_small.render(name, True, (*C["hud_text"], int(220 * alpha)))
        surf.blit(lt, lt.get_rect(centerx=200, y=18))
        surf.blit(nt, nt.get_rect(centerx=200, y=62))
        self.screen.blit(surf, surf.get_rect(center=(WIN_W // 2, WIN_H // 2)))

    def draw_how_to_play(self):
        self._draw_dim_overlay()
        cx, cy = WIN_W // 2, WIN_H // 2 - 60
        w, h = 560, 420
        rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(self.screen, C["panel"], rect, border_radius=10)
        pygame.draw.rect(self.screen, C["hud_gold"], rect, 2, border_radius=10)

        title = self.font_big.render("HOW TO PLAY", True, C["hud_gold"])
        self.screen.blit(title, title.get_rect(centerx=cx, y=rect.y + 14))

        lines = [
            ("CONTROLS", C["hud_orange"]),
            ("  WASD / Arrow Keys — Move your tank", C["hud_text"]),
            ("  SPACE — Fire bullet", C["hud_text"]),
            ("  P — Pause / Resume", C["hud_text"]),
            ("  ESC — Return to Main Menu", C["hud_text"]),
            ("", None),
            ("OBJECTIVES", C["hud_orange"]),
            ("  Destroy all enemy tanks to advance", C["hud_text"]),
            ("  Protect the Eagle (★) at all costs!", C["hud_text"]),
            ("  Enemy bullet hitting Eagle = instant loss", C["hud_text"]),
            ("", None),
            ("ENEMY AI TYPES", C["hud_orange"]),
            ("  Basic  (grey)  — BFS pathfinding", C["hud_text"]),
            ("  Fast   (blue)  — Greedy rush to base", C["hud_text"]),
            ("  Armor  (red)   — A* + retreats on 3rd hit", C["hud_text"]),
            ("  Boss   (purple)— Minimax adversarial AI", C["hud_text"]),
            ("", None),
            ("  Press ESC to go back", C["hud_dim"]),
        ]

        y = rect.y + 58
        for text, col in lines:
            if col is None:
                y += 8
                continue
            if text == lines[0][0] or text in ("OBJECTIVES","ENEMY AI TYPES"):
                surf = self.font_small.render(text, True, col)
            else:
                surf = self.font_tiny.render(text, True, col)
            self.screen.blit(surf, (rect.x + 20, y))
            y += surf.get_height() + 3

    def _draw_dim_overlay(self):
        dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.screen.blit(dim, (0, 0))

    def _draw_centered_box(self, cx, cy, w, h, title, sub, col):
        rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(self.screen, C["panel"], rect, border_radius=8)
        pygame.draw.rect(self.screen, col, rect, 2, border_radius=8)
        tt = self.font_big.render(title, True, col)
        st = self.font_small.render(sub, True, C["hud_text"])
        self.screen.blit(tt, tt.get_rect(centerx=cx, y=rect.y + 20))
        self.screen.blit(st, st.get_rect(centerx=cx, y=rect.y + 68))


# ── Colour helpers ─────────────────────────────────────────

def _lighten(col, amt):
    return tuple(min(255, c + amt) for c in col)

def _darken(col, amt):
    return tuple(max(0, c - amt) for c in col)

def _fade(col, alpha):
    return (*col[:3], alpha)

def _star_points(cx, cy, outer, inner, points):
    pts = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = math.pi / points * i - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts