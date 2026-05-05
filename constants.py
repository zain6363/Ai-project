# ============================================================
#  BATTLE CITY — CONSTANTS & CONFIGURATION
#  AL2002 Artificial Intelligence Lab | Spring 2026
# ============================================================

import pygame

# --- Window & Grid ---
TILE        = 28          # pixels per tile
COLS        = 26
ROWS        = 26
GRID_W      = COLS * TILE  # 728
GRID_H      = ROWS * TILE  # 728
HUD_W       = 220
WIN_W       = GRID_W + HUD_W
WIN_H       = GRID_H + 60  # extra top bar
GRID_OFFSET_X = 0
GRID_OFFSET_Y = 40         # top bar height

FPS = 60

# --- Tile Types ---
EMPTY  = 0
BRICK  = 1
STEEL  = 2
WATER  = 3
FOREST = 4
EAGLE  = 5

# --- Directions ---
UP    = 0
RIGHT = 1
DOWN  = 2
LEFT  = 3
DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]

# --- Colour Palette (rich retro-arcade theme) ---
C = {
    # Background / UI
    "bg":           (8,   8,  14),
    "panel":        (14,  16,  24),
    "panel_border": (40,  50,  80),
    "topbar":       (10,  12,  20),
    "topbar_line":  (255, 180,   0),

    # Terrain
    "empty":        (14,  14,  20),
    "brick_light":  (180,  60,  40),
    "brick_dark":   (110,  30,  20),
    "steel_light":  (100, 120, 150),
    "steel_dark":   (50,   65,  85),
    "water_a":      (20,   60, 160),
    "water_b":      (10,   40, 120),
    "forest_a":     (20,  100,  30),
    "forest_b":     (10,   60,  18),
    "forest_c":     (30,  130,  40),
    "eagle_gold":   (220, 160,   0),
    "eagle_dark":   (140,  90,   0),

    # Tanks
    "player":       (255, 210,   0),
    "player_body":  (200, 160,   0),
    "basic":        (160, 160, 160),
    "basic_body":   (100, 100, 100),
    "fast":         ( 60, 180, 255),
    "fast_body":    ( 20, 110, 200),
    "armor":        (255,  90,  20),
    "armor_body":   (180,  50,   5),
    "power":        (255, 180,  40),
    "power_body":   (200, 130,  10),
    "boss":         (180,  40, 255),
    "boss_body":    (100,  10, 200),

    # Bullets
    "bullet_player": (255, 255, 100),
    "bullet_enemy":  (255,  80,  80),

    # HUD
    "hud_text":     (220, 220, 240),
    "hud_dim":      (100, 100, 130),
    "hud_gold":     (255, 200,   0),
    "hud_green":    ( 50, 220,  80),
    "hud_red":      (255,  60,  60),
    "hud_blue":     ( 60, 160, 255),
    "hud_orange":   (255, 140,   0),
    "hud_purple":   (200,  80, 255),

    # Difficulty badges
    "easy_bg":      ( 20, 160,  60),
    "easy_fg":      (200, 255, 210),
    "medium_bg":    (180, 120,   0),
    "medium_fg":    (255, 240, 160),
    "hard_bg":      (160,  20,  20),
    "hard_fg":      (255, 200, 200),

    # Effects
    "exp_outer":    (255, 120,   0),
    "exp_inner":    (255, 240, 180),
    "exp_core":     (255, 255, 255),
    "spark":        (255, 220,   0),

    # White / Black
    "white":        (255, 255, 255),
    "black":        (  0,   0,   0),
    "dim":          ( 30,  30,  45),
}

# --- Difficulty Configs ---
DIFF = {
    "easy": {
        "enemy_speed":    1.5,   # tiles/sec
        "bullet_speed":   8.0,   # px/frame (at 60fps)
        "enemy_fire_cd":  120,   # frames between shots
        "player_fire_cd": 18,
        "armor_hp":       4,
        "pool_size":      12,
        "spawn_delay":    80,
    },
    "medium": {
        "enemy_speed":    2.2,
        "bullet_speed":   10.0,
        "enemy_fire_cd":  80,
        "player_fire_cd": 15,
        "armor_hp":       4,
        "pool_size":      16,
        "spawn_delay":    60,
    },
    "hard": {
        "enemy_speed":    3.2,
        "bullet_speed":   13.0,
        "enemy_fire_cd":  50,
        "player_fire_cd": 12,
        "armor_hp":       4,
        "pool_size":      20,
        "spawn_delay":    40,
    },
}

SPAWN_POINTS = [(0, 0), (12, 0), (24, 0)]

LEVEL_NAMES = {1: "BRICK MAZE", 2: "STEEL FORTRESS", 3: "BOSS BATTLE"}