#!/usr/bin/env python3
"""Unpack WinBack's character models from your ROM so they can be studied.

For each of the 62 model ids this writes, under the output folder:
  idNN.dl.bin / idNN.vtx.bin / idNN.tex.bin   the three unpacked files
  idNN.png                                    a sheet of the model's textures
and characters.txt, listing ROM offsets, sizes, part lists and triangle counts.

The format is described in docs/characters.md. Everything written here comes
from the ROM, so it must never be committed or shared.

Usage: python tools/extract_characters.py <rom> [out_dir]
"""
import os
import struct
import sys
import zlib

MAIN_TO_VRAM = 0x80024C00
MODEL_COUNT = 62
DL_TABLE = 0x80104C20
VTX_TABLE = 0x80104E10
TEX_TABLE = 0x80105000
MODEL_INFO = 0x80109540
JEAN_LUC = 0x22
SHEET_WIDTH = 512
MISSING = [255, 0, 255, 255]


def unpack(rom, start):
    """LZ decoder matching func_80071FE0."""
    window = bytearray(0x4000)
    pos = 1
    out = bytearray()
    src = start
    mask = 0x80
    cur = 0

    def bits(count):
        nonlocal src, mask, cur
        value = 0
        for _ in range(count):
            if mask == 0x80:
                cur = rom[src]
                src += 1
            value = (value << 1) | (1 if cur & mask else 0)
            mask = mask >> 1 or 0x80
        return value

    while True:
        if bits(1):
            byte = bits(8)
            out.append(byte)
            window[pos] = byte
            pos = (pos + 1) & 0x3FFF
        else:
            offset = bits(14)
            if offset == 0:
                return bytes(out)
            for i in range(bits(4) + 3):
                byte = window[(offset + i) & 0x3FFF]
                out.append(byte)
                window[pos] = byte
                pos = (pos + 1) & 0x3FFF


def read_u32(rom, vram):
    return struct.unpack(">I", rom[vram - MAIN_TO_VRAM:vram - MAIN_TO_VRAM + 4])[0]


def table_entry(rom, table, index):
    return read_u32(rom, table + index * 8), read_u32(rom, table + index * 8 + 4)


def commands(dl, start=0):
    for offset in range(start, len(dl) - 7, 8):
        yield offset, *struct.unpack(">II", dl[offset:offset + 8])


