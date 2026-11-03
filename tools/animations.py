#!/usr/bin/env python3
"""Reads the game's character animations from your ROM and finds the unused ones.

Usage: animations.py rom.z64 list              every clip's length, skeleton and ROM offset
       animations.py rom.z64 unused            clips that no code, table or script names
       animations.py rom.z64 sheet out.png ID...   each clip as a strip of stick figures
       animations.py rom.z64 viewer [out.html] a page playing every clip, with filters

The format and how "unused" is decided are in docs/animations.md. The sheet and the
viewer are made from the ROM, so they must never be committed or shared.
"""
import json
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import event_scripts
from game_code import Cpu

CLIP_COUNT = 2387
ASSET_FILE = 0xF87B0
HEADERS = ASSET_FILE + 0xA8D0
OFFSETS = ASSET_FILE + 0xCE1C
CLIP_DATA = 0x53F990
MAIN_ROM_TO_VRAM = 0x80024C00
KEY_SCALE = 0.1
TANGENT_SCALE = 1 / 30
TRACKS = 60

ROOT_POSITION = 3
UPPER_ROOT_POSITION = 33
LEFT_HAND = 48
RIGHT_HAND = 57

OP_ANIMATE = 2
OP_MOVE_AND_ANIMATE = 36

# Ids the code writes to obj+0x16E0 and obj+0x16E2 as constants, found by tracing every
# store to those two fields back to where its value comes from.
CODE_IDS = {
    2, 140, 1013, 1049, 1052, 1053, 1070, 1072, 1074, 1076, 1078, 1079, 1081, 1089, 1092, 1095, 1096, 1097, 1099,
    1104, 1105, 1106, 1107, 1108, 1109, 1110, 1111, 1115, 1116, 1119, 1121, 1122, 1123, 1125, 1131, 1137, 1138, 1147,
    1148, 1150, 1151, 1152, 1171, 1179, 1185, 1189, 1197, 1198, 1199, 1200, 1201, 1202, 1203, 1204, 1207, 1210, 1211,
    1217, 1218, 1239, 1243, 1245, 1249, 1254, 1255, 1256, 1257, 1258, 1259, 1260, 1261, 1267, 1268, 1277, 1278, 1280,
    1281, 1282, 1291, 1299, 1308, 1316, 1322, 1328, 1329, 1330, 1331, 1332, 1333, 1334, 1337, 1338, 1607, 1608, 1613,
    1623, 1624, 1626, 1627, 1628, 1632, 1642, 1643, 1645, 1646, 1647, 1676, 1680, 1682, 1690, 1693, 1694, 1697, 1698,
    1699, 1701, 1728, 1731, 1736, 1745, 1746, 1763, 1767, 1769, 1772, 1811, 1812, 1817, 1821, 1823, 1824, 1827, 1834,
    2077, 2080, 2082, 2084, 2085, 2086, 2087, 2088, 2095, 2097, 2102, 2103, 2104, 2105, 2109, 2110, 2111, 2112, 2115,
    2120, 2123, 2124, 2134, 2138, 2141, 2144, 2149, 2150, 2161, 2162, 2168, 2170, 2185, 2189, 2191, 2195, 2196, 2197,
    2198, 2199, 2200, 2202, 2207, 2208, 2211, 2215, 2219, 2223, 2226, 2233, 2234, 2242, 2316, 2325, 2326, 2331, 2335,
    2337, 2338, 2341, 2352, 2354, 2359, 2361, 2362, 2363, 2364, 2378, 2379, 2380, 2387,
}
# The tables those stores read from, as (first address, end address).
ID_TABLES = [
    (0x80103BDC, 0x80103BF2), (0x80105430, 0x80105A5A), (0x80105AD0, 0x80105B14), (0x80105B3C, 0x80105B84),
    (0x8010C408, 0x8010C42C), (0x801103E0, 0x80110478), (0x801128F8, 0x801129D0),
]

# Body parts joined by lines, with the head's tip and both hands added as 15, 16 and 17.
BONES = [(0, 1, 0), (1, 2, 0), (2, 3, 0), (0, 4, 1), (4, 5, 1), (5, 6, 1), (0, 8, 2), (8, 15, 2),
         (7, 9, 3), (9, 10, 3), (10, 16, 3), (7, 12, 4), (12, 13, 4), (13, 17, 4)]
HEAD_LENGTH = 22
OBJECT = 0x80300000
COLOURS = [(255, 120, 80), (90, 170, 255), (240, 240, 240), (255, 200, 60), (120, 230, 120)]


