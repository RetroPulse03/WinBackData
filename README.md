# WinBack Data

A reference for how *WinBack: Covert Operations* (N64, USA) works and where its data is: file formats, memory addresses, game logic and tools for reading them. It was built while making [WinBack Recompiled](https://github.com/RetroPulse03/WinBackRecomp).

**No game data is included.** Nothing here contains the ROM or files taken from it. The tools work on your own copy of the game.

## Contents

| Document | Covers |
|---|---|
| [ROM map](docs/rom-map.md) | ROM layout, code segment, compression |
| [Characters](docs/characters.md) | Character models, textures, body parts, loading |
| [Game state](docs/game-state.md) | Main loop, stages, checkpoints, event scripts |
| [Camera](docs/camera.md) | Player camera movement and data |
| [Rendering](docs/rendering.md) | Microcode, framebuffer and drawing details |

## Tools

Run these with Python 3, using your own ROM. They need no other packages.

```
python tools/extract_characters.py <rom.z64> [output folder]
```

This unpacks every character model and writes a texture sheet for each. The output folder defaults to `output/characters`. Output is ignored by Git and must not be shared.

## Reading these notes

- Names like `func_8004D144` and `D_80158760` are automatic names for addresses in the USA version. The ROM's SHA-1 is `fa04477b321a95e1f7a2edcac5c09bfa6ef72041`.
- Items marked *(inferred)* come from the shape of the data and haven't been confirmed in the game's code or by testing.

## Contributing

Corrections and new findings are welcome through issues and pull requests. Don't include the ROM or anything taken from it.
