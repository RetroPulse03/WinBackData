# Character models

[`tools/extract_characters.py`](../tools/extract_characters.py) unpacks all of this from your own ROM, with a texture sheet for each model.

## Files

There are 62 model ids. Three tables of `{rom_start, rom_end}` pairs are indexed by id:

| Table | Contents | Stored |
|---|---|---|
| `D_80104C20` | F3DEX2 display list | Raw |
| `D_80104E10` | Vertices (`Vtx`, 16 bytes each) | [Compressed](rom-map.md#compression) |
| `D_80105000` | Textures and palettes | [Compressed](rom-map.md#compression) |

Vertices carry normals rather than colours: their last bytes form vectors of length about 127.

Display lists use segments, set per model by `func_800C7C14`:

| Segment | Points to |
|---|---|
| 7 | The model's display list |
| 8 | The model's vertices |
| 9 | The model's textures |
| A | The textures of the model in load slot 0 (`func_80026884`) |

A few images use a direct RAM address instead (model 44 uses `0x802B65B8`). What is stored there isn't identified yet. The extractor shows these as magenta.

## Shared textures

Slot 0 is always Jean-Luc (id `0x22`), so segment A is his texture file. Other models borrow from it. Models 35-43 visibly wear his uniform this way, so repainting it changes them as well. Slot 0 can't simply be given to another character, because those models would then read the wrong images.

## Parts and detail levels

`D_80109540[id]` points to `{u32 type, near, mid, far}`. Each of the last three points to 15 display list pointers in segment 7, one for each rigid body part. There is no skinning.

`func_800337A8` and `func_80059E5C` choose a list by comparing a value with thresholds (200 and 500 in the first, 250 and 600 in the second), apparently the distance from the camera *(inferred)*. `func_800A8B10` sets the initial list from the game mode. The chosen list is stored at `obj+0x1744`.

Part order *(inferred from vertex extents)*: 0 hips, 1-3 and 4-6 legs, 7 torso, 8 head, 9-11 and 12-14 arms.

`type` is 0, 1 or 2 and is stored at `obj+0x175A`. Its meaning is unknown, though it may be a body type *(inferred)*.

| Model | Near / mid / far triangles |
|---|---|
| 34 Jean-Luc | 457 / 308 / 256 |
| 35 | 442 / 252 / 252 |
| 0 | 250 / 250 / 149 |
| 24 | 111 / 111 / 111 |

The extractor's `characters.txt` lists these for every model.

## Model ids

| Ids | Contents |
|---|---|
| 0-17 | Soldiers *(inferred from their textures)*: 3 body builds in 6 colour schemes. All colours of a build share vertices and textures. Only `G_SETPRIMCOLOR` in the display list differs, tinting mostly greyscale textures. |
| 18-23 | Other models, not yet identified |
| 24-33 | Models with only 15 display lists, so one detail level. 30-33 reuse 24's files. |
| 34 | Jean-Luc, confirmed by code (the default player model) |
| 35-61 | Other characters, not yet matched to names |

The game's name list is at `0x8010DFE8`: JEAN-LUC, GUNT, DUKE, LEON, RYAN, BANDERAS, SRGT. THUNDER, LILA, JIN, ASH, CECILE, DAN, KENNETH, LISA, STEVE, JAKE, MIKE, THOMAS, LAW, KEITH, MATT, SECRETARY OF DEFENSE, ADVISOR, ASSISTANT, SOLDIER, PILOT, ENGINEER. Its order doesn't follow the model ids.

## Loading

`func_8004C438` loads a stage. It passes a list of ids ending in `0xFF` to `func_8004D144`, and `func_8004D39C` loads each into the next free slot. Slot pointers are in `D_801CC6B8` (display list), `D_801B0D20` (textures) and `D_80144E18` (vertices). Ids that share files are only loaded once (`func_8004D8B0`).

Two rosters are at `D_80116A70` and `D_80116A80`, chosen by area group. Both start with Jean-Luc. Data is packed from `0x8025CA00`. The next fixed load is at `0x802A4A00`, which suggests a limit of `0x48000` bytes *(inferred)*. These rosters use 84% and 81% of that.

`func_800A8B10` copies a model's slot pointers to `obj+0x188C` (display list), `obj+0x1890` (textures) and `obj+0x1894` (vertices).

The model id is `obj+0x16F5`. The code reads it about 170 times, often comparing it with specific ids, so changing a character's model will reach hardcoded behaviour.

## Not yet known

- Which id is which character, apart from Jean-Luc.
- The skeleton and animation data.
- The meaning of `type`.
- What the direct RAM texture addresses point to.
- Which rosters the other stages and versus mode use.
