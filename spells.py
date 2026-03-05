import random
import json
import os

# ── Word pools ─────────────────────────────────────────────────────────────────
PREFIXES = [
    "Arcane", "Void", "Solar", "Frost", "Crimson", "Shadow", "Thunder", "Ember",
    "Astral", "Primal", "Ancient", "Eldritch", "Divine", "Abyssal", "Radiant",
    "Infernal", "Celestial", "Temporal", "Spectral", "Venomous", "Glacial", "Molten",
    "Cursed", "Blessed", "Twilight", "Dawn", "Dusk", "Ethereal", "Chaotic", "Sacred",
]
ADJECTIVES = [
    "Greater", "Lesser", "Minor", "Major", "Swift", "Silent", "Thunderous",
    "Consuming", "Piercing", "Splitting", "Seeking", "Exploding", "Chained",
    "Scattered", "Focused", "Empowered", "Twin", "Triple", "Raging", "Serene",
    "Wild", "Dense", "Heavy", "Volatile", "Dormant", "Surging", "Waning",
]
ELEMENTS = [
    "Fire", "Ice", "Lightning", "Venom", "Stone", "Light", "Dark", "Wind",
    "Water", "Earth", "Ether", "Blood", "Soul", "Dream", "Chaos", "Void",
    "Nature", "Plague", "Frost", "Steam", "Sand", "Crystal", "Bone", "Star",
    "Iron", "Gold", "Silver", "Obsidian", "Magma", "Acid",
]
TYPES = [
    "Bolt", "Wave", "Nova", "Surge", "Blast", "Strike", "Barrage", "Cascade",
    "Pulse", "Ray", "Torrent", "Eruption", "Vortex", "Lance", "Storm", "Comet",
    "Arrow", "Spear", "Orb", "Ring", "Spiral", "Shard", "Beam", "Burst",
    "Volley", "Dart", "Hammer", "Javelin", "Gust", "Cross",
]
SUFFIXES = [
    "of Ruin", "of Power", "of the Ancients", "of Doom", "of Light", "of Shadows",
    "of the Void", "of Eternity", "of Chaos", "of Order", "of the Fallen",
    "of Ascension", "of the Deep", "of the Storm", "of Flames", "of Ice",
    "Prime", "Omega", "Alpha", "Supreme", "Eternal", "Infinite", "Ultimate",
    "of Fury", "of the Abyss", "of Creation", "of Destruction", "of the Ancients",
]

# Projectile color by keyword found in spell name
KEYWORD_COLORS = {
    "Fire": (255, 100, 30),   "Magma": (255, 70, 20),    "Ember": (255, 130, 40),
    "Crimson": (210, 30, 50), "Blood": (200, 20, 20),    "Infernal": (220, 60, 20),
    "Ice": (100, 210, 255),   "Frost": (140, 220, 255),  "Glacial": (160, 230, 255),
    "Lightning": (255, 255, 80), "Thunder": (220, 220, 80), "Star": (255, 240, 120),
    "Solar": (255, 210, 60),  "Gold": (255, 210, 30),    "Dawn": (255, 200, 100),
    "Venom": (80, 220, 40),   "Acid": (120, 220, 20),    "Plague": (110, 190, 30),
    "Nature": (80, 200, 80),
    "Stone": (160, 130, 90),  "Earth": (140, 110, 70),   "Iron": (150, 160, 170),
    "Obsidian": (70, 30, 90), "Bone": (230, 220, 190),   "Sand": (220, 195, 120),
    "Light": (255, 255, 200), "Radiant": (255, 255, 180), "Blessed": (240, 240, 200),
    "Divine": (240, 230, 160), "Silver": (200, 210, 220), "Crystal": (130, 255, 230),
    "Dark": (120, 50, 180),   "Shadow": (80, 40, 120),   "Void": (60, 0, 100),
    "Abyssal": (50, 0, 80),   "Cursed": (100, 20, 130),  "Eldritch": (130, 50, 160),
    "Soul": (180, 180, 255),  "Dream": (200, 150, 220),  "Ethereal": (200, 160, 255),
    "Spectral": (160, 140, 255), "Astral": (150, 130, 255), "Celestial": (180, 160, 255),
    "Chaos": (200, 50, 200),  "Temporal": (170, 120, 255),
    "Wind": (200, 230, 255),  "Water": (50, 130, 255),   "Steam": (210, 210, 210),
    "Ether": (200, 150, 255),
}
DEFAULT_COLOR = (160, 80, 255)


