# ============================================================
#  BATTLE CITY — MAIN GAME LOOP
#  AL2002 Artificial Intelligence Lab | Spring 2026
# ============================================================

import pygame
import sys
import random
import math

from constants import *
from csp_map    import generate_map
from entities   import PlayerTank, make_enemy, Explosion
from renderer   import Renderer
import highscore


# ── Level enemy pools ─────────────────────────────────────────
LEVEL_POOLS = {
    1: ['basic'] * 8  + ['fast'] * 4,
    2: ['basic'] * 4  + ['fast'] * 4 + ['armor'] * 4 + ['power'] * 4,
    3: ['armor'] * 4  + ['power'] * 4 + ['boss'] * 1,
}

EAGLE_POS = (12, 24)   # grid tile coords of eagle


# ── Bullet collision helper ────────────────────────────────────

def _bullet_tile(bx, by):
    """Convert bullet pixel coords to grid tile coords."""
    gx = int((bx - GRID_OFFSET_X) / TILE)
    gy = int((by - GRID_OFFSET_Y) / TILE)
    return gx, gy


# ============================================================
#  Game
# ============================================================

class Game:

    # ── Init ─────────────────────────────────────────────────

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Welcome to Battle City!  |  AI Lab  |  Spring 2026")
        self.screen  = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock   = pygame.time.Clock()
        self.renderer = Renderer(self.screen)

        # Global state
        self.running    = True
        self.scene      = 'loading'  # 'loading' | 'menu' | 'how' | 'playing' | 'over'
        self.difficulty = 'medium'
        self.diff_cfg   = DIFF[self.difficulty]

        # Loading screen
        self.load_frames      = 0          # elapsed frames
        self.load_duration    = 240        # total frames (4 s at 60 fps)
        self.load_progress    = 0.0        # 0.0 → 1.0

        # Menu cursor  (0=Start, 1=High Scores, 2=How To Play, 3=Quit)
        self.menu_sel   = 0
        self.show_diff  = False

        # High score state
        self.new_score_rank = -1              # 0-based rank of last saved entry
        self.cached_scores  = highscore.load_scores()  # refreshed on each visit

        # Level / in-game
        self.level      = 1
        self.score      = 0
        self.lives      = 3

        # Per-level data
        self.map_        = None
        self.eagle_alive = True
        self.player      = None
        self.enemies     = []
        self.bullets     = []
        self.explosions  = []
        self.spawn_queue = []      # list of subtype strings waiting to spawn
        self.spawn_timer = 0
        self.pool_total  = 0

        # Banner animation
        self.banner_timer = 0      # frames to show level banner

        # Pause / over state
        self.paused      = False
        self.over_won    = False

    # ── Level setup ──────────────────────────────────────────

    def _setup_level(self):
        self.diff_cfg   = DIFF[self.difficulty]
        self.map_        = generate_map(self.level, self.difficulty)
        self.eagle_alive = True
        self.enemies     = []
        self.bullets     = []
        self.explosions  = []
        self.paused      = False

        # Player
        px, py = 4, 23
        self.player = PlayerTank(px, py,
                                 fire_cd=self.diff_cfg['player_fire_cd'],
                                 speed_tps=4.0)
        self.player.lives = self.lives
        self.player.score = self.score

        # Enemy pool
        pool = list(LEVEL_POOLS.get(self.level, LEVEL_POOLS[1]))
        random.shuffle(pool)
        self.spawn_queue  = pool
        self.pool_total   = len(pool)
        self.spawn_timer  = 0

        # Spawn first wave immediately
        for _ in range(min(3, len(self.spawn_queue))):
            self._try_spawn_enemy()

        self.banner_timer = 180   # show banner for 3 s

    def _try_spawn_enemy(self):
        if not self.spawn_queue:
            return
        pts = list(SPAWN_POINTS)
        random.shuffle(pts)
        for sx, sy in pts:
            # Make sure spawn point is clear
            occupied = any(
                e.alive and e.igx() == sx and e.igy() == sy
                for e in self.enemies
            )
            if not occupied:
                subtype = self.spawn_queue.pop(0)
                e = make_enemy(sx, sy, subtype, self.diff_cfg)
                self.enemies.append(e)
                # Spawn flash explosion
                cx = GRID_OFFSET_X + sx * TILE + TILE // 2
                cy = GRID_OFFSET_Y + sy * TILE + TILE // 2
                self.explosions.append(Explosion(cx, cy, max_r=20))
                return

    # ── Input ─────────────────────────────────────────────────

    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False

            elif ev.type == pygame.KEYDOWN:

                # ---- Loading (any key skips) ----
                if self.scene == 'loading':
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                        self._finish_loading()

                # ---- Menu ----
                elif self.scene == 'menu':
                    if ev.key in (pygame.K_UP, pygame.K_w):
                        self.menu_sel = (self.menu_sel - 1) % 4
                        self.show_diff = False
                    elif ev.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_sel = (self.menu_sel + 1) % 4
                        self.show_diff = False
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.menu_sel == 0:          # START GAME
                            self.show_diff = True
                        elif self.menu_sel == 1:        # HIGH SCORES
                            self.cached_scores  = highscore.load_scores()
                            self.new_score_rank = -1
                            self.scene = 'scores'
                        elif self.menu_sel == 2:        # HOW TO PLAY
                            self.scene = 'how'
                        elif self.menu_sel == 3:        # QUIT
                            self.running = False
                    # Difficulty hotkeys
                    elif ev.key == pygame.K_e and self.show_diff:
                        self.difficulty = 'easy'
                        self._start_game()
                    elif ev.key == pygame.K_m and self.show_diff:
                        self.difficulty = 'medium'
                        self._start_game()
                    elif ev.key == pygame.K_h and self.show_diff:
                        self.difficulty = 'hard'
                        self._start_game()
                    elif ev.key == pygame.K_ESCAPE:
                        self.show_diff = False

                # ---- High Scores ----
                elif self.scene == 'scores':
                    if ev.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        self.scene = 'menu'
                        self.new_score_rank = -1
                    elif ev.key == pygame.K_DELETE:
                        highscore.clear_scores()
                        self.cached_scores  = []
                        self.new_score_rank = -1

                # ---- How to play ----
                elif self.scene == 'how':
                    if ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                        self.scene = 'menu'

                # ---- Playing ----
                elif self.scene == 'playing':
                    if ev.key == pygame.K_p:
                        self.paused = not self.paused
                    elif ev.key == pygame.K_ESCAPE:
                        self.scene = 'menu'
                        self.paused = False

                # ---- Game over ----
                elif self.scene == 'over':
                    if ev.key == pygame.K_RETURN:
                        # Replay
                        self._restart()
                    elif ev.key == pygame.K_ESCAPE:
                        self.scene = 'menu'
                        self.show_diff = False

    def _handle_player_input(self):
        if not self.player or not self.player.alive or self.player.moving:
            return

        keys = pygame.key.get_pressed()
        moved = False

        dir_map = {
            pygame.K_UP:    UP,
            pygame.K_w:     UP,
            pygame.K_DOWN:  DOWN,
            pygame.K_s:     DOWN,
            pygame.K_LEFT:  LEFT,
            pygame.K_a:     LEFT,
            pygame.K_RIGHT: RIGHT,
            pygame.K_d:     RIGHT,
        }

        for key, direction in dir_map.items():
            if keys[key]:
                nx = self.player.igx() + DX[direction]
                ny = self.player.igy() + DY[direction]
                if self._can_enter(nx, ny, exclude=self.player):
                    self.player.start_move(direction, nx, ny)
                else:
                    self.player.dir = direction   # face direction even if blocked
                moved = True
                break

        # Shoot
        if keys[pygame.K_SPACE]:
            self._player_shoot()

    def _can_enter(self, nx, ny, exclude=None):
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            return False
        if self.map_[ny][nx] in (BRICK, STEEL, WATER, EAGLE):
            return False
        for tank in [self.player] + self.enemies:
            if tank is exclude or not tank.alive:
                continue
            if tank.igx() == nx and tank.igy() == ny:
                return False
        return True

    def _player_shoot(self):
        if not self.player or not self.player.alive:
            return
        # Check cooldown
        self.player.fire_timer = max(0, self.player.fire_timer - 0)
        if self.player.fire_timer > 0:
            return
        # Count player bullets already alive
        pb = [b for b in self.bullets if b.owner == 'player']
        if len(pb) >= 2:
            return
        cx, cy = self.player.pixel_center()
        from entities import Bullet
        spd = self.diff_cfg['bullet_speed'] * 1.2
        col = C["bullet_player"]
        b = Bullet(cx, cy, self.player.dir, 'player', spd, col)
        self.bullets.append(b)
        self.player.fire_timer = self.diff_cfg['player_fire_cd']

    # ── Loading update ────────────────────────────────────────

    def _update_loading(self):
        if self.scene != 'loading':
            return
        self.load_frames += 1
        # Ease-out progress so it slows near 100%
        t = min(1.0, self.load_frames / self.load_duration)
        self.load_progress = t * t * (3 - 2 * t)   # smoothstep
        if self.load_frames >= self.load_duration:
            self._finish_loading()

    def _finish_loading(self):
        self.load_progress = 1.0
        self.scene = 'menu'

    # ── Update ────────────────────────────────────────────────

    def _update(self):
        if self.paused or self.scene != 'playing':
            return

        # self.renderer.tick() -> called in main run loop instead

        # Banner countdown
        if self.banner_timer > 0:
            self.banner_timer -= 1

        # Player fire timer countdown
        if self.player and self.player.alive:
            self.player.fire_timer = max(0, self.player.fire_timer - 1)

        # Player movement
        self.player.update_movement()

        # Enemy spawning
        self.spawn_timer += 1
        alive_count = sum(1 for e in self.enemies if e.alive)
        if (alive_count < 4
                and self.spawn_queue
                and self.spawn_timer >= self.diff_cfg['spawn_delay']):
            self._try_spawn_enemy()
            self.spawn_timer = 0

        # Enemy AI + movement
        for e in self.enemies:
            if not e.alive:
                continue
            e.update_movement()
            if not e.moving:
                e.fire_timer = max(0, e.fire_timer - 1)
                bullet = e.decide(self.map_, self.player, self.enemies, EAGLE_POS)
                if bullet:
                    self.bullets.append(bullet)

        # Bullet updates
        dead_bullets = []
        for b in self.bullets:
            b.update()
            gx, gy = _bullet_tile(b.x, b.y)

            # Out of bounds
            if not (0 <= gx < COLS and 0 <= gy < ROWS):
                dead_bullets.append(b)
                continue

            # Tile collision
            t = self.map_[gy][gx]
            if t == BRICK:
                self.map_[gy][gx] = EMPTY
                self._add_explosion(b.x, b.y, 22)
                dead_bullets.append(b)
                continue
            if t == STEEL:
                self._add_explosion(b.x, b.y, 16)
                dead_bullets.append(b)
                continue
            if t == EAGLE:
                self.eagle_alive = False
                self._add_explosion(b.x, b.y, 40)
                dead_bullets.append(b)
                continue

            # Tank collision
            hit = self._check_bullet_tank_hit(b, gx, gy)
            if hit:
                dead_bullets.append(b)

        self.bullets = [b for b in self.bullets if b not in dead_bullets]

        # Explosions
        for ex in self.explosions:
            ex.update()
        self.explosions = [ex for ex in self.explosions if ex.alive]

        # Win / lose conditions
        if not self.eagle_alive:
            self._end_game(won=False)
            return

        if self.player and not self.player.alive:
            self.lives -= 1
            if self.lives <= 0:
                self._end_game(won=False)
            else:
                # Respawn player
                self.player = PlayerTank(4, 23,
                                         fire_cd=self.diff_cfg['player_fire_cd'],
                                         speed_tps=4.0)
                self.player.lives = self.lives
                self.player.score = self.score
                self._add_explosion(
                    GRID_OFFSET_X + 4 * TILE + TILE//2,
                    GRID_OFFSET_Y + 23 * TILE + TILE//2, 40)
            return

        all_done = (not self.spawn_queue
                    and all(not e.alive for e in self.enemies))
        if all_done:
            self.score += (self.level * 1000)
            self.level += 1
            if self.level > 3:
                self._end_game(won=True)
            else:
                self._setup_level()

    def _check_bullet_tank_hit(self, b, gx, gy):
        """Return True if bullet hit a tank."""
        if b.owner != 'player' and self.player and self.player.alive:
            px, py = self.player.igx(), self.player.igy()
            if abs(gx - px) <= 0 and abs(gy - py) <= 0:
                self._add_explosion(b.x, b.y, 36)
                self.player.alive = False
                return True

        if b.owner == 'player':
            for e in self.enemies:
                if not e.alive:
                    continue
                if abs(gx - e.igx()) <= 0 and abs(gy - e.igy()) <= 0:
                    e.hp -= 1
                    e.flash_timer = 10
                    if hasattr(e, 'on_hit'):
                        e.on_hit()
                    if e.hp <= 0:
                        e.alive = False
                        self.score += {'basic': 100, 'fast': 200,
                                       'armor': 400, 'power': 300,
                                       'boss': 2000}.get(e.subtype, 100)
                        self._add_explosion(b.x, b.y, 48)
                    else:
                        self._add_explosion(b.x, b.y, 24)
                    return True
        return False

    def _add_explosion(self, cx, cy, r=36):
        self.explosions.append(Explosion(int(cx), int(cy), max_r=r))

    def _end_game(self, won):
        self.over_won = won
        if won:
            self.score += self.lives * 500
        # Persist to leaderboard
        self.new_score_rank = highscore.save_score(
            self.score, self.difficulty, self.level, won)
        self.cached_scores  = highscore.load_scores()
        self.scene = 'over'

    def _start_game(self):
        self.level  = 1
        self.score  = 0
        self.lives  = 3
        self.show_diff = False
        self._setup_level()
        self.scene  = 'playing'

    def _restart(self):
        self._start_game()

    # ── Render ────────────────────────────────────────────────

    def _render(self):
        self.screen.fill(C["bg"])

        if self.scene == 'loading':
            self.renderer.draw_loading_screen(self.load_progress)

        elif self.scene == 'menu':
            self.renderer.draw_title_screen(self.menu_sel, self.show_diff)

        elif self.scene == 'scores':
            self.renderer.draw_highscores(self.cached_scores, self.new_score_rank)

        elif self.scene == 'how':
            self.renderer.draw_title_screen(self.menu_sel, False)
            self.renderer.draw_how_to_play()

        elif self.scene == 'playing':
            # Top bar
            self.renderer.draw_topbar({'level': self.level})

            # Map
            self.renderer.draw_map(self.map_, self.eagle_alive)

            # Entities (below forest)
            if self.player and self.player.alive:
                flash = getattr(self.player, 'flash_timer', 0) > 0
                self.renderer.draw_tank(self.player, flash=flash)

            for e in self.enemies:
                if e.alive:
                    flash = getattr(e, 'flash_timer', 0) > 0
                    if flash:
                        e.flash_timer = max(0, e.flash_timer - 1)
                    self.renderer.draw_tank(e, flash=flash)

            # Forest overlay (hides tanks underneath)
            self.renderer.draw_forest_overlay(self.map_)

            # Bullets
            for b in self.bullets:
                self.renderer.draw_bullet(b)

            # Explosions
            for ex in self.explosions:
                self.renderer.draw_explosion(ex)

            # Grid border
            self.renderer.draw_grid_border()

            # HUD
            boss_info = None
            for e in self.enemies:
                if e.alive and e.subtype == 'boss':
                    boss_info = {
                        'boss_hp':    e.hp,
                        'boss_max_hp': e.max_hp,
                        'boss_phase': getattr(e, 'phase', 1),
                    }
                    break

            pool_rem = len(self.spawn_queue)
            alive_cnt = sum(1 for e in self.enemies if e.alive)

            hud_state = {
                'level':          self.level,
                'score':          self.score,
                'lives':          self.lives,
                'difficulty':     self.difficulty,
                'pool_remaining': pool_rem,
                'pool_total':     self.pool_total,
                'enemies_alive':  alive_cnt,
            }
            if boss_info:
                hud_state.update(boss_info)

            self.renderer.draw_hud(hud_state)

            # Level banner
            if self.banner_timer > 0:
                alpha = min(1.0, self.banner_timer / 60.0)
                name  = LEVEL_NAMES.get(self.level, f'Level {self.level}')
                self.renderer.draw_level_banner(self.level, name, alpha)

            # Pause
            if self.paused:
                self.renderer.draw_pause()

        elif self.scene == 'over':
            self.renderer.draw_title_screen(self.menu_sel, False)
            self.renderer.draw_game_over(
                self.score, self.over_won,
                is_highscore=(self.new_score_rank >= 0))

        pygame.display.flip()

    # ── Main loop ─────────────────────────────────────────────

    def run(self):
        while self.running:
            self._handle_events()
            if self.scene == 'loading':
                self._update_loading()
            elif self.scene == 'playing' and not self.paused:
                self._handle_player_input()
                self._update()
            self.renderer.tick()   # advance anim even on menu / loading
            self._render()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


# ── Entry point ───────────────────────────────────────────────

def main():
    game = Game()
    game.run()


if __name__ == '__main__':
    main()
