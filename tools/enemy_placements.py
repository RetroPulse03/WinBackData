"""Lists the characters each map places, grouped by the zone that spawns them.

Usage: enemy_placements.py rom.z64 [FIRST [LAST]]

Runs the game's own map loader (func_80050750) for each map file and reads the
placement list it leaves at D_801BED70. In Story, the spawner makes a zone's
characters when player 0 enters that zone, so the per-zone counts show how
many slots a zone needs at once. It takes a few seconds per map.
See docs/game-state.md > Players and split screen.
"""
import collections
import struct
import sys

from game_code import Cpu

MAP_FILES = 0x279D00
MAP_NUMBER = 0x8016A4EA
PLACEMENTS = 0x801BED70
PLACEMENT_SIZE = 24
HEALTH_TABLE = 0x80103BB0 - 0x80024C00


def health(rom, entry):
    """Starting health as func_80051E34 sets it, before the difficulty scaling."""
    kind = entry[0xC]
    if entry[0xF] & 0x80:
        return 1
    if kind == 0x29:
        return 127
    return 1 if kind >= 0x2B else rom[HEALTH_TABLE + kind]


def placements(rom, number):
    cpu = Cpu(rom)
    cpu.stubs[0x80052410] = lambda c: c.put(c.r[5], rom[c.r[4]:c.r[4] + c.r[6]])
    cpu.stubs[0x80051014] = lambda c: None  # builds per-entry data that isn't needed here
    cpu.stubs[0x80051248] = lambda c: None
    cpu.w16(MAP_NUMBER, number)
    cpu.call(0x80050750)
    entries = []
    address = PLACEMENTS
    while struct.unpack(">h", cpu.get(address, 2))[0] != -1:
        entries.append(cpu.get(address, PLACEMENT_SIZE))
        address += PLACEMENT_SIZE
    return entries


def main():
    rom = open(sys.argv[1], "rb").read()
    count = struct.unpack_from(">I", rom, MAP_FILES)[0]
    first = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    last = int(sys.argv[3], 0) if len(sys.argv) > 3 else count - 1
    sizes = collections.Counter()
    for number in range(first, last + 1):
        entries = [e for e in placements(rom, number) if health(rom, e) > 0]
        zones = collections.Counter(e[0xA] for e in entries)
        sizes.update(zones.values())
        listing = ", ".join(f"{zone}: {n}" for zone, n in sorted(zones.items()))
        print(f"map {number}: {len(entries)} characters; by zone {listing}", flush=True)
    print("zones by number of characters:", dict(sorted(sizes.items())))


if __name__ == "__main__":
    main()