def generate_spell_name(spell_id: int) -> str:
    """Deterministically generate a spell name from an integer ID."""
    rng = random.Random(spell_id)
    structure = rng.randint(0, 5)
    if structure == 0:
        parts = [rng.choice(PREFIXES), rng.choice(ELEMENTS), rng.choice(TYPES)]
    elif structure == 1:
        parts = [rng.choice(ADJECTIVES), rng.choice(ELEMENTS), rng.choice(TYPES), rng.choice(SUFFIXES)]
    elif structure == 2:
        parts = [rng.choice(PREFIXES), rng.choice(ADJECTIVES), rng.choice(ELEMENTS), rng.choice(TYPES)]
    elif structure == 3:
        parts = [rng.choice(ELEMENTS), rng.choice(TYPES)]
    elif structure == 4:
        parts = [rng.choice(PREFIXES), rng.choice(TYPES), rng.choice(SUFFIXES)]
    else:
        parts = [rng.choice(PREFIXES), rng.choice(ELEMENTS), rng.choice(TYPES), rng.choice(SUFFIXES)]
    return " ".join(parts)


def generate_spell_stats(spell_id: int) -> dict:
    """Deterministically generate stats from spell ID."""
    rng = random.Random(spell_id ^ 0xDEADBEEF)
    damage = rng.randint(8, 80)
    speed  = round(rng.uniform(4.0, 14.0), 1)
    size   = rng.randint(5, 18)

    name  = generate_spell_name(spell_id)
    color = DEFAULT_COLOR
    for kw, col in KEYWORD_COLORS.items():
        if kw in name:
            color = col
            break

    return {"damage": damage, "speed": speed, "size": size, "color": color}


class Spell:
    """Immutable spell object derived from an integer ID."""
    __slots__ = ("id", "name", "damage", "speed", "size", "color")

    def __init__(self, spell_id: int):
        self.id   = spell_id
        self.name = generate_spell_name(spell_id)
        stats     = generate_spell_stats(spell_id)
        self.damage = stats["damage"]
        self.speed  = stats["speed"]
        self.size   = stats["size"]
        self.color  = stats["color"]

    def __repr__(self):
        return f"<Spell {self.name!r} dmg={self.damage}>"


class SpellBook:
    """Tracks discovered spells, hotkey assignments, and presets. Auto-saves."""
    SAVE_FILE = "spellbook_save.json"
    STARTER_IDS = [1, 42, 777]   # guaranteed starting spells

    def __init__(self):
        self.discovered_ids: list[int] = []
        self.hotkeys: list[int | None]  = [None] * 5
        self.presets: dict[str, list]   = {}
        self.active_slot: int           = 0
        self._load()
        if not self.discovered_ids:
            self.discovered_ids = list(self.STARTER_IDS)
            self.hotkeys[0] = self.STARTER_IDS[0]
            self.hotkeys[1] = self.STARTER_IDS[1]
            self._save()

    # ── Discovery ──────────────────────────────────────────────────────────────
    def discover_random(self) -> int | None:
        """Find and store a spell ID the player hasn't seen yet."""
        for _ in range(300):
            sid = random.randint(1, 99_999_999)
            if sid not in self.discovered_ids:
                self.discovered_ids.append(sid)
                self._save()
                return sid
        return None

    # ── Hotkeys ────────────────────────────────────────────────────────────────
    def get_spell(self, spell_id: int | None) -> Spell | None:
        return Spell(spell_id) if spell_id is not None else None

    def get_active_spell(self) -> Spell | None:
        return self.get_spell(self.hotkeys[self.active_slot])

    def assign_to_slot(self, slot: int, spell_id: int):
        if 0 <= slot < 5:
            self.hotkeys[slot] = spell_id
            self._save()

    def clear_slot(self, slot: int):
        if 0 <= slot < 5:
            self.hotkeys[slot] = None
            self._save()

    # ── Presets ────────────────────────────────────────────────────────────────
    def save_preset(self, name: str):
        self.presets[name] = list(self.hotkeys)
        self._save()

    def load_preset(self, name: str):
        if name in self.presets:
            self.hotkeys = list(self.presets[name])
            self._save()

    def delete_preset(self, name: str):
        if name in self.presets:
            del self.presets[name]
            self._save()

    # ── Persistence ────────────────────────────────────────────────────────────
    def _save(self):
        data = {
            "discovered_ids": self.discovered_ids,
            "hotkeys":        self.hotkeys,
            "presets":        self.presets,
        }
        with open(self.SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        if not os.path.exists(self.SAVE_FILE):
            return
        try:
            with open(self.SAVE_FILE) as f:
                data = json.load(f)
            self.discovered_ids = data.get("discovered_ids", [])
            self.hotkeys        = data.get("hotkeys", [None] * 5)
            self.presets        = data.get("presets", {})
        except Exception:
            pass