def u16(rom, offset):
    return struct.unpack_from(">H", rom, offset)[0]


def u32(rom, offset):
    return struct.unpack_from(">I", rom, offset)[0]


def header(rom, clip):
    """Gives a clip's (frames, skeleton type, sound or effect events)."""
    word = u32(rom, ASSET_FILE + (u32(rom, HEADERS + (clip - 1) * 4) & 0xFFFFFF))
    return word & 0xFFFF, word >> 30, word >> 16 & 0x3FFF


def clip_offset(rom, clip):
    return CLIP_DATA + u32(rom, OFFSETS + (clip - 1) * 4)


def read_key(rom, offset):
    """Gives a key's (time, value, tangent in, tangent out) and its length in bytes."""
    word = u32(rom, offset)
    flags = word >> 16
    value = (word & 0x3FFF) * KEY_SCALE ** ((word >> 14 & 3) + 1)
    if flags & 0x2000:
        value = -value
    if flags & 0x8000:
        return (flags & 0x1FFF, value, *struct.unpack_from(">2f", rom, offset + 4)), 12
    if flags & 0x4000:
        return (flags & 0x1FFF, value, 0.0, 0.0), 4
    tangent = struct.unpack_from(">f", rom, offset + 4)[0]
    return (flags & 0x1FFF, value, tangent, tangent), 8


def read_tracks(rom, clip):
    base = clip_offset(rom, clip)
    tracks = []
    for track in range(TRACKS):
        offset = base + u16(rom, base + track * 2)
        keys = []
        for _ in range(rom[base + 0x78 + track]):
            key, size = read_key(rom, offset)
            keys.append(key)
            offset += size
        tracks.append(keys)
    return tracks


def evaluate(keys, time):
    """The same Hermite curve as func_80057FB4."""
    if not keys:
        return 0.0
    if time <= keys[0][0]:
        return keys[0][1]
    for previous, following in zip(keys, keys[1:]):
        if time <= following[0]:
            span = following[0] - previous[0]
            if span <= 0:
                return following[1]
            s = (time - previous[0]) / span
            s2, s3 = s * s, s * s * s
            return ((2 * s3 - 3 * s2 + 1) * previous[1] + (3 * s2 - 2 * s3) * following[1]
                    + ((s3 - 2 * s2 + s) * previous[3] + (s3 - s2) * following[2]) * span * TANGENT_SCALE)
    return keys[-1][1]


class Poser:
    """Runs the game's own skeleton code on a clip's values."""

    def __init__(self, rom):
        self.cpu = Cpu(rom)
        self.cpu.stubs[0x80052410] = lambda cpu: None

    def pose(self, values, skeleton):
        cpu = self.cpu
        cpu.put(OBJECT, bytes(0x2000))
        cpu.w8(OBJECT + 0x175A, skeleton)
        cpu.w32(0x801044F0, 0)
        cpu.put(OBJECT + 0xD28, struct.pack(">60f", *values))
        cpu.put(OBJECT + 0xE18, struct.pack(">30f", *values[:30]))
        cpu.call(0x80068324, OBJECT)
        cpu.call(0x80069D44, OBJECT)
        root = values[ROOT_POSITION:ROOT_POSITION + 3]
        upper = values[UPPER_ROOT_POSITION:UPPER_ROOT_POSITION + 3]
        points = []
        for part in range(15):
            position = struct.unpack(">3f", cpu.get(OBJECT + 0x13F8 + part * 0x30 + 36, 12))
            points.append([position[i] + root[i] for i in range(3)])
        points.append([points[8][0], points[8][1] + HEAD_LENGTH, points[8][2]])
        for hand in (LEFT_HAND, RIGHT_HAND):
            points.append([values[hand + i] - upper[i] + root[i] for i in range(3)])
        return points


def clip_poses(rom, poser, clip, count):
    frames, skeleton, _ = header(rom, clip)
    tracks = read_tracks(rom, clip)
    poses = []
    for step in range(count):
        time = frames * step / (count - 1)
        poses.append(poser.pose([evaluate(keys, time) for keys in tracks], skeleton))
    return poses


def named_ids(rom):
    """Every clip id that code, a table or an event script names, and which of them did."""
    named = {clip: {"code"} for clip in CODE_IDS}
    for first, end in ID_TABLES:
        for address in range(first, end, 2):
            value = u16(rom, address - MAIN_ROM_TO_VRAM)
            if 1 <= value <= CLIP_COUNT:
                named.setdefault(value, set()).add("table")
    for _, event in event_scripts.all_events(rom):
        for opcode, arguments in event[2]:
            value = None
            if opcode == OP_ANIMATE:
                value = arguments[1]
            elif opcode == OP_MOVE_AND_ANIMATE:
                value = arguments[4]
            if value and 1 <= value <= CLIP_COUNT:
                named.setdefault(value, set()).add("script")
    return named


