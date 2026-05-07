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
        self._build_tank_surfaces()
        self._build_scanlines()
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
        s = pygame.Surface((T, T)).convert()
        s.fill(C["empty"])
        pygame.draw.circle(s, (22, 22, 32), (T // 2, T // 2), 1)
        self._tiles[EMPTY] = s

        # BRICK
        s = pygame.Surface((T, T)).convert()
        s.fill(C["brick_dark"])
        hw = T // 2 - 1
        rects = [(1, 1, hw, hw), (hw + 2, hw + 2, hw, hw),
                 (hw + 2, 1, hw, hw), (1, hw + 2, hw, hw)]
        cols  = [C["brick_light"], C["brick_light"],
                 (200, 70, 50), (200, 70, 50)]
        for r, col in zip(rects, cols):
            pygame.draw.rect(s, col, r)
        pygame.draw.line(s, C["brick_dark"], (0, T//2), (T, T//2), 1)
        pygame.draw.line(s, C["brick_dark"], (T//2, 0), (T//2, T), 1)
        self._tiles[BRICK] = s

        # STEEL
        s = pygame.Surface((T, T)).convert()
        s.fill(C["steel_dark"])
        pygame.draw.rect(s, C["steel_light"], (2, 2, T - 4, T - 4))
        pygame.draw.line(s, (180, 200, 220), (2, 2), (T - 2, 2), 2)
        pygame.draw.line(s, (180, 200, 220), (2, 2), (2, T - 2), 2)
        pygame.draw.line(s, (30, 40, 55), (T - 3, 2), (T - 3, T - 3), 1)
        pygame.draw.line(s, (30, 40, 55), (2, T - 3), (T - 3, T - 3), 1)
        pygame.draw.circle(s, (200, 220, 240), (T // 2, T // 2), 3)
        self._tiles[STEEL] = s

        # WATER
        for variant in (0, 1):
            s = pygame.Surface((T, T)).convert()
            s.fill(C["water_b"])
            offset = 4 if variant == 0 else 0
            for row in range(3):
                y = 4 + row * 8 + offset // 2
                pygame.draw.line(s, C["water_a"], (2, y), (T - 2, y), 2)
            self._tiles[(WATER, variant)] = s

        # FOREST
        s = pygame.Surface((T, T), pygame.SRCALPHA).convert_alpha()
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, C["forest_b"], (0, 0, T, T))
        for cx, cy, r in [(6, 6, 5), (T-6, 6, 5), (T//2, T//2-3, 6),
                           (4, T-6, 4), (T-4, T-6, 4)]:
            pygame.draw.circle(s, C["forest_a"], (cx, cy), r)
        for cx, cy, r in [(7, 7, 3), (T-7, 7, 3), (T//2, T//2-3, 4)]:
            pygame.draw.circle(s, C["forest_c"], (cx, cy), r)
        self._tiles[FOREST] = s

        # FOREST overlay
        so = pygame.Surface((T, T), pygame.SRCALPHA).convert_alpha()
        so.fill((0, 0, 0, 0))
        pygame.draw.rect(so, (*C["forest_b"], 200), (0, 0, T, T))
        for cx, cy, r in [(6, 6, 5), (T-6, 6, 5), (T//2, T//2-3, 6),
                           (4, T-6, 4), (T-4, T-6, 4)]:
            pygame.draw.circle(so, (*C["forest_a"], 220), (cx, cy), r)
        self._tiles['forest_overlay'] = so

        # EAGLE
        s = pygame.Surface((T, T)).convert()
        s.fill(C["empty"])
        self._draw_eagle_on(s, alive=True)
        self._tiles[EAGLE] = s

        # EAGLE dead
        sd = pygame.Surface((T, T)).convert()
        sd.fill(C["empty"])
        self._draw_eagle_on(sd, alive=False)
        self._tiles['eagle_dead'] = sd

    def _build_tank_surfaces(self):
        """Pre-render all tank variants (color x dir x flash)."""
        self._tank_cache = {}
        subtypes = ['player', 'basic', 'fast', 'armor', 'power', 'boss']
        directions = [UP, DOWN, LEFT, RIGHT]
        for sub in subtypes:
            col  = C[sub]
            bcol = C[sub + "_body"]
            for d in directions:
                for flash in (False, True):
                    s = self._render_tank_to_surface(col, bcol, d, flash, is_player=(sub=='player'))
                    self._tank_cache[(sub, d, flash)] = s

    def _render_tank_to_surface(self, col, bcol, d, flash, is_player=False):
        T = TILE
        hs = T // 2
        if flash:
            col, bcol = C["white"], C["white"]
        
        surf = pygame.Surface((T, T), pygame.SRCALPHA).convert_alpha()
        surf.fill((0, 0, 0, 0))

        if d in (UP, DOWN):
            pygame.draw.rect(surf, bcol, (0, 2, 4, T - 4))
            pygame.draw.rect(surf, bcol, (T - 4, 2, 4, T - 4))
            for i in range(3):
                yy = 4 + i * (T - 10) // 3
                pygame.draw.rect(surf, _lighten(bcol, 40), (1, yy, 2, 4))
                pygame.draw.rect(surf, _lighten(bcol, 40), (T-3, yy, 2, 4))
        else:
            pygame.draw.rect(surf, bcol, (2, 0, T - 4, 4))
            pygame.draw.rect(surf, bcol, (2, T - 4, T - 4, 4))
            for i in range(3):
                xx = 4 + i * (T - 10) // 3
                pygame.draw.rect(surf, _lighten(bcol, 40), (xx, 1, 4, 2))
                pygame.draw.rect(surf, _lighten(bcol, 40), (xx, T-3, 4, 2))

        pygame.draw.rect(surf, col, (4, 4, T - 8, T - 8))
        pygame.draw.rect(surf, _lighten(col, 30), (5, 5, T-10, 4))
        pygame.draw.circle(surf, _darken(col, 30), (hs, hs), 6)
        pygame.draw.circle(surf, col, (hs, hs), 5)

        barrel_w = 3
        if d == UP:    pygame.draw.rect(surf, _darken(col, 20), (hs - 1, 2, barrel_w, hs - 2))
        elif d == DOWN:  pygame.draw.rect(surf, _darken(col, 20), (hs - 1, hs + 2, barrel_w, hs - 2))
        elif d == LEFT:  pygame.draw.rect(surf, _darken(col, 20), (2, hs - 1, hs - 2, barrel_w))
        elif d == RIGHT: pygame.draw.rect(surf, _darken(col, 20), (hs + 2, hs - 1, hs - 2, barrel_w))

        if is_player:
            pygame.draw.polygon(surf, C["white"], _star_points(hs, hs, 4, 2, 5))
        return surf

    def _build_scanlines(self):
        self._scanline_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA).convert_alpha()
        for y in range(0, WIN_H, 3):
            pygame.draw.line(self._scanline_surf, (0, 0, 0, 18), (0, y), (WIN_W, y))

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
        hs = TILE // 2
        
        # Use cached surface
        sub = getattr(tank, 'subtype', 'player') if tank.type == 'enemy' else 'player'
        flash_state = flash and (self._anim_tick % 4 < 2)
        key = (sub, tank.dir, flash_state)
        
        surf = self._tank_cache.get(key)
        if surf:
            self.screen.blit(surf, (cx - hs, cy - hs))

        # HP bar
        if tank.hp > 1 and tank.max_hp > 1:
            bw = TILE - 4
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
            ms = pygame.Surface((int(ri * 2 + 4), int(ri * 2 + 4)), pygame.SRCALPHA).convert_alpha()
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
        tick = self._anim_tick

        # ── Dynamic animated background ────────────────────────
        # Draw a scrolling grid of lines that shift hue over time
        grid_spacing = 48
        scroll_x = (tick * 0.4) % grid_spacing
        scroll_y = (tick * 0.25) % grid_spacing
        hue_phase = tick * 0.008
        line_r = int(18 + 14 * math.sin(hue_phase))
        line_g = int(22 + 10 * math.sin(hue_phase + 2.1))
        line_b = int(48 + 24 * math.sin(hue_phase + 4.2))
        line_col = (line_r, line_g, line_b)

        x = -grid_spacing + scroll_x
        while x < WIN_W + grid_spacing:
            pygame.draw.line(self.screen, line_col, (int(x), 0), (int(x), WIN_H))
            x += grid_spacing
        y = -grid_spacing + scroll_y
        while y < WIN_H + grid_spacing:
            pygame.draw.line(self.screen, line_col, (0, int(y)), (WIN_W, int(y)))
            y += grid_spacing

        # Glowing intersection dots that pulse with colour
        ix = -grid_spacing + scroll_x
        while ix < WIN_W + grid_spacing:
            iy = -grid_spacing + scroll_y
            while iy < WIN_H + grid_spacing:
                wave = math.sin((ix + iy) * 0.018 + tick * 0.05)
                dot_r = int(40 + 60 * ((wave + 1) / 2))
                dot_g = int(50 + 40 * math.sin((ix - iy) * 0.02 + tick * 0.03))
                dot_b = int(90 + 80 * ((math.sin(tick * 0.04 + ix * 0.01) + 1) / 2))
                dot_a = int(60 + 80 * ((wave + 1) / 2))
                dot_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(dot_surf, (dot_r, dot_g, dot_b, dot_a), (3, 3), 3)
                self.screen.blit(dot_surf, (int(ix) - 3, int(iy) - 3))
                iy += grid_spacing
            ix += grid_spacing

        self._draw_scanlines()

        # ── Title with multi-layer glow bloom ──────────────────
        title_x = WIN_W // 2
        title_y = 90
        pulse = 0.5 + 0.5 * math.sin(tick * 0.08)          # 0..1 smooth
        pulse_fast = 0.5 + 0.5 * math.sin(tick * 0.18)

        # Radial bloom layers (large → small, decreasing alpha)
        bloom_data = [
            (18, int(30 + 40 * pulse)),
            (10, int(60 + 60 * pulse)),
            ( 5, int(100 + 80 * pulse_fast)),
        ]
        ts_ref = self.font_title.render("BATTLE CITY", True, C["hud_gold"])
        bx0 = ts_ref.get_rect(centerx=title_x, centery=title_y).x
        by0 = ts_ref.get_rect(centerx=title_x, centery=title_y).y
        tw, th = ts_ref.get_size()
        for spread, alpha in bloom_data:
            bloom = pygame.Surface((tw + spread * 2, th + spread * 2), pygame.SRCALPHA)
            # Render text into a temp surface, tint to orange, then set alpha
            tmp = self.font_title.render("BATTLE CITY", True,
                                         (255, int(160 + 60 * pulse), 20))
            tmp.set_alpha(alpha)
            bloom.blit(tmp, (spread, spread))
            self.screen.blit(bloom, (bx0 - spread, by0 - spread))

        # Hard shadow
        for off, col in [((5, 7), (60, 28, 0)), ((2, 3), (130, 70, 0))]:
            ts = self.font_title.render("BATTLE CITY", True, col)
            self.screen.blit(ts, ts.get_rect(centerx=title_x + off[0],
                                              centery=title_y + off[1]))
        # Crisp main title
        ts = self.font_title.render("BATTLE CITY", True, C["hud_gold"])
        self.screen.blit(ts, ts.get_rect(centerx=title_x, centery=title_y))

        # Sub-title — also pulses gently
        sub_col = (
            255,
            int(120 + 80 * pulse_fast),
            int(20 + 30 * pulse_fast),
        )
        sub = self.font_big.render("TANK  1990", True, sub_col)
        self.screen.blit(sub, sub.get_rect(centerx=title_x, centery=title_y + 62))

        # Divider with animated glow segment
        dy = title_y + 95
        pygame.draw.line(self.screen, C["hud_gold"],
                         (WIN_W//2 - 200, dy), (WIN_W//2 + 200, dy), 1)
        seg_hw = int(60 + 40 * pulse)
        pygame.draw.line(self.screen,
                         (255, int(180 + 60 * pulse), 0),
                         (WIN_W//2 - seg_hw, dy),
                         (WIN_W//2 + seg_hw, dy), 3)

        # Animated tank parade
        self._draw_title_tanks(tick)

        # ── Menu items ─────────────────────────────────────────
        mx, my = WIN_W // 2, 310
        menu_w, menu_h = 340, 50
        items = ["START GAME", "HIGH SCORES", "HOW TO PLAY", "QUIT"]

        for i, item in enumerate(items):
            iy = my + i * (menu_h + 8)
            rect = pygame.Rect(mx - menu_w//2, iy - menu_h//2, menu_w, menu_h)

            if i == menu_sel:
                # ── Pulsing selected item ──────────────────────
                glow_val = int(200 + 55 * math.sin(tick * 0.14))
                glow_val2 = int(glow_val * 0.75)

                # Layer 1: diffuse outer halo
                halo = pygame.Surface((menu_w + 24, menu_h + 24), pygame.SRCALPHA)
                halo_alpha = int(40 + 50 * pulse)
                pygame.draw.rect(halo,
                                 (glow_val, glow_val2, 0, halo_alpha),
                                 (0, 0, menu_w + 24, menu_h + 24),
                                 border_radius=12)
                self.screen.blit(halo, (rect.x - 12, rect.y - 12))

                # Layer 2: tight outer ring
                glow_rect = rect.inflate(6, 6)
                pygame.draw.rect(self.screen,
                                 (glow_val // 3, glow_val2 // 4, 0),
                                 glow_rect, border_radius=10)

                # Item background
                pygame.draw.rect(self.screen, (50, 40, 10), rect, border_radius=6)

                # Animated border (two-tone alternating)
                border_col = (glow_val, int(glow_val // 1.3), 0)
                pygame.draw.rect(self.screen, border_col, rect, 3, border_radius=6)

                # Inner highlight line
                pygame.draw.line(self.screen,
                                 (255, 220, 80, 60),
                                 (rect.x + 8, rect.y + 2),
                                 (rect.right - 8, rect.y + 2), 1)

                col    = C["hud_gold"]
                prefix = "► "
                # Shadow behind text
                stxt = self.font_med.render(prefix + item, True, (0, 0, 0))
                self.screen.blit(stxt,
                    stxt.get_rect(center=(rect.centerx + 2, rect.centery + 2)))
            else:
                pygame.draw.rect(self.screen, (18, 20, 30), rect, border_radius=6)
                pygame.draw.rect(self.screen, C["panel_border"], rect, 1, border_radius=6)
                col    = C["hud_text"]
                prefix = "  "

            txt = self.font_med.render(prefix + item, True, col)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

        # Difficulty panel
        if show_diff:
            self._draw_diff_panel(mx)

        # Bottom credits
        cr = self.font_tiny.render(
            "© 2026  AL2002 ARTIFICIAL INTELLIGENCE LAB  |  SPRING 2026",
            True, (50, 55, 80))
        self.screen.blit(cr, cr.get_rect(centerx=WIN_W//2, y=WIN_H - 22))

    def _draw_title_tanks(self, tick):
        """Marching tank icons on title screen — now with a subtle glow halo."""
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
            bob = int(4 * math.sin(tick * 0.07 + i * 1.2))
            # Subtle halo under each mini tank
            halo_r = int(16 + 6 * math.sin(tick * 0.1 + i * 0.8))
            halo_a = int(50 + 40 * math.sin(tick * 0.08 + i))
            hs_surf = pygame.Surface((halo_r * 2, halo_r * 2), pygame.SRCALPHA)
            halo_col = (*col[:3], halo_a)
            pygame.draw.circle(hs_surf, halo_col, (halo_r, halo_r), halo_r)
            self.screen.blit(hs_surf, (sx - halo_r, y0 + bob - halo_r))
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
        tick = self._anim_tick
        pulse = 0.5 + 0.5 * math.sin(tick * 0.12)

        pw, ph = 420, 210
        rect = pygame.Rect(cx - pw//2, 488, pw, ph)

        # Panel background with inner gradient feel
        bg_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (8, 10, 22, 245), (0, 0, pw, ph), border_radius=10)
        self.screen.blit(bg_surf, rect.topleft)

        # Animated outer border
        border_glow = int(180 + 75 * pulse)
        pygame.draw.rect(self.screen,
                         (border_glow, int(border_glow * 0.55), 0),
                         rect, 2, border_radius=10)

        lbl = self.font_small.render("— SELECT DIFFICULTY —", True, C["hud_orange"])
        self.screen.blit(lbl, lbl.get_rect(centerx=cx, y=rect.y + 10))

        diffs = [
            ("E  EASY",   C["easy_bg"],   C["easy_fg"],   "Perfect for learning"),
            ("M  MEDIUM", C["medium_bg"], C["medium_fg"], "Balanced challenge"),
            ("H  HARD",   C["hard_bg"],   C["hard_fg"],   "True AI gauntlet"),
        ]
        card_w = pw // 3 - 14
        card_h = 80
        for i, (label, bg, fg, sub) in enumerate(diffs):
            bx = rect.x + 10 + i * (pw // 3)
            by = rect.y + 44
            br = pygame.Rect(bx, by, card_w, card_h)

            # Draw card background
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(card_surf, (*bg[:3], 220), (0, 0, card_w, card_h), border_radius=7)
            self.screen.blit(card_surf, br.topleft)

            # Animated highlight border on each card
            phase_off = i * 2.1
            card_glow = int(140 + 80 * math.sin(tick * 0.10 + phase_off))
            border_thickness = 2
            pygame.draw.rect(self.screen,
                             (min(255, fg[0] + 40),
                              min(255, fg[1] + 40),
                              min(255, fg[2] + 40)),
                             br, border_thickness, border_radius=7)

            # Inner top highlight
            pygame.draw.line(self.screen,
                             (min(255, fg[0] + 80), min(255, fg[1] + 80), min(255, fg[2] + 80)),
                             (br.x + 6, br.y + 2), (br.right - 6, br.y + 2), 1)

            # Key letter badge
            key_letter = label[0]   # 'E', 'M', or 'H'
            badge_r = pygame.Rect(br.x + 6, br.y + 6, 20, 20)
            pygame.draw.rect(self.screen, fg, badge_r, border_radius=4)
            kl = self.font_tiny.render(key_letter, True, bg)
            self.screen.blit(kl, kl.get_rect(center=badge_r.center))

            # Label & sub-text
            tl = self.font_small.render(label[3:], True, fg)   # skip "E  "
            ts = self.font_tiny.render(sub, True, _darken(fg, 30))
            self.screen.blit(tl, tl.get_rect(centerx=br.centerx, y=br.y + 10))
            self.screen.blit(ts, ts.get_rect(centerx=br.centerx, y=br.y + 48))

            # Pulsing underline for each card
            ul_alpha = int(120 + 100 * math.sin(tick * 0.12 + phase_off))
            ul_surf = pygame.Surface((card_w - 16, 3), pygame.SRCALPHA)
            pygame.draw.rect(ul_surf, (*fg[:3], ul_alpha), (0, 0, card_w - 16, 3), border_radius=1)
            self.screen.blit(ul_surf, (br.x + 8, br.bottom - 8))

        hint = self.font_tiny.render("Press  E / M / H  to select", True, C["hud_dim"])
        self.screen.blit(hint, hint.get_rect(centerx=cx, y=rect.bottom - 22))

    # ── Loading Screen ────────────────────────────────────────

    def draw_loading_screen(self, progress: float):
        """Draw the boot/loading screen.

        Args:
            progress: 0.0 → 1.0  completion fraction
        """
        tick  = self._anim_tick
        cx    = WIN_W // 2
        pulse = 0.5 + 0.5 * math.sin(tick * 0.08)
        pulse2= 0.5 + 0.5 * math.sin(tick * 0.18)

        # ── Background ──────────────────────────────────────────
        self.screen.fill(C["bg"])

        # Scrolling grid (same as title screen, slightly slower)
        grid_spacing = 52
        scroll_x = (tick * 0.3) % grid_spacing
        scroll_y = (tick * 0.18) % grid_spacing
        hue_phase = tick * 0.007
        lr = int(14 + 12 * math.sin(hue_phase))
        lg = int(18 + 8  * math.sin(hue_phase + 2.1))
        lb = int(44 + 22 * math.sin(hue_phase + 4.2))
        line_col = (lr, lg, lb)
        x = -grid_spacing + scroll_x
        while x < WIN_W + grid_spacing:
            pygame.draw.line(self.screen, line_col, (int(x), 0), (int(x), WIN_H))
            x += grid_spacing
        y = -grid_spacing + scroll_y
        while y < WIN_H + grid_spacing:
            pygame.draw.line(self.screen, line_col, (0, int(y)), (WIN_W, int(y)))
            y += grid_spacing

        # Pulsing radial vignette – soft centre glow
        vrad = int(WIN_H * 0.55 + WIN_H * 0.05 * pulse)
        vsurf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        for ri in range(vrad, 0, -max(1, vrad // 12)):
            a = int(4 + 8 * (1 - ri / vrad))
            pygame.draw.circle(vsurf,
                               (int(30 * pulse), int(18 * pulse2), int(60 * pulse), a),
                               (cx, WIN_H // 2), ri)
        self.screen.blit(vsurf, (0, 0))

        # ── Title block ──────────────────────────────────────────
        title_y = WIN_H // 2 - 180

        # Multi-layer bloom behind title text
        ts_ref = self.font_title.render("BATTLE CITY", True, C["hud_gold"])
        bx0 = ts_ref.get_rect(centerx=cx, centery=title_y).x
        by0 = ts_ref.get_rect(centerx=cx, centery=title_y).y
        tw, th = ts_ref.get_size()
        for spread, alpha in [
            (20, int(25 + 35 * pulse)),
            (10, int(55 + 55 * pulse)),
            ( 4, int(90 + 80 * pulse2)),
        ]:
            bloom = pygame.Surface((tw + spread * 2, th + spread * 2), pygame.SRCALPHA)
            tmp = self.font_title.render("BATTLE CITY", True,
                                         (255, int(155 + 65 * pulse), 10))
            tmp.set_alpha(alpha)
            bloom.blit(tmp, (spread, spread))
            self.screen.blit(bloom, (bx0 - spread, by0 - spread))

        # Shadows
        for off, col in [((5, 7), (55, 24, 0)), ((2, 3), (120, 60, 0))]:
            ts = self.font_title.render("BATTLE CITY", True, col)
            self.screen.blit(ts, ts.get_rect(centerx=cx + off[0],
                                              centery=title_y + off[1]))
        # Crisp title
        self.screen.blit(ts_ref, ts_ref.get_rect(centerx=cx, centery=title_y))

        # Sub-line
        sub_col = (255, int(118 + 78 * pulse2), int(18 + 28 * pulse2))
        sub = self.font_big.render("Welcome to Battle City!",
                                   True, sub_col)
        self.screen.blit(sub, sub.get_rect(centerx=cx, centery=title_y + 58))

        # Divider
        dy = title_y + 84
        pygame.draw.line(self.screen, C["hud_gold"],
                         (cx - 220, dy), (cx + 220, dy), 1)
        seg = int(70 + 50 * pulse)
        pygame.draw.line(self.screen, (255, int(180 + 60 * pulse), 0),
                         (cx - seg, dy), (cx + seg, dy), 3)

        # ── Progress bar ─────────────────────────────────────────
        bar_w   = int(WIN_W * 0.62)
        bar_h   = 22
        bar_x   = cx - bar_w // 2
        bar_y   = WIN_H // 2 + 60

        # Track
        pygame.draw.rect(self.screen, (18, 18, 28),
                         (bar_x, bar_y, bar_w, bar_h), border_radius=11)
        pygame.draw.rect(self.screen, (40, 45, 70),
                         (bar_x, bar_y, bar_w, bar_h), 1, border_radius=11)

        # Filled portion with animated shimmer
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            # Base fill gradient (left=orange, right=gold)
            fill_surf = pygame.Surface((fill_w, bar_h))
            for px in range(fill_w):
                t_col = px / max(1, fill_w)
                r = int(220 + 35 * t_col)
                g = int(130 + 70 * t_col)
                b = 0
                pygame.draw.line(fill_surf, (r, g, b), (px, 0), (px, bar_h))
            # Clip to rounded left half
            fill_rect = pygame.Rect(bar_x, bar_y, fill_w, bar_h)
            fill_surf_clip = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            fill_surf_clip.blit(fill_surf, (0, 0))
            self.screen.blit(fill_surf_clip, (bar_x, bar_y))

            # Shimmer sweep
            shimmer_x = bar_x + int((fill_w + 40) * ((tick * 2) % (bar_w + 40)) / (bar_w + 40))
            shimmer_surf = pygame.Surface((32, bar_h), pygame.SRCALPHA)
            for px in range(32):
                a = int(100 * math.sin(math.pi * px / 31))
                pygame.draw.line(shimmer_surf, (255, 255, 200, a),
                                 (px, 0), (px, bar_h))
            self.screen.blit(shimmer_surf,
                             (min(shimmer_x, bar_x + fill_w - 16), bar_y))

            # Top gloss
            gloss = pygame.Surface((fill_w, bar_h // 2), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 28))
            self.screen.blit(gloss, (bar_x, bar_y))

        # Progress bar border (always on top)
        pygame.draw.rect(self.screen,
                         (int(180 + 75 * pulse), int(100 + 40 * pulse), 0),
                         (bar_x, bar_y, bar_w, bar_h), 2, border_radius=11)

        # ── Mini tank driving along bar ───────────────────────────
        tank_x = bar_x + max(20, fill_w) + 2
        tank_y = bar_y + bar_h // 2
        if fill_w < bar_w - 24:
            bob = int(2 * math.sin(tick * 0.4))
            self._draw_mini_tank(int(tank_x), tank_y + bob,
                                 C["player"], C["player_body"], RIGHT)
            # Exhaust particles
            for pf in range(3):
                px_off = tank_x - 8 - pf * 5
                py_off = tank_y + bob + int(3 * math.sin(tick * 0.5 + pf))
                pa = max(0, int(180 - pf * 60))
                ps = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(ps,
                                   (255, int(160 + 60 * pulse), 0, pa),
                                   (3, 3), 3 - pf)
                self.screen.blit(ps, (int(px_off) - 3, int(py_off) - 3))

        # ── Percentage text ───────────────────────────────────────
        pct  = int(progress * 100)
        pct_surf = self.font_big.render(f"{pct}%", True, C["hud_gold"])
        self.screen.blit(pct_surf,
                         pct_surf.get_rect(centerx=cx, y=bar_y + bar_h + 10))

        # ── Cycling status messages ───────────────────────────────
        messages = [
            "Initialising AI modules...",
            "Loading BFS pathfinder...",
            "Calibrating A* heuristics...",
            "Deploying Minimax engine...",
            "Generating terrain maps...",
            "Arming enemy battalions...",
            "Charging player cannon...",
            "Battle systems online...",
            "All units ready. Good luck, Commander!",
        ]
        # Pick message based on progress bucket
        idx = min(int(progress * len(messages)), len(messages) - 1)
        msg_surf = self.font_small.render(messages[idx], True, C["hud_dim"])
        # Blink on final message
        if idx == len(messages) - 1:
            blink_a = int(200 + 55 * math.sin(tick * 0.25))
            msg_surf.set_alpha(blink_a)
        self.screen.blit(msg_surf,
                         msg_surf.get_rect(centerx=cx, y=bar_y + bar_h + 46))

        # ── Small tips strip ─────────────────────────────────────
        tips = [
            "TIP  Protect the Eagle at all costs!",
            "TIP  WASD or Arrow Keys to move your tank",
            "TIP  Press P to pause anytime",
            "TIP  Armor tanks require multiple hits",
            "TIP  Boss uses Minimax AI — stay unpredictable!",
        ]
        tip_idx = (tick // 140) % len(tips)
        tip_alpha = int(255 * min(1.0, (tick % 140) / 20.0))   # fade in
        tip_surf = self.font_tiny.render(tips[tip_idx], True, C["hud_dim"])
        tip_surf.set_alpha(tip_alpha)
        self.screen.blit(tip_surf,
                         tip_surf.get_rect(centerx=cx, y=WIN_H - 44))

        # ── Corner badge ─────────────────────────────────────────
        badge = self.font_tiny.render("© 2026  AL2002 AI LAB", True, (40, 44, 65))
        self.screen.blit(badge, (10, WIN_H - 18))

        # CRT scanlines on top
        self._draw_scanlines()

    def _draw_scanlines(self):
        """Subtle CRT scanlines (pre-rendered)."""
        self.screen.blit(self._scanline_surf, (0, 0))

    # ── Pause / Overlay screens ────────────────────────────

    def draw_pause(self):
        self._draw_dim_overlay()
        cx, cy = WIN_W // 2, WIN_H // 2
        self._draw_centered_box(cx, cy, 320, 140, "PAUSED",
                                "Press P to resume  |  ESC for menu",
                                C["hud_gold"])

    def draw_game_over(self, score, won, is_highscore=False):
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

        # High-score banner
        if is_highscore:
            tick  = self._anim_tick
            pulse = 0.5 + 0.5 * math.sin(tick * 0.14)
            hs_col  = (255, int(200 + 55*pulse), 0)
            hs_surf = self.font_small.render(
                "★  NEW HIGH SCORE!  ★", True, hs_col)
            hs_surf.set_alpha(int(200 + 55*pulse))
            self.screen.blit(hs_surf,
                             hs_surf.get_rect(centerx=cx, y=cy - 75))
            hint2 = self.font_tiny.render(
                "View it on the leaderboard from the main menu",
                True, C["hud_dim"])
            self.screen.blit(hint2, hint2.get_rect(centerx=cx, y=cy + 100))

        hint = self.font_small.render(
            "ENTER — Play Again    ESC — Main Menu", True, C["hud_dim"])
        self.screen.blit(hint, hint.get_rect(
            centerx=cx, y=cy + (116 if is_highscore else 90)))

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

    # ── High Scores Screen ─────────────────────────────────────

    def draw_highscores(self, scores: list, new_rank: int = -1):
        """Full-screen leaderboard.

        Args:
            scores:   list of score dicts from highscore.load_scores()
            new_rank: 0-based index of the just-saved entry (-1 = none)
        """
        tick  = self._anim_tick
        cx    = WIN_W // 2
        pulse = 0.5 + 0.5 * math.sin(tick * 0.08)
        pulse2= 0.5 + 0.5 * math.sin(tick * 0.18)

        # ── Background (same scrolling grid as title) ────────────
        self.screen.fill(C["bg"])
        grid_spacing = 48
        scroll_x = (tick * 0.35) % grid_spacing
        scroll_y = (tick * 0.22) % grid_spacing
        hp = tick * 0.007
        lc = (int(16 + 12*math.sin(hp)),
              int(20 + 8 *math.sin(hp+2.1)),
              int(45 + 22*math.sin(hp+4.2)))
        x = -grid_spacing + scroll_x
        while x < WIN_W + grid_spacing:
            pygame.draw.line(self.screen, lc, (int(x), 0), (int(x), WIN_H))
            x += grid_spacing
        y = -grid_spacing + scroll_y
        while y < WIN_H + grid_spacing:
            pygame.draw.line(self.screen, lc, (0, int(y)), (WIN_W, int(y)))
            y += grid_spacing
        self._draw_scanlines()

        # ── Title ────────────────────────────────────────────────
        ty = 54
        # Bloom glow behind title
        ts_ref = self.font_big.render("★  HIGH SCORES  ★", True, C["hud_gold"])
        bx0 = ts_ref.get_rect(centerx=cx, centery=ty).x
        by0 = ts_ref.get_rect(centerx=cx, centery=ty).y
        tw, th = ts_ref.get_size()
        for spread, alpha in [(12, int(30+40*pulse)), (5, int(70+70*pulse2))]:
            bloom = pygame.Surface((tw+spread*2, th+spread*2), pygame.SRCALPHA)
            tmp = self.font_big.render("★  HIGH SCORES  ★", True,
                                       (255, int(150+80*pulse), 0))
            tmp.set_alpha(alpha)
            bloom.blit(tmp, (spread, spread))
            self.screen.blit(bloom, (bx0-spread, by0-spread))
        self.screen.blit(ts_ref, ts_ref.get_rect(centerx=cx, centery=ty))

        # Animated divider
        seg = int(80 + 50*pulse)
        pygame.draw.line(self.screen, C["hud_gold"],
                         (cx-240, ty+22), (cx+240, ty+22), 1)
        pygame.draw.line(self.screen, (255, int(180+60*pulse), 0),
                         (cx-seg, ty+22), (cx+seg, ty+22), 3)

        # ── Column headers ───────────────────────────────────────
        header_y = ty + 36
        cols_x = [60, 160, 360, 520, 620, 740, 860]
        headers = ["#", "SCORE", "DIFFICULTY", "LEVEL", "RESULT", "DATE"]
        for i, h in enumerate(headers):
            hs = self.font_tiny.render(h, True, C["hud_dim"])
            self.screen.blit(hs, (cols_x[i], header_y))
        pygame.draw.line(self.screen, C["panel_border"],
                         (40, header_y+16), (WIN_W-40, header_y+16), 1)

        # ── Rank medal colours ───────────────────────────────────
        medal = {
            0: (255, 215,   0),   # gold
            1: (192, 192, 192),   # silver
            2: (205, 127,  50),   # bronze
        }

        # ── Score rows ───────────────────────────────────────────
        row_h   = 42
        row_y0  = header_y + 24
        max_show = 10

        if not scores:
            empty = self.font_med.render(
                "No scores yet — be the first to conquer the battlefield!",
                True, C["hud_dim"])
            self.screen.blit(empty,
                             empty.get_rect(centerx=cx, y=row_y0 + 80))
        else:
            for i, entry in enumerate(scores[:max_show]):
                ry = row_y0 + i * row_h
                is_new = (i == new_rank)

                # Row background
                row_surf = pygame.Surface((WIN_W - 80, row_h - 4), pygame.SRCALPHA)
                if is_new:
                    new_a = int(50 + 40 * pulse)
                    pygame.draw.rect(row_surf, (255, 200, 0, new_a),
                                     (0, 0, WIN_W-80, row_h-4), border_radius=6)
                    # Pulsing border
                    border_col = (255, int(200+55*pulse), 0)
                    pygame.draw.rect(row_surf, (*border_col, 200),
                                     (0, 0, WIN_W-80, row_h-4), 2, border_radius=6)
                elif i % 2 == 0:
                    pygame.draw.rect(row_surf, (20, 22, 34, 180),
                                     (0, 0, WIN_W-80, row_h-4), border_radius=4)
                else:
                    pygame.draw.rect(row_surf, (14, 16, 26, 180),
                                     (0, 0, WIN_W-80, row_h-4), border_radius=4)
                self.screen.blit(row_surf, (40, ry))

                text_y = ry + (row_h - 4)//2 - 7   # vertically centred

                # ── Rank number / medal ──────────────────────────
                rank_col = medal.get(i, C["hud_dim"])
                if i < 3:
                    # Draw medal circle
                    pygame.draw.circle(self.screen, rank_col,
                                       (cols_x[0]+8, text_y+8), 11)
                    pygame.draw.circle(self.screen, _darken(rank_col, 40),
                                       (cols_x[0]+8, text_y+8), 11, 2)
                    rn = self.font_tiny.render(str(i+1), True, C["bg"])
                    self.screen.blit(rn, rn.get_rect(center=(cols_x[0]+8, text_y+8)))
                else:
                    rn = self.font_small.render(str(i+1), True, rank_col)
                    self.screen.blit(rn, (cols_x[0]+2, text_y))

                # ── Score ────────────────────────────────────────
                score_col = C["hud_gold"] if is_new else C["hud_text"]
                sc = self.font_med.render(f"{entry.get('score', 0):,}", True, score_col)
                self.screen.blit(sc, (cols_x[1], text_y - 2))

                # ── Difficulty badge ──────────────────────────────
                diff = entry.get('difficulty', 'medium')
                dbg  = C.get(f"{diff}_bg", (40, 40, 60))
                dfg  = C.get(f"{diff}_fg", C["hud_text"])
                badge_rect = pygame.Rect(cols_x[2], text_y, 80, 18)
                pygame.draw.rect(self.screen, dbg, badge_rect, border_radius=4)
                pygame.draw.rect(self.screen, dfg, badge_rect, 1, border_radius=4)
                dt = self.font_tiny.render(diff.upper(), True, dfg)
                self.screen.blit(dt, dt.get_rect(center=badge_rect.center))

                # ── Level reached ────────────────────────────────
                lv = entry.get('level', 1)
                lv_names = {1: "Brick Maze", 2: "Steel Fort", 3: "Boss Btl"}
                lv_col   = (C["hud_orange"] if lv == 3
                            else C["hud_blue"] if lv == 2
                            else C["hud_dim"])
                lvs = self.font_small.render(f"Lvl {lv}", True, lv_col)
                self.screen.blit(lvs, (cols_x[3], text_y))

                # ── Win / Loss badge ──────────────────────────────
                won = entry.get('won', False)
                if won:
                    res_col  = C["hud_green"]
                    res_icon = "✔ WON"
                else:
                    res_col  = C["hud_red"]
                    res_icon = "✘ LOST"
                rs = self.font_small.render(res_icon, True, res_col)
                self.screen.blit(rs, (cols_x[4], text_y))

                # ── Date ─────────────────────────────────────────
                ds = self.font_tiny.render(entry.get('date', ''), True, C["hud_dim"])
                self.screen.blit(ds, (cols_x[5], text_y + 2))

                # ── NEW! marker ───────────────────────────────────
                if is_new:
                    blink_a = int(220 + 35*math.sin(tick * 0.3))
                    new_lbl = self.font_tiny.render("NEW!", True, C["hud_gold"])
                    new_lbl.set_alpha(blink_a)
                    self.screen.blit(new_lbl, (WIN_W - 80, text_y + 2))

        # ── Footer ───────────────────────────────────────────────
        pygame.draw.line(self.screen, C["panel_border"],
                         (40, WIN_H - 40), (WIN_W - 40, WIN_H - 40), 1)
        hint = self.font_small.render(
            "ESC — Back to Menu    DEL — Clear Scores", True, C["hud_dim"])
        self.screen.blit(hint, hint.get_rect(centerx=cx, y=WIN_H - 30))

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