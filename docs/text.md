# Text

[`tools/dialogue.py`](../tools/dialogue.py) lists the game's dialogue from your ROM and works out how each line wraps.

All of the English text is plain uppercase ASCII. None of it is compressed.

## Dialogue

The dialogue archive is at ROM `0x9264B0`: `u32 count`, then `count + 1` offsets from the archive's start. It holds 44 files.

`func_8009A500` and `func_8009A2FC` read a file with `func_8008E728` into the buffer at `0x802C7080`, unless it is the file already loaded (`D_8010E104`). That buffer is `0x1130` bytes, ending where the buffer for the current line starts (`0x802C81B0`). The largest file is `0x1078` bytes.

A file is `u16 count`, then `count` `u16` offsets from the file's start, then the lines. A line is one speaker byte followed by text ending in a zero. Speaker 0 is the player. Speakers `0x1D` and up don't use the normal text box.

The script command that shows a line is opcode 4, with arguments `(time, file, line)`.

### Codes inside text

| Code | Meaning |
|---|---|
| `%A30` | Moves on by itself after that many frames *(inferred from `func_8009A280`, which adds these up)* |
| `%m8` | Draws a button icon |
| `%N`, `%w` | Inserts a number |
| `\n` | Line break |

### Wrapping

Lines wrap automatically, so a name can be changed without editing line breaks. The dialogue box is `0x112` wide. A word moves to the next row if it would pass the box's width (`func_80079064`), and rows are 10 pixels apart. The box has room for 3 rows.

Letters have their own widths, in the table at `D_8010AE30`: width, height, and two kerning values, the second used before T, V, W and Y.

## Name lists

| Address | Used for | Notes |
|---|---|---|
| `0x8010DFE8` | The speaker's name, above dialogue | Indexed by speaker byte. The Japanese names follow the English ones and aren't used in this version *(inferred)*. |
| `0x801129E4` | Versus with up to 2 players, and the character screen | Entry 0 is the player |
| `0x80112A80` | Versus with 3 or more players | 6 short names. Entry 1 is `JEAN`, entry 0 `STEVE`. |

These lists hold pointers, so one entry can be pointed at a new string of any length.

## Jean-Luc's name

`JEAN-LUC` is in 47 places across 21 dialogue files, plus two of the name lists. `JEAN` is in the short list. A `Jean BUSY!!` string at ROM `0xF4AF0` looks like a debug message *(inferred)*.

Changing it to a name 3 letters longer leaves every line within the 3 rows, checked with `dialogue.py`, and the longest was also checked in the game.

`COUGAR` is not in the ROM as text, in any capitalisation, either directly or in the 629 archive and table files that were unpacked and searched. If the game uses that surname, it is drawn inside an image. Images have not been searched.

## Changing text from a mod

Hook `func_8008E728` on entry to note its arguments `(dest, archive, index)`, and on return rebuild the file in `dest`, with new offsets, when `archive` is `0x9264B0`. Keep the result inside the `0x1130` byte buffer. Name lists can be changed by overwriting their pointers.