def describe_motion(poses):
    """A rough label for a clip from how its figure moves. These are guesses, not game data."""
    hips = [pose[0][1] for pose in poses]
    head = [pose[15][1] for pose in poses]
    feet = [min(pose[3][1], pose[6][1]) for pose in poses]
    if min(hips) < -30:
        return "long drop"
    if any(h < hip - 5 for h, hip in zip(head, hips)) and hips[-1] > 40:
        return "flip or roll"
    if hips[0] > 50 and hips[-1] < 35:
        return "falls down"
    if hips[0] < 35 and hips[-1] > 50:
        return "gets up"
    if max(hips) < 35:
        return "lying down"
    if max(feet) > 30:
        return "leaves the ground"
    if max(hips) - min(hips) > 25:
        return "crouches or rises"
    return "standing"


class Image:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.pixels = bytearray([20, 22, 28] * (width * height))

    def line(self, x0, y0, x1, y1, colour):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for step in range(steps + 1):
            x = int(x0 + (x1 - x0) * step / steps)
            y = int(y0 + (y1 - y0) * step / steps)
            for px, py in ((x, y), (x + 1, y), (x, y + 1)):
                if 0 <= px < self.width and 0 <= py < self.height:
                    self.pixels[(py * self.width + px) * 3:(py * self.width + px) * 3 + 3] = bytes(colour)

    def save(self, path):
        stride = self.width * 3
        raw = b"".join(b"\0" + bytes(self.pixels[y * stride:(y + 1) * stride]) for y in range(self.height))

        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

        size = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        with open(path, "wb") as file:
            file.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", size) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def sheet(rom, path, clips):
    """One row per clip, in the order given, each with eight evenly spaced poses."""
    cell_width, cell_height, count, scale = 118, 170, 8, 0.62
    image = Image(cell_width * count, cell_height * len(clips))
    poser = Poser(rom)
    for row, clip in enumerate(clips):
        poses = clip_poses(rom, poser, clip, count)
        start = poses[0][0][2]
        for column, pose in enumerate(poses):
            middle = column * cell_width + cell_width // 2
            ground = (row + 1) * cell_height - 8
            image.line(middle - 40, ground, middle + 40, ground, (70, 70, 80))
            for a, b, colour in BONES:
                image.line(middle + (pose[a][2] - start + pose[a][0] * 0.45) * scale, ground - pose[a][1] * scale,
                           middle + (pose[b][2] - start + pose[b][0] * 0.45) * scale, ground - pose[b][1] * scale,
                           COLOURS[colour])
    image.save(path)


def viewer(rom, path):
    named = named_ids(rom)
    poser = Poser(rom)
    clips = []
    for clip in range(1, CLIP_COUNT + 1):
        frames, skeleton, events = header(rom, clip)
        poses = clip_poses(rom, poser, clip, min(frames + 1, 16))
        flat = [[round(value) for point in pose for value in point] for pose in poses]
        clips.append(dict(i=clip, f=frames, k=skeleton, e=events, n=sorted(named.get(clip, [])),
                          m=describe_motion(poses), p=flat))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "animation_viewer.html"), encoding="utf-8") as file:
        page = file.read()
    with open(path, "w", encoding="utf-8") as file:
        file.write(page.replace("/*CLIPS*/null", json.dumps(clips, separators=(",", ":")))
                   .replace("/*BONES*/null", json.dumps(BONES, separators=(",", ":"))))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    with open(sys.argv[1], "rb") as file:
        rom = file.read()
    event_scripts.rom_data = rom
    command = sys.argv[2]
    if command == "list":
        for clip in range(1, CLIP_COUNT + 1):
            frames, skeleton, events = header(rom, clip)
            print(f"{clip} frames={frames} skeleton={skeleton} events={events} rom={clip_offset(rom, clip):#x}")
    elif command == "unused":
        named = named_ids(rom)
        print(" ".join(str(clip) for clip in range(1, CLIP_COUNT + 1) if clip not in named))
    elif command == "sheet":
        sheet(rom, sys.argv[3], [int(value) for value in sys.argv[4:]])
    elif command == "viewer":
        path = sys.argv[3] if len(sys.argv) > 3 else "output/animations.html"
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        viewer(rom, path)


if __name__ == "__main__":
    main()
