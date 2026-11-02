#!/usr/bin/env python3
"""Build a 3D viewer for WinBack's characters from your ROM.

This writes one HTML file holding every model's near detail level, split into
its 15 body parts and the joints between them, with textures. Open it in a browser
to look at the models and to mix parts from different characters. The format is
described in docs/characters.md. The file is made from the ROM, so it must never be committed
or shared.

Usage: python tools/character_viewer.py <rom> [output.html]
"""
import base64
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_characters import (DL_TABLE, JEAN_LUC, MODEL_COUNT, MODEL_INFO, TEX_TABLE, VTX_TABLE, decode, read_u32,
                                table_entry, unpack)
from game_code import Cpu

# func_8006A508 picks one of these by obj+0x175A. Each holds 30 floats.
SKELETON_TABLES = {0: 0x80107490, 2: 0x80107508, 1: 0x80107580}

# Combiners used by character display lists.
COMBINE_TEXTURE = 0xFC127FFF  # texture x light
COMBINE_TINT = 0xFC11FE04     # texture x primitive colour x light
COMBINE_COLOUR = 0xFC3239FF   # primitive colour x light
COMBINER_KIND = {COMBINE_TEXTURE: 0, COMBINE_TINT: 1, COMBINE_COLOUR: 2}

# Joints exist for models from Jean-Luc up. See docs/characters.md (Joints).
FIRST_JOINTED_MODEL = 0x22
LAST_JOINTED_MODEL = 0x3A  # the game's joint tables end here, so later models borrow this one's
# Model 60 keeps some of those joints' images and palettes elsewhere in its texture file.
BORROWED_IMAGE_MOVES = {60: {0x90038E0: 0x9001EE0, 0x9003CE0: 0x90022E0, 0x9003EE0: 0x90024E0, 0x90040E0: 0x90026E0}}
ASSET_FILE_ROM = 0xF87B0
ASSET_FILE_VRAM = 0x80229A00
ASSET_FILE_SIZE = 0x33000
JOINT_SLOTS = 0x801CC710
OBJECT = 0x80600000
JOINT_DL = 0x80700000
# Which part decides a joint's look when mixing, by its vertices in the slot.
JOINT_OWNERS = {0x208: 4, 0x308: 1, 0x008: 5, 0x108: 2, 0x608: 0, 0x408: 13, 0x508: 10}

# Rotations (three axes) of each kind of part in the rest pose. +Z of the world is
# the way the character faces, +Y is up.
LIMB = ((0, -1, 0), (0, 0, 1), (-1, 0, 0))
ARM = ((0, -1, 0), (0, 0, -1), (1, 0, 0))
TORSO = ((0, 1, 0), (0, 0, 1), (1, 0, 0))
HEAD = ((0, 0, 1), (0, 1, 0), (-1, 0, 0))
# A forearm turns about the elbow towards the upper arm's -Y. Fully straight arms leave slits in the elbow joints.
ELBOW_BEND = math.radians(15)
BENT_ARM = ((0, -math.cos(ELBOW_BEND), math.sin(ELBOW_BEND)), (0, -math.sin(ELBOW_BEND), -math.cos(ELBOW_BEND)), (1, 0, 0))


def signed8(value):
    return value - 256 if value > 127 else value


