"""
Spell Discoverer — Test Build
Controls:
  WASD / Arrow keys : Move
  Left Click        : Cast active spell (aims at mouse)
  1-5               : Select active hotkey slot
  B                 : Open / close Spell Book
  R (in game)       : Research a random new spell
  R (game over)     : Restart

Spell Book:
  Click a spell     : Select it
  Arrow Up/Down     : Navigate list
  1-5               : Assign selected spell to that hotkey slot
  Presets tab       : Save / load / delete hotkey presets
"""

import pygame
import sys
import math
import random
from spells import SpellBook, Spell

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 1024
SCREEN_H = 768
HUD_H    = 78
GAME_H   = SCREEN_H - HUD_H
FPS      = 60

BG       = (18, 18, 28)
GRID_C   = (26, 26, 40)
WHITE    = (255, 255, 255)
GRAY     = (110, 110, 130)
GOLD     = (255, 205, 50)
RED      = (220, 60,  60)
GREEN    = (60,  210, 80)


# ── Player ─────────────────────────────────────────────────────────────────────
class Player:
    RADIUS  = 14
    SPEED   = 4
    MAX_HP  = 100

    def __init__(self):
        self.x        = float(SCREEN_W // 2)
        self.y        = float(GAME_H   // 2)
        self.hp       = float(self.MAX_HP)
        self.cooldown = 0

    def update(self, keys):
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if dx and dy:
            dx *= 0.7071; dy *= 0.7071
        r = self.RADIUS
        self.x = max(r, min(SCREEN_W - r, self.x + dx * self.SPEED))
        self.y = max(r, min(GAME_H   - r, self.y + dy * self.SPEED))
        if self.cooldown > 0:
            self.cooldown -= 1

    def draw(self, surf):
        x, y, r = int(self.x), int(self.y), self.RADIUS
        pygame.draw.circle(surf, (50, 190, 80), (x, y), r)
        pygame.draw.circle(surf, WHITE,         (x, y), r, 2)
        # HP bar
        bw = 36
        pygame.draw.rect(surf, (100, 20, 20), (x - bw//2, y - r - 10, bw, 5))
        fill = int(bw * max(0, self.hp) / self.MAX_HP)
        col  = GREEN if self.hp > 40 else (220, 160, 20) if self.hp > 20 else RED
        pygame.draw.rect(surf, col, (x - bw//2, y - r - 10, fill, 5))


# ── Enemy ──────────────────────────────────────────────────────────────────────
class Enemy:
    RADIUS   = 13
    BASE_HP  = 30
    BASE_SPD = 1.4

    def __init__(self, x, y, wave=1):
        self.x      = float(x)
        self.y      = float(y)
        self.hp     = self.BASE_HP + wave * 5
        self.max_hp = self.hp
        self.speed  = self.BASE_SPD + wave * 0.08
        shade = min(230, 70 + wave * 15)
        self.color  = (shade, max(20, 80 - wave * 10), max(20, 80 - wave * 10))

    def update(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        d  = math.hypot(dx, dy)
        if d:
            self.x += dx / d * self.speed
            self.y += dy / d * self.speed

    def take_damage(self, amount) -> bool:
        self.hp -= amount
        return self.hp <= 0

    def draw(self, surf):
        x, y, r = int(self.x), int(self.y), self.RADIUS
        pygame.draw.rect(surf, self.color, (x - r, y - r, r * 2, r * 2))
        pygame.draw.rect(surf, WHITE,      (x - r, y - r, r * 2, r * 2), 1)
        bw = 30
        pygame.draw.rect(surf, (100, 20, 20), (x - bw//2, y - r - 8, bw, 4))
        fill = int(bw * max(0, self.hp) / self.max_hp)
        pygame.draw.rect(surf, GREEN, (x - bw//2, y - r - 8, fill, 4))


# ── Projectile ─────────────────────────────────────────────────────────────────
class Projectile:
    def __init__(self, x, y, dx, dy, spell: Spell):
        self.x, self.y   = float(x), float(y)
        self.dx, self.dy = dx, dy
        self.speed  = spell.speed
        self.damage = spell.damage
        self.size   = spell.size
        self.color  = spell.color
        self.alive  = True

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        if not (-60 < self.x < SCREEN_W + 60 and -60 < self.y < GAME_H + 60):
            self.alive = False

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(surf, self.color, (x, y), self.size)
        r, g, b = self.color
        pygame.draw.circle(surf, (r // 3, g // 3, b // 3), (x, y), self.size + 4, 2)


# ── Floating notification ──────────────────────────────────────────────────────
class Note:
    def __init__(self, text, x, y, color=GOLD, duration=160):
        self.text     = text
        self.x        = float(x)
        self.y        = float(y)
        self.color    = color
        self.duration = duration
        self.timer    = 0

    def update(self) -> bool:
        self.y    -= 0.4
        self.timer += 1
        return self.timer >= self.duration

    def draw(self, surf, font):
        ratio = 1.0 - self.timer / self.duration
        c = tuple(max(0, int(ch * ratio)) for ch in self.color)
        t = font.render(self.text, True, c)
        surf.blit(t, (int(self.x) - t.get_width() // 2, int(self.y)))


# ── Spell Book UI ──────────────────────────────────────────────────────────────
class SpellBookUI:
    PX, PY = 70, 45
    PW     = SCREEN_W - 140
    PH     = SCREEN_H - 90
    ROW_H  = 27
    VISIBLE = 16

    def __init__(self, sb: SpellBook):
        self.sb       = sb
        self.open     = False
        self.tab      = "spells"   # "spells" | "presets"
        self.sel      = -1         # selected row (view-relative)
        self.scroll   = 0
        self.naming   = False
        self.name_buf = ""

    def toggle(self):
        self.open = not self.open
        if self.open:
            self.sel = -1; self.scroll = 0

    def handle_event(self, ev):
        if not self.open:
            return
        if ev.type == pygame.KEYDOWN:
            if self.naming:
                if ev.key == pygame.K_RETURN and self.name_buf.strip():
                    self.sb.save_preset(self.name_buf.strip())
                    self.naming = False; self.name_buf = ""
                elif ev.key == pygame.K_ESCAPE:
                    self.naming = False; self.name_buf = ""
                elif ev.key == pygame.K_BACKSPACE:
                    self.name_buf = self.name_buf[:-1]
                elif ev.unicode.isprintable():
                    self.name_buf += ev.unicode
                return

            if ev.key in (pygame.K_ESCAPE, pygame.K_b):
                self.open = False; return

            if self.tab == "spells":
                # Assign selected spell to hotkey slot 1-5
                slot_map = {
                    pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                    pygame.K_4: 3, pygame.K_5: 4,
                }
                if ev.key in slot_map and self.sel >= 0:
                    real = self.scroll + self.sel
                    if real < len(self.sb.discovered_ids):
                        self.sb.assign_to_slot(slot_map[ev.key],
                                               self.sb.discovered_ids[real])
                if ev.key == pygame.K_UP and self.sel > 0:
                    self.sel -= 1
                elif ev.key == pygame.K_DOWN:
                    cap = min(self.VISIBLE, len(self.sb.discovered_ids)) - 1
                    if self.sel < cap:
                        self.sel += 1

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            self._click(*ev.pos)
        elif ev.type == pygame.MOUSEWHEEL:
            if self.tab == "spells":
                mx_scroll = max(0, len(self.sb.discovered_ids) - self.VISIBLE)
                self.scroll = max(0, min(mx_scroll, self.scroll - ev.y))

    def _click(self, mx, my):
        PX, PY, PW = self.PX, self.PY, self.PW
        # Tab buttons
        if pygame.Rect(PX + 8,   PY + 36, 140, 26).collidepoint(mx, my):
            self.tab = "spells";  self.sel = -1; return
        if pygame.Rect(PX + 158, PY + 36, 110, 26).collidepoint(mx, my):
            self.tab = "presets"; self.sel = -1; return

        list_y = PY + 70
        if self.tab == "spells":
            for i in range(self.VISIBLE):
                idx = self.scroll + i
                if idx >= len(self.sb.discovered_ids):
                    break
                r = pygame.Rect(PX + 8, list_y + 18 + i * self.ROW_H, PW - 16, self.ROW_H - 2)
                if r.collidepoint(mx, my):
                    self.sel = i if self.sel != i else -1
                    return

        elif self.tab == "presets":
            names  = list(self.sb.presets.keys())
            row_h  = 40
            for i, name in enumerate(names):
                ry = list_y + i * row_h
                if pygame.Rect(PX + 8, ry, PW - 170, row_h - 4).collidepoint(mx, my):
                    self.sb.load_preset(name); return
                if pygame.Rect(PX + PW - 80, ry + 6, 68, 26).collidepoint(mx, my):
                    self.sb.delete_preset(name); return
            save_y = list_y + len(names) * row_h + 12
            if pygame.Rect(PX + 8, save_y, 160, 32).collidepoint(mx, my) and not self.naming:
                self.naming = True; self.name_buf = ""

    def draw(self, screen, fonts):
        if not self.open:
            return
        PX, PY, PW, PH = self.PX, self.PY, self.PW, self.PH

        # Dim background
        dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 155))
        screen.blit(dim, (0, 0))

        # Panel
        pygame.draw.rect(screen, (25, 25, 40), (PX, PY, PW, PH), border_radius=8)
        pygame.draw.rect(screen, (80, 80, 130), (PX, PY, PW, PH), 2, border_radius=8)

        # Title
        t = fonts["large"].render("SPELL BOOK", True, GOLD)
        screen.blit(t, (PX + PW // 2 - t.get_width() // 2, PY + 8))
        esc_t = fonts["small"].render("[ESC] Close", True, GRAY)
        screen.blit(esc_t, (PX + PW - esc_t.get_width() - 10, PY + 12))

        # Tabs
        for label, key, tx in [
            (f"Spells ({len(self.sb.discovered_ids)})", "spells",  PX + 8),
            ("Presets",                                  "presets", PX + 158),
        ]:
            active = self.tab == key
            pygame.draw.rect(screen, (52, 52, 78) if active else (32, 32, 50),
                             (tx, PY + 36, 140, 26), border_radius=4)
            if active:
                pygame.draw.rect(screen, GOLD, (tx, PY + 36, 140, 26), 1, border_radius=4)
            lt = fonts["medium"].render(label, True, GOLD if active else GRAY)
            screen.blit(lt, (tx + 70 - lt.get_width() // 2, PY + 40))

        pygame.draw.line(screen, (55, 55, 85), (PX + 5, PY + 66), (PX + PW - 5, PY + 66))
        list_y = PY + 70

        # ── Spells tab ─────────────────────────────────────────────────────────
        if self.tab == "spells":
            # Column headers
            screen.blit(fonts["small"].render("Spell",  True, GRAY), (PX + 34, list_y + 2))
            screen.blit(fonts["small"].render("Slot",   True, GRAY), (PX + PW - 195, list_y + 2))
            screen.blit(fonts["small"].render("DMG",    True, GRAY), (PX + PW - 130, list_y + 2))
            screen.blit(fonts["small"].render("SPD",    True, GRAY), (PX + PW - 75,  list_y + 2))
            pygame.draw.line(screen, (55, 55, 85),
                             (PX + 8, list_y + 16), (PX + PW - 8, list_y + 16))

            row_start = list_y + 18
            for i in range(self.VISIBLE):
                idx = self.scroll + i
                if idx >= len(self.sb.discovered_ids):
                    break
                sid   = self.sb.discovered_ids[idx]
                spell = Spell(sid)
                ry    = row_start + i * self.ROW_H

                if self.sel == i:
                    pygame.draw.rect(screen, (52, 52, 82),
                                     (PX + 6, ry - 1, PW - 12, self.ROW_H - 2),
                                     border_radius=3)

                pygame.draw.circle(screen, spell.color, (PX + 20, ry + 10), 7)
                nt = fonts["medium"].render(spell.name, True,
                                            WHITE if self.sel == i else (195, 200, 220))
                screen.blit(nt, (PX + 32, ry + 2))

                # Show which slots have this spell
                hx = PX + PW - 195
                for slot, hid in enumerate(self.sb.hotkeys):
                    if hid == sid:
                        ht = fonts["small"].render(f"[{slot+1}]", True, GOLD)
                        screen.blit(ht, (hx, ry + 4))
                        hx += 26

                dt = fonts["medium"].render(str(spell.damage), True, (220, 100, 100))
                screen.blit(dt, (PX + PW - 130, ry + 2))
                st = fonts["medium"].render(str(spell.speed),  True, (100, 160, 255))
                screen.blit(st, (PX + PW - 75, ry + 2))

            # Scrollbar
            total = len(self.sb.discovered_ids)
            if total > self.VISIBLE:
                bar_h   = self.VISIBLE * self.ROW_H
                thumb_h = max(20, bar_h * self.VISIBLE // total)
                thumb_y = row_start + (bar_h - thumb_h) * self.scroll // max(1, total - self.VISIBLE)
                pygame.draw.rect(screen, GRAY, (PX + PW - 6, row_start, 4, bar_h), border_radius=2)
                pygame.draw.rect(screen, GOLD, (PX + PW - 6, thumb_y,  4, thumb_h), border_radius=2)

            # Bottom instruction
            if self.sel >= 0:
                real = self.scroll + self.sel
                if real < len(self.sb.discovered_ids):
                    sp_name = Spell(self.sb.discovered_ids[real]).name
                    msg = f'"{sp_name}"  ->  press 1-5 to assign'
                    it  = fonts["medium"].render(msg, True, GOLD)
                    screen.blit(it, (PX + PW // 2 - it.get_width() // 2, PY + PH - 26))
            else:
                it = fonts["small"].render(
                    "Click or use arrow keys to select a spell, then press 1-5 to assign to a slot",
                    True, GRAY)
                screen.blit(it, (PX + PW // 2 - it.get_width() // 2, PY + PH - 22))

        # ── Presets tab ────────────────────────────────────────────────────────
        elif self.tab == "presets":
            names = list(self.sb.presets.keys())
            row_h = 40
            if not names:
                nt = fonts["medium"].render("No presets saved yet.", True, GRAY)
                screen.blit(nt, (PX + PW // 2 - nt.get_width() // 2, list_y + 20))

            for i, name in enumerate(names):
                ry = list_y + i * row_h
                pygame.draw.rect(screen, (38, 38, 56),
                                 (PX + 8, ry, PW - 100, row_h - 4), border_radius=4)
                nt = fonts["medium"].render(name, True, WHITE)
                screen.blit(nt, (PX + 14, ry + 4))

                # Slot preview (first 3 spells)
                bits = []
                for sid in self.sb.presets[name]:
                    bits.append(Spell(sid).name[:12] if sid is not None else "---")
                prev = "  |  ".join(bits[:3])
                if len(bits) > 3: prev += "  ..."
                pt = fonts["small"].render(prev, True, GRAY)
                screen.blit(pt, (PX + 14, ry + 22))

                # LOAD button
                lx = PX + PW - 155
                pygame.draw.rect(screen, (40, 120, 65), (lx, ry + 6, 60, 26), border_radius=4)
                lt = fonts["small"].render("LOAD", True, WHITE)
                screen.blit(lt, (lx + 30 - lt.get_width() // 2, ry + 11))

                # DELETE button
                dx = PX + PW - 88
                pygame.draw.rect(screen, (130, 40, 40), (dx, ry + 6, 68, 26), border_radius=4)
                dlt = fonts["small"].render("DELETE", True, WHITE)
                screen.blit(dlt, (dx + 34 - dlt.get_width() // 2, ry + 11))

            save_y = list_y + len(names) * row_h + 14
            if self.naming:
                pygame.draw.rect(screen, (38, 38, 58), (PX + 8, save_y, 240, 30), border_radius=4)
                pygame.draw.rect(screen, GOLD,         (PX + 8, save_y, 240, 30), 1, border_radius=4)
                it = fonts["medium"].render(self.name_buf + "|", True, WHITE)
                screen.blit(it, (PX + 14, save_y + 5))
                ht = fonts["small"].render("ENTER to save  |  ESC to cancel", True, GOLD)
                screen.blit(ht, (PX + 258, save_y + 8))
            else:
                pygame.draw.rect(screen, (45, 85, 145), (PX + 8, save_y, 160, 32), border_radius=4)
                bt = fonts["medium"].render("+ Save Preset", True, WHITE)
                screen.blit(bt, (PX + 88 - bt.get_width() // 2, save_y + 6))
                ht = fonts["small"].render("saves current hotkey slots 1-5", True, GRAY)
                screen.blit(ht, (PX + 178, save_y + 10))


# ── HUD ────────────────────────────────────────────────────────────────────────
def draw_hud(screen, sb: SpellBook, fonts, score: int, player_hp: float, player_max_hp: int):
    pygame.draw.rect(screen, (16, 16, 26), (0, 0, SCREEN_W, HUD_H))
    pygame.draw.line(screen, (55, 55, 88), (0, HUD_H - 1), (SCREEN_W, HUD_H - 1), 2)

    SLOT_W, SLOT_H, GAP = 158, 60, 4
    sx0, sy = 8, 9

    for i in range(5):
        sx     = sx0 + i * (SLOT_W + GAP)
        active = sb.active_slot == i
        pygame.draw.rect(screen, (46, 46, 72) if active else (26, 26, 42),
                         (sx, sy, SLOT_W, SLOT_H), border_radius=5)
        pygame.draw.rect(screen, GOLD if active else (50, 50, 80),
                         (sx, sy, SLOT_W, SLOT_H), 2, border_radius=5)
        key_t = fonts["small"].render(str(i + 1), True, GOLD if active else (70, 70, 95))
        screen.blit(key_t, (sx + 5, sy + 3))

        sid = sb.hotkeys[i]
        if sid is not None:
            spell = Spell(sid)
            pygame.draw.circle(screen, spell.color, (sx + 18, sy + 38), 7)
            nt = fonts["small"].render(spell.name[:22], True, WHITE)
            screen.blit(nt, (sx + 30, sy + 28))
            dt = fonts["small"].render(f"dmg:{spell.damage}  spd:{spell.speed}", True, (150, 150, 170))
            screen.blit(dt, (sx + 30, sy + 42))
        else:
            et = fonts["medium"].render("-- empty --", True, (55, 55, 75))
            screen.blit(et, (sx + SLOT_W // 2 - et.get_width() // 2, sy + SLOT_H // 2 - 6))

    # HP bar (right side)
    rx = SCREEN_W - 195
    hp_label = fonts["small"].render("HP", True, WHITE)
    screen.blit(hp_label, (rx, 12))
    bx = rx + 24
    pygame.draw.rect(screen, (80, 18, 18), (bx, 12, 160, 16), border_radius=4)
    fill = int(160 * max(0, player_hp) / player_max_hp)
    col  = GREEN if player_hp > 40 else (220, 160, 20) if player_hp > 20 else RED
    pygame.draw.rect(screen, col, (bx, 12, fill, 16), border_radius=4)
    hp_num = fonts["small"].render(f"{max(0, int(player_hp))}/{player_max_hp}", True, WHITE)
    screen.blit(hp_num, (bx + 80 - hp_num.get_width() // 2, 14))

    # Kill counter
    kt = fonts["medium"].render(f"Kills: {score}", True, WHITE)
    screen.blit(kt, (rx, 36))

    # Controls hint (bottom of HUD)
    hint = fonts["small"].render(
        "[WASD] Move   [LClick] Cast   [1-5] Select slot   [B] Spell Book   [R] Research",
        True, (55, 55, 80))
    screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, HUD_H - 17))


# ── Background ─────────────────────────────────────────────────────────────────
def draw_background(surf):
    surf.fill(BG)
    for x in range(0, SCREEN_W + 1, 60):
        pygame.draw.line(surf, GRID_C, (x, 0), (x, GAME_H))
    for y in range(0, GAME_H + 1, 60):
        pygame.draw.line(surf, GRID_C, (0, y), (SCREEN_W, y))


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Spell Discoverer — Test Build")
    clock  = pygame.time.Clock()

    fonts = {
        "small":  pygame.font.SysFont("consolas", 13),
        "medium": pygame.font.SysFont("consolas", 15),
        "large":  pygame.font.SysFont("consolas", 22),
        "huge":   pygame.font.SysFont("consolas", 38),
    }

    sb        = SpellBook()
    ui        = SpellBookUI(sb)
    game_surf = pygame.Surface((SCREEN_W, GAME_H))

    def new_game():
        return {
            "player":      Player(),
            "enemies":     [],
            "projectiles": [],
            "notes":       [],
            "score":       0,
            "wave":        1,
            "spawn_t":     0,
            "spawn_int":   120,
            "game_over":   False,
        }

    state = new_game()

    while True:
        clock.tick(FPS)
        mx, my = pygame.mouse.get_pos()
        gmx    = mx
        gmy    = my - HUD_H   # game-space mouse y

        player      = state["player"]
        enemies     = state["enemies"]
        projectiles = state["projectiles"]
        notes       = state["notes"]

        # ── Events ─────────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            was_open = ui.open
            ui.handle_event(ev)
            if was_open:
                continue   # all events consumed while UI was open

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_b:
                    ui.toggle()

                elif ev.key == pygame.K_r:
                    if state["game_over"]:
                        state = new_game()
                    else:
                        sid = sb.discover_random()
                        if sid:
                            sp = Spell(sid)
                            notes.append(Note(
                                f"Researched: {sp.name}",
                                SCREEN_W // 2, GAME_H // 2 - 70,
                                color=(80, 220, 200), duration=200
                            ))

                elif not state["game_over"]:
                    slot_map = {
                        pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                        pygame.K_4: 3, pygame.K_5: 4,
                    }
                    if ev.key in slot_map:
                        sb.active_slot = slot_map[ev.key]

            if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                    and not state["game_over"] and not ui.open):
                spell = sb.get_active_spell()
                if spell and player.cooldown <= 0:
                    dx = gmx - player.x
                    dy = gmy - player.y
                    d  = math.hypot(dx, dy)
                    if d:
                        proj = Projectile(player.x, player.y, dx / d, dy / d, spell)
                        projectiles.append(proj)
                        player.cooldown = 16
                        # Floating spell name on cast
                        notes.append(Note(
                            spell.name, player.x, player.y - 28,
                            color=spell.color, duration=55
                        ))

        # ── Update ─────────────────────────────────────────────────────────────
        if not state["game_over"] and not ui.open:
            keys = pygame.key.get_pressed()
            player.update(keys)

            # Enemy spawn
            state["spawn_t"] += 1
            if state["spawn_t"] >= state["spawn_int"]:
                state["spawn_t"] = 0
                count = 1 + state["wave"] // 4
                for _ in range(count):
                    side = random.randint(0, 3)
                    if   side == 0: ex, ey = random.randint(0, SCREEN_W), -20
                    elif side == 1: ex, ey = SCREEN_W + 20, random.randint(0, GAME_H)
                    elif side == 2: ex, ey = random.randint(0, SCREEN_W), GAME_H + 20
                    else:           ex, ey = -20, random.randint(0, GAME_H)
                    enemies.append(Enemy(ex, ey, state["wave"]))

            # Enemy update + collision with player
            for e in enemies:
                e.update(player)
                if math.hypot(e.x - player.x, e.y - player.y) < player.RADIUS + e.RADIUS:
                    player.hp -= 0.35

            # Projectile update + hit detection
            for p in projectiles:
                p.update()
                if not p.alive:
                    continue
                for e in enemies:
                    if math.hypot(p.x - e.x, p.y - e.y) < p.size + e.RADIUS:
                        killed = e.take_damage(p.damage)
                        p.alive = False
                        if killed:
                            state["score"] += 1
                            # Wave scaling: every 5 kills
                            new_wave = state["score"] // 5 + 1
                            if new_wave > state["wave"]:
                                state["wave"]      = new_wave
                                state["spawn_int"] = max(55, 120 - new_wave * 7)
                            # 35% chance to drop a new spell on kill
                            if random.random() < 0.35:
                                sid = sb.discover_random()
                                if sid:
                                    sp = Spell(sid)
                                    notes.append(Note(
                                        f"New: {sp.name}",
                                        e.x, e.y,
                                        color=(80, 230, 190), duration=210
                                    ))
                        break

            state["enemies"]     = [e for e in enemies if e.hp > 0]
            state["projectiles"] = [p for p in projectiles if p.alive]
            state["notes"]       = [n for n in notes if not n.update()]

            if player.hp <= 0:
                player.hp = 0
                state["game_over"] = True

        # ── Draw ───────────────────────────────────────────────────────────────
        draw_background(game_surf)
        for e in state["enemies"]:     e.draw(game_surf)
        for p in state["projectiles"]: p.draw(game_surf)
        player.draw(game_surf)
        for n in state["notes"]:       n.draw(game_surf, fonts["small"])

        screen.blit(game_surf, (0, HUD_H))
        draw_hud(screen, sb, fonts, state["score"], player.hp, player.MAX_HP)
        ui.draw(screen, fonts)

        if state["game_over"]:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 140))
            screen.blit(ov, (0, 0))
            gt = fonts["huge"].render("GAME OVER", True, RED)
            screen.blit(gt, (SCREEN_W // 2 - gt.get_width() // 2, SCREEN_H // 2 - 60))
            st = fonts["large"].render(
                f"Kills: {state['score']}   |   Spells found: {len(sb.discovered_ids)}",
                True, WHITE)
            screen.blit(st, (SCREEN_W // 2 - st.get_width() // 2, SCREEN_H // 2 + 5))
            rt = fonts["medium"].render(
                "[R] Restart   [B] View Spell Book", True, GRAY)
            screen.blit(rt, (SCREEN_W // 2 - rt.get_width() // 2, SCREEN_H // 2 + 45))

        pygame.display.flip()


if __name__ == "__main__":
    main()