def find_textures(dl):
    """Walk the display list; return {(image, fmt, siz, w, h): palette} as bound at each G_VTX."""
    found = {}
    timg = image = palette = fmt = siz = current = None
    for _, w0, w1 in commands(dl):
        op = w0 >> 24
        if op == 0xFD:
            timg = w1
        elif op in (0xF3, 0xF4):
            image = timg
        elif op == 0xF0:
            palette = timg
        elif op == 0xF5 and (w1 >> 24) & 7 == 0:
            fmt, siz = (w0 >> 21) & 7, (w0 >> 19) & 3
        elif op == 0xF2 and (w1 >> 24) & 7 == 0:
            current = (image, fmt, siz, ((w1 >> 12) & 0xFFF) // 4 + 1, (w1 & 0xFFF) // 4 + 1)
        elif op == 0x01 and current:
            found.setdefault(current, palette if current[1] == 2 else None)
    return found


def rgba5551(value):
    return [(value >> 11 & 31) * 255 // 31, (value >> 6 & 31) * 255 // 31,
            (value >> 1 & 31) * 255 // 31, 255 if value & 1 else 0]


def resolve(address, own, shared):
    """Segment 9 is the model's own file, segment A Jean-Luc's. Anything else isn't decoded yet."""
    return {9: own, 0xA: shared}.get(address >> 24), address & 0xFFFFFF


def decode(key, palette_addr, own, shared):
    image, fmt, siz, width, height = key
    data, offset = resolve(image, own, shared)
    if data is None:
        return width, height, MISSING * (width * height)

    palette = None
    if palette_addr is not None:
        pal_data, pal_offset = resolve(palette_addr, own, shared)
        if pal_data is not None:
            palette = [rgba5551(struct.unpack(">H", pal_data[pal_offset + i * 2:pal_offset + i * 2 + 2])[0])
                       if pal_offset + i * 2 + 2 <= len(pal_data) else MISSING
                       for i in range(16 if siz == 0 else 256)]

    bpp = (4, 8, 16, 32)[siz]
    stride = (width * bpp + 7) // 8
    pixels = []
    for y in range(height):
        for x in range(width):
            i = offset + y * stride + (x * bpp >> 3)
            if i + (bpp // 8) > len(data) or i >= len(data):
                pixels += MISSING
                continue
            byte = data[i]
            value = byte if bpp != 4 else (byte >> 4 if x % 2 == 0 else byte & 15)
            if fmt == 2 and palette:  # CI
                pixels += palette[value]
            elif fmt == 4:  # I
                grey = value * 17 if bpp == 4 else value
                pixels += [grey, grey, grey, 255]
            elif fmt == 3 and bpp == 4:  # IA4
                pixels += [(value >> 1) * 36] * 3 + [255 if value & 1 else 0]
            elif fmt == 3 and bpp == 8:  # IA8
                pixels += [(value >> 4) * 17] * 3 + [(value & 15) * 17]
            elif fmt == 3 and bpp == 16:  # IA16
                pixels += [value] * 3 + [data[i + 1]]
            elif fmt == 0 and bpp == 16:  # RGBA16
                pixels += rgba5551(byte << 8 | data[i + 1])
            else:
                pixels += MISSING
    return width, height, pixels


def write_png(path, width, height, rgba):
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    raw = b"".join(b"\0" + bytes(rgba[y * width * 4:(y + 1) * width * 4]) for y in range(height))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def write_sheet(path, images):
    x = y = row = 0
    placed = []
    for width, height, pixels in images:
        if x + width > SHEET_WIDTH:
            x, y, row = 0, y + row + 2, 0
        placed.append((x, y, width, height, pixels))
        x += width + 2
        row = max(row, height)
    total = y + row + 1
    sheet = bytearray([40, 40, 40, 255]) * (SHEET_WIDTH * total)
    for px, py, width, height, pixels in placed:
        for line in range(height):
            start = ((py + line) * SHEET_WIDTH + px) * 4
            sheet[start:start + width * 4] = bytes(pixels[line * width * 4:(line + 1) * width * 4])
    write_png(path, SHEET_WIDTH, total, sheet)


def triangles(dl, offset):
    count = 0
    for _, w0, _ in commands(dl, offset):
        count += {0x05: 1, 0x06: 2}.get(w0 >> 24, 0)
        if w0 >> 24 == 0xDF:
            return count
    return count


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rom_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "output/characters"
    os.makedirs(out_dir, exist_ok=True)
    with open(rom_path, "rb") as f:
        rom = f.read()

    shared = unpack(rom, table_entry(rom, TEX_TABLE, JEAN_LUC)[0])
    report = ["id  type  dl_rom    vtx_rom   tex_rom   tex_size  tris near/mid/far"]
    missing_total = 0
    for model in range(MODEL_COUNT):
        dl_start, dl_end = table_entry(rom, DL_TABLE, model)
        vtx_start = table_entry(rom, VTX_TABLE, model)[0]
        tex_start = table_entry(rom, TEX_TABLE, model)[0]
        dl = rom[dl_start:dl_end]
        vtx = unpack(rom, vtx_start)
        tex = unpack(rom, tex_start)
        for suffix, blob in (("dl", dl), ("vtx", vtx), ("tex", tex)):
            with open(os.path.join(out_dir, f"id{model:02d}.{suffix}.bin"), "wb") as f:
                f.write(blob)

        images = [decode(key, palette, tex, shared) for key, palette in sorted(find_textures(dl).items())]
        missing_total += sum(1 for _, _, p in images if p[:4] == MISSING)
        write_sheet(os.path.join(out_dir, f"id{model:02d}.png"), images)

        info = read_u32(rom, MODEL_INFO + model * 4)
        lists = [read_u32(rom, info + 4 * n) for n in (1, 2, 3)]
        tris = [sum(triangles(dl, read_u32(rom, part + 4 * n) & 0xFFFFFF) for n in range(15)) for part in lists]
        report.append(f"{model:2d}  {read_u32(rom, info):4d}  {dl_start:08X}  {vtx_start:08X}  {tex_start:08X}"
                      f"  {len(tex):8X}  {tris[0]}/{tris[1]}/{tris[2]}")

    with open(os.path.join(out_dir, "characters.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print(f"Wrote {MODEL_COUNT} models to {out_dir} ({missing_total} textures not decoded, shown magenta)")


if __name__ == "__main__":
    main()