class Part:
    """Walks one part's display list into triangles grouped by material."""

    def __init__(self, dl, vtx, offset, asset_file=0):
        self.dl = dl
        self.vtx = vtx
        self.asset_file = asset_file
        self.group = None
        self.batches = {}
        self.tile = None
        self.size = (0, 0, 0, 0)
        self.key = None
        self.timg = self.image = self.palette = 0
        self.combiner = COMBINE_TEXTURE
        self.prim = 0xFFFFFFFF
        self.double_sided = False
        self.textured_without_image = False
        self.buffer = [None] * 32
        self.walk(offset)

    def walk(self, offset):
        dl, vtx, buffer = self.dl, self.vtx, self.buffer
        while True:
            w0, w1 = struct.unpack(">II", dl[offset:offset + 8])
            offset += 8
            op = w0 >> 24
            if op == 0x01:  # G_VTX
                count = (w0 >> 12) & 0xFF
                end = (w0 >> 1) & 0x7F
                base = w1 & 0xFFFFFF
                self.group = base
                for i in range(count):
                    buffer[end - count + i] = struct.unpack(">3hHhh3bB", vtx[base + i * 16:base + i * 16 + 16])
            elif op == 0xDE:  # G_DL, only found in the joints' lists, into segment 2
                self.walk(self.asset_file + (w1 & 0xFFFFFF))
                if (w0 >> 16) & 0xFF:
                    return
            elif op == 0x05:  # G_TRI1
                self.triangle(buffer, w0)
            elif op == 0x06:  # G_TRI2
                self.triangle(buffer, w0)
                self.triangle(buffer, w1)
            elif op == 0xD9:  # G_GEOMETRYMODE
                if not w0 & 0x400:
                    self.double_sided = True
                if w1 & 0x400:
                    self.double_sided = False
            elif op == 0xFA:  # G_SETPRIMCOLOR
                self.prim = w1
            elif op == 0xFC:  # G_SETCOMBINE
                self.combiner = w0
            elif op == 0xFD:  # G_SETTIMG
                self.timg = w1
            elif op in (0xF3, 0xF4):  # G_LOADBLOCK, G_LOADTILE
                self.image = self.timg
            elif op == 0xF0:  # G_LOADTLUT
                self.palette = self.timg
            elif op == 0xF5 and (w1 >> 24) & 7 == 0:  # G_SETTILE
                self.tile = dict(fmt=(w0 >> 21) & 7, siz=(w0 >> 19) & 3,
                                 cmt=(w1 >> 18) & 3, maskt=(w1 >> 14) & 15, shiftt=(w1 >> 10) & 15,
                                 cms=(w1 >> 8) & 3, masks=(w1 >> 4) & 15, shifts=w1 & 15)
            elif op == 0xF2 and (w1 >> 24) & 7 == 0:  # G_SETTILESIZE
                self.size = ((w0 >> 12) & 0xFFF, w0 & 0xFFF, (w1 >> 12) & 0xFFF, w1 & 0xFFF)
            elif op == 0xDF:  # G_ENDDL
                return

    def triangle(self, buffer, word):
        tile = self.tile
        textured = self.combiner != COMBINE_COLOUR
        if textured and tile is None:
            self.textured_without_image = True
            return
        material = (self.combiner, self.prim if self.combiner != COMBINE_TEXTURE else 0xFFFFFFFF, self.double_sided)
        if textured:
            width = self.size[2] // 4 + 1
            height = self.size[3] // 4 + 1
            material += (self.image, self.palette if tile["fmt"] == 2 else None, tile["fmt"], tile["siz"], width, height,
                         tile["cms"], tile["masks"], tile["cmt"], tile["maskt"])
        batch = self.batches.setdefault((self.group, material), [])
        for shift in (16, 8, 0):
            x, y, z, _, s, t, nx, ny, nz, _ = buffer[((word >> shift) & 0xFF) // 2]
            # S10.5 coordinates, at the 0.5 scale the game draws characters with (inferred: all parts span 0-2).
            s, t = s / 64.0, t / 64.0
            if textured:
                s = s * 2.0 ** -tile["shifts"] - self.size[0] / 4.0
                t = t * 2.0 ** -tile["shiftt"] - self.size[1] / 4.0
                s, t = s / width, t / height
            batch += [x, y, z, nx / 127.0, ny / 127.0, nz / 127.0, round(s, 4), round(t, 4)]


def wrap_mode(mode, mask):
    if mask == 0:
        return 0  # clamp
    return 2 if mode & 1 else 1  # mirror, repeat


def rest_pose(rom, kind):
    """Each part's (rotation, position) when standing straight with its arms down."""
    start = SKELETON_TABLES[kind] - 0x80024C00
    s = struct.unpack(">30f", rom[start:start + 120])

    def add(p, r, x, y, z):
        return [p[k] + r[0][k] * x + r[1][k] * y + r[2][k] * z for k in range(3)]

    hips = [0, s[2] + s[4] + s[6] + 10, 0]
    pose = [None] * 15
    pose[0] = (LIMB, hips)

    def limb(first, parent, upper, lower, entry):
        p = add(hips, parent, s[entry], 0, s[entry + 1])
        pose[first] = (upper, p)
        p = add(p, upper, s[entry + 2], 0, 0)
        pose[first + 1] = (lower, p)
        pose[first + 2] = (lower, add(p, lower, s[entry + 4], 0, 0))

    limb(1, LIMB, LIMB, LIMB, 2)
    limb(4, LIMB, LIMB, LIMB, 8)
    pose[7] = (TORSO, hips)
    pose[8] = (HEAD, add(hips, TORSO, s[16], 0, 0))
    limb(9, TORSO, ARM, BENT_ARM, 18)
    limb(12, TORSO, ARM, BENT_ARM, 24)
    return pose


def joint_batches(rom, model, kind):
    """Runs the game's joint code for a model in the rest pose. Returns a Part of its triangles."""
    cpu = Cpu(rom)
    cpu.put(ASSET_FILE_VRAM, rom[ASSET_FILE_ROM:ASSET_FILE_ROM + ASSET_FILE_SIZE])

    def load_raw(c):
        c.put(c.r[5], rom[c.r[4]:c.r[4] + c.r[6]])

    cpu.stubs[0x80052410] = load_raw
    cpu.w32(0x801D2C80, JOINT_DL)  # display list pointer
    cpu.w32(0x801B0D20, 0x0A000000)  # slot 0's textures, shown as segment A
    cpu.w8(OBJECT + 0x16F5, model)
    cpu.w8(OBJECT + 0x175A, kind)
    cpu.w8(OBJECT + 0x1768, 1)
    cpu.w32(OBJECT + 0x1890, 0x09000000)
    pose = rest_pose(rom, kind)
    cpu.put(OBJECT + 0x13C8, struct.pack(">12f", 1, 0, 0, 0, 1, 0, 0, 0, 1, *pose[0][1]))  # the whole object, for the waist's normals
    for index, (r, p) in enumerate(pose):
        cpu.put(OBJECT + 0x13F8 + index * 0x30, struct.pack(">12f", *r[0], *r[1], *r[2], *p))
    cpu.call(0x8006B3B8, OBJECT)  # claims a joint slot and loads the model's vertex template
    cpu.call(0x8006B564, OBJECT)  # places the joints from the part matrices
    cpu.call(0x8006C68C, OBJECT)  # draws hips and knees
    cpu.call(0x8006EF90, OBJECT)  # draws waist and elbows
    cpu.w32(cpu.u32(0x801D2C80), 0xDF000000)
    return Part(cpu.ram, cpu.ram, JOINT_DL & 0xFFFFFF, ASSET_FILE_VRAM & 0xFFFFFF)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_path = sys.argv[2] if len(sys.argv) > 2 else "output/characters/viewer.html"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(sys.argv[1], "rb") as f:
        rom = f.read()

    shared = unpack(rom, table_entry(rom, TEX_TABLE, JEAN_LUC)[0])
    textures = {}
    texture_list = []

    def texture(material, own):
        image, palette, fmt, siz, width, height = material[3:9]
        width, height, pixels = decode((image, fmt, siz, width, height), palette, own, shared)
        data = bytes(pixels)
        if data not in textures:
            textures[data] = len(texture_list)
            texture_list.append(dict(w=width, h=height, d=base64.b64encode(data).decode()))
        return textures[data]

    def batch_entry(material, data, own):
        kind = COMBINER_KIND.get(material[0], 0)
        prim = material[1]
        entry = dict(k=kind, c=[prim >> 24, prim >> 16 & 255, prim >> 8 & 255], ds=material[2], v=data)
        if kind != 2:
            entry["t"] = texture(material, own)
            entry["ws"] = wrap_mode(material[9], material[10])
            entry["wt"] = wrap_mode(material[11], material[12])
        return entry

    poses = {kind: [dict(r=r, p=p) for r, p in rest_pose(rom, kind)] for kind in SKELETON_TABLES}
    models = []
    seen = {}
    for model in range(MODEL_COUNT):
        dl_range = table_entry(rom, DL_TABLE, model)
        if dl_range in seen:
            models.append(dict(alias=seen[dl_range]))
            continue
        seen[dl_range] = model
        dl = rom[dl_range[0]:dl_range[1]]
        vtx = unpack(rom, table_entry(rom, VTX_TABLE, model)[0])
        own = unpack(rom, table_entry(rom, TEX_TABLE, model)[0])
        info = read_u32(rom, MODEL_INFO + model * 4)
        near = read_u32(rom, info + 4)
        parts = []
        for index in range(15):
            address = read_u32(rom, near + index * 4)
            batches = []
            triangles = 0
            walk = Part(dl, vtx, address & 0xFFFFFF)
            for (_, material), data in walk.batches.items():
                batches.append(batch_entry(material, data, own))
                triangles += len(data) // 24
            parts.append(dict(b=batches, n=triangles))
        kind = read_u32(rom, info)
        joints = {}
        if model >= FIRST_JOINTED_MODEL:
            source = min(model, LAST_JOINTED_MODEL)
            moves = BORROWED_IMAGE_MOVES.get(model, {})
            for (group, material), data in joint_batches(rom, source, kind).batches.items():
                material = tuple(moves.get(value, value) if index in (3, 4) else value for index, value in enumerate(material))
                owner = JOINT_OWNERS[group - (JOINT_SLOTS & 0xFFFFFF)]
                joint = joints.setdefault(owner, dict(owner=owner, b=[], n=0))
                joint["b"].append(batch_entry(material, data, own))
                joint["n"] += len(data) // 24
        models.append(dict(type=kind, parts=parts, joints=list(joints.values())))
        if model > LAST_JOINTED_MODEL:
            models[-1]["jointsFrom"] = LAST_JOINTED_MODEL

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "character_viewer.html"), encoding="utf-8") as f:
        template = f.read()
    data = json.dumps(dict(models=models, textures=texture_list, poses=poses), separators=(",", ":"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(template.replace("/*DATA*/null", data))
    print(f"Wrote {out_path} ({len(texture_list)} textures, {os.path.getsize(out_path) // 1024} KB)")


if __name__ == "__main__":
    main()
