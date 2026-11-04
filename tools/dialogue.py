"""Lists the game's dialogue from your ROM and checks how each line wraps.

Usage: dialogue.py rom.z64 [find replace]

With a name to find and its replacement, shows only the lines containing it,
with the number of lines each takes in its text box before and after. See
docs/text.md for the formats.
"""
import struct
import sys

ARCHIVE = 0x9264B0
MAIN_ROM_TO_VRAM = 0x80024C00
GLYPHS = 0x8010AE30 - MAIN_ROM_TO_VRAM
SYMBOLS = 0x8010B01C - MAIN_ROM_TO_VRAM
BOX_WIDTH = 0x112
BOX_LINES = 3


def files(rom):
    count = struct.unpack_from(">I", rom, ARCHIVE)[0]
    offsets = struct.unpack_from(f">{count + 1}I", rom, ARCHIVE + 4)
    for i in range(count):
        yield i, rom[ARCHIVE + offsets[i]:ARCHIVE + offsets[i + 1]]


def lines(data):
    """Each line is a speaker byte, then text ending in a zero."""
    count = struct.unpack_from(">H", data, 0)[0]
    for offset in struct.unpack_from(f">{count}H", data, 2):
        end = data.index(0, offset + 1)
        yield data[offset], data[offset + 1:end]


def glyph(rom, c):
    """func_8007C0E0: which entry of the glyph table draws a character."""
    if 0x41 <= c <= 0x5A:
        return c - 0x41
    if 0x30 <= c <= 0x39:
        return c - 0x16
    i = 0
    while rom[SYMBOLS + i]:
        if rom[SYMBOLS + i] == c:
            return i + 0x24
        i += 1
    return -1


def char_width(rom, c, following):
    """func_8007C1F4: the kerning depends on the next character."""
    if c == 0x20:
        return 4
    i = glyph(rom, c)
    if i < 0:
        return 0
    width, _, normal, before_slanted = rom[GLYPHS + i * 4:GLYPHS + i * 4 + 4]
    return width - (before_slanted if following in b"TVWY" else normal)


def word_width(rom, text, at):
    """func_8007C240: the width up to the next space, line break or end."""
    total = 0
    while at < len(text) and text[at] not in (0x20, 0x0A):
        if text[at] == 0x25:
            at += 2
            while at < len(text) and 0x30 <= text[at] <= 0x39:
                at += 1
            continue
        following = text[at + 1] if at + 1 < len(text) else 0
        total += char_width(rom, text[at], following)
        at += 1
    return total // 2 * 2


def layout(rom, text):
    """func_80079064: words wrap when they would pass the box's width."""
    x, rows, at = 0, [b""], 0
    while at < len(text):
        c = text[at]
        if at == 0 or text[at - 1] in (0x20, 0x0A):
            if BOX_WIDTH < x + word_width(rom, text, at) + 4:
                x = 1
                rows.append(b"")
        if c == 0x0A:
            x = 0
            rows.append(b"")
            at += 1
        elif c == 0x25:
            start = at
            kind = text[at + 1]
            at += 2
            digits = at
            while at < len(text) and 0x30 <= text[at] <= 0x39:
                at += 1
            if kind == 0x6D:
                x += 0x1C if text[digits:at] == b"6" else 0xB
                rows[-1] += text[start:at]
        else:
            following = text[at + 1] if at + 1 < len(text) else 0
            x += char_width(rom, c, following)
            rows[-1] += bytes([c])
            at += 1
    return rows


def main():
    rom = open(sys.argv[1], "rb").read()
    find = sys.argv[2].encode() if len(sys.argv) > 2 else None
    replace = sys.argv[3].encode() if len(sys.argv) > 3 else b""
    for i, data in files(rom):
        for n, (speaker, text) in enumerate(lines(data)):
            if find is None:
                print(f"{i:2} {n:3} speaker {speaker:2}: {text.decode('ascii')!r}")
            elif find in text:
                before = layout(rom, text)
                after = layout(rom, text.replace(find, replace))
                flag = "  TOO LONG" if len(after) > BOX_LINES else ""
                print(f"{i:2} {n:3} speaker {speaker:2}: {len(before)} -> {len(after)} lines{flag}")
                for row in after:
                    print(f"      {row.decode('ascii')}")


if __name__ == "__main__":
    main()
