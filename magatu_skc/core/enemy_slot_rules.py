"""Rules for stage extension enemy-number selections."""

KEY_ENEMY_FORBIDDEN_CODES = frozenset((
    0x81,  # Blue Burn
    0x83,  # Blue Burn #2
    0x9D,  # Seraphic Radiance
))

FAIRY_FALL_DEATH_ENEMY_CODES = frozenset((
    0x68, 0x69, 0x6C, 0x6D,  # Dragon
    0x70, 0x71, 0x74, 0x75,  # Golem
    0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F,  # Gargoyle
))


def enemy_code_at(level, enemy_number: int):
    enemies = getattr(level, "enemies", []) or []
    enemy_number = int(enemy_number)
    if enemy_number <= 0 or enemy_number > len(enemies):
        return None
    return int(getattr(enemies[enemy_number - 1], "element_no", -1)) & 0xFF


def can_key_enemy_code(enemy_code: int) -> bool:
    enemy_code = int(enemy_code) & 0xFF
    return enemy_code not in KEY_ENEMY_FORBIDDEN_CODES


def can_fairy_enemy_code(enemy_code: int) -> bool:
    return (int(enemy_code) & 0xFF) in FAIRY_FALL_DEATH_ENEMY_CODES


def can_key_enemy_number(level, enemy_number: int, fairy_enemy_number: int = 0) -> bool:
    enemy_number = int(enemy_number)
    if enemy_number <= 0:
        return True
    if fairy_enemy_number > 0 and enemy_number == int(fairy_enemy_number):
        return False
    code = enemy_code_at(level, enemy_number)
    return code is not None and can_key_enemy_code(code)


def can_fairy_enemy_number(level, enemy_number: int, key_enemy_number: int = 0) -> bool:
    enemy_number = int(enemy_number)
    if enemy_number <= 0:
        return True
    if key_enemy_number > 0 and enemy_number == int(key_enemy_number):
        return False
    code = enemy_code_at(level, enemy_number)
    return code is not None and can_fairy_enemy_code(code)


def coerce_enemy_number(level, requested: int, current: int, predicate) -> int | None:
    requested = int(requested)
    current = int(current)
    enemies = getattr(level, "enemies", []) or []
    max_enemy = len(enemies)
    if requested <= 0:
        return 0
    if requested > max_enemy:
        return None
    if predicate(requested):
        return requested

    direction = 1 if requested > current else -1
    for n in range(requested + direction, max_enemy + 1 if direction > 0 else 0, direction):
        if predicate(n):
            return n
    for n in range(requested - direction, max_enemy + 1 if direction < 0 else 0, -direction):
        if predicate(n):
            return n
    return None
