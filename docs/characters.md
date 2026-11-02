# Character models

[`tools/extract_characters.py`](../tools/extract_characters.py) unpacks all of this from your own ROM, with a texture sheet for each model. [`tools/character_viewer.py`](../tools/character_viewer.py) builds a 3D viewer from your ROM, where parts of different characters can be mixed.

## Files

There are 62 model ids. Three tables of `{rom_start, rom_end}` pairs are indexed by id:

| Table | Contents | Stored |
|---|---|---|
| `D_80104C20` | F3DEX2 display list | Raw |
| `D_80104E10` | Vertices (`Vtx`, 16 bytes each) | [Compressed](rom-map.md#compression) |
| `D_80105000` | Textures and palettes | [Compressed](rom-map.md#compression) |

A vertex is `s16 x, y, z, flag, s, t` then `s8 nx, ny, nz` and an alpha byte. Vertices carry normals rather than colours, so characters are lit by the game's lights.

Display lists use segments, set per model by `func_800C7C14`:

| Segment | Points to |
|---|---|
| 7 | The model's display list |
| 8 | The model's vertices |
| 9 | The model's textures |
| A | The textures of the model in load slot 0 (`func_80026884`) |

All 2790 part lists (see below) read images only through segments 9 and A. Display list files also hold some commands outside those lists that use direct RAM addresses from the stage's fixed load at `0x802A4A00` (model 44 uses `0x802B65B8`, an I4 32x32 image). What draws them isn't identified yet, and the extractor shows them as magenta.

## Shared textures

Slot 0 is always Jean-Luc (id `0x22`), so segment A is his texture file. Other models borrow from it. Models 35-43 visibly wear his uniform this way, so repainting it changes them as well. Slot 0 can't simply be given to another character, because those models would then read the wrong images.

## Parts and detail levels

`D_80109540[id]` points to `{u32 type, near, mid, far}`. Each of the last three points to 15 display list pointers in segment 7, one for each rigid body part. There is no skinning: each part is drawn whole under its own matrix.

`func_800337A8` and `func_80059E5C` choose a list by comparing a value with thresholds (200 and 500 in the first, 250 and 600 in the second), apparently the distance from the camera *(inferred)*. `func_800A8B10` sets the initial list from the game mode. The chosen list is stored at `obj+0x1744`, and only the drawing function `func_80057100` reads it.

`func_80057100` sets segments 7, 8 and 9 from `obj+0x188C`, `+0x1894` and `+0x1890`, then for each part loads its matrix (`obj+0x1008 + part * 0x40`, converted from the floats at `obj+0x13F8 + part * 0x30`) and calls its display list. An entry of `-1` skips the part.

| Part | Body |
|---|---|
| 0 | Hips |
| 1-3 | Left thigh, shin, foot |
| 4-6 | Right thigh, shin, foot |
| 7 | Torso |
| 8 | Head |
| 9-11 | Left upper arm, forearm, hand |
| 12-14 | Right upper arm, forearm, hand |

The grouping comes from `func_80069D44`, which fills the matrices. Left and right follow from the skeleton's offsets and the axes below, taking +Y as the way the character faces.

### Parts are independent

Across all 62 models and all three detail levels, no part uses a vertex loaded by an earlier part, relies on an earlier part's texture or primitive colour, changes a segment, or calls another list, and each leaves the colour combiner on its default. A part from one model can therefore be drawn in place of any other.

### Textures on a part

A part is a series of texture loads, each followed by the triangles that use it. Textures are drawn at a scale of 0.5 *(inferred: coordinates span 0 to 2 of the image)*. Three combiners are used:

| Combiner | Result | Used for |
|---|---|---|
| `0xFC127FFF` | Texture x light | Full colour images, the default |
| `0xFC11FE04` | Texture x primitive colour x light | Greyscale images tinted by `G_SETPRIMCOLOR` |
| `0xFC3239FF` | Primitive colour x light | Plain colours, no texture |

Clothes often use tinted greyscale images, so one image can appear in different colours on different characters.

| Model | Near / mid / far triangles |
|---|---|
| 34 Jean-Luc | 457 / 308 / 256 |
| 35 | 442 / 252 / 252 |
| 0 | 250 / 250 / 149 |
| 24 | 111 / 111 / 111 |

The extractor's `characters.txt` lists these for every model.

## Skeleton

`type` is 0, 1 or 2 and is stored at `obj+0x175A`. It selects a skeleton, read by `func_80069D44` and `func_8006A508`: `D_80107490` (0), `D_80107580` (1) or `D_80107508` (2), each 30 floats. 54 models use type 0, 5 use type 1 and 3 use type 2. The names below are ours.

| Measurement | Type 0 (medium) | Type 1 (slim) | Type 2 (large) |
|---|---|---|---|
| Hip joint, from the hips origin (down, sideways) | 20, 9 | 15, 8 | 22, 10 |
| Thigh | 40 | 37 | 45 |
| Shin | 50 | 47 | 57 |
| Neck, up from the torso origin | 32 | 32 | 36 |
| Shoulder (up, sideways) | 28, 22 | 27, 16 | 32, 26 |
| Upper arm | 31.4 | 27 | 35 |
| Forearm | 25 | 23 | 29 |

The front end moves type 2 models down by 20 and type 1 models up by 10 when showing them (`func_80093A5C`).

Each part's vertices are relative to its own joint. These axes come from matrices logged in the running game:

| Parts | +X | +Y | +Z |
|---|---|---|---|
| Hips, limbs | Down the limb | Forward | Towards the character's right |
| Torso | Up | Forward | Towards the character's left |
| Head | Forward | Up | Towards the character's right |

`func_80069D44` places the hips and torso at the same point, sets the torso and head from angles, then calls `func_8006A508` for each limb. That function works out the two long bones from a target position (`obj+0xF08 + n * 12`, with `n` 2, 3, 6, 7) using the bone lengths, so a limb's bend is solved each frame rather than stored. The hand or foot then takes its own angles. Because targets are positions, the same animation can probably drive any skeleton *(inferred)*. Animation data itself isn't located yet.

`func_80057100` also scales some parts: the head by (2.5, 2, 2.5) while `D_8010DCCC` is set, and the torso and upper arms by amounts in `obj+0x1968` and `obj+0x196C` that rise and fall over time, which looks like breathing *(inferred)*.

## Mixing parts

This has been tested in the game on Jean-Luc, with parts from three other type 0 models. They drew with the right textures and lighting. This was only seen on a standing character from behind, so the front, walking and shooting are unchecked. Nothing in the game's code needs changing. Each part list entry is pointed at a small display list that selects the other model's files, calls its part and selects the original files again:

```
G_SEGMENT 7 = other model's display list
G_SEGMENT 8 = other model's vertices
G_SEGMENT 9 = other model's textures
G_DL      other model's part
G_SEGMENT 7, 8, 9 = this model's files
G_ENDDL
```

- `obj+0x1744` must be set again before each draw, since the detail level code overwrites it. A mod can do this from a hook on `func_80057100`.
- The game only uses the first 4 MiB of RAM, so `0x80400000` and up is free. The renderer's addresses are limited to 24 bits, so display lists and textures must stay below `0x81000000`. That rules out `recomp_alloc`, whose memory starts above that.
- Files load with `func_80052410(rom, dest, size)` (display list) and `func_8005230C(rom, dest, size)` (compressed), which stores the unpacked size in `D_801390B8`. Mixing therefore isn't bound by the stage's roster limit.
- Mixing skeleton types won't line up at the joints. The skeleton follows `obj+0x175A`, and parts were modelled for their own type's lengths. This has only been seen in the viewer, not in the game.

Not yet tested: models other than the player, versus mode, and characters whose id the game's code compares against.

## Model ids

| Ids | Contents |
|---|---|
| 0-17 | Soldiers *(inferred from their appearance)*: 3 body builds in 6 colour schemes. All colours of a build share vertices and textures. Only `G_SETPRIMCOLOR` in the display list differs, tinting mostly greyscale textures. |
| 18-23 | Other models, not yet identified |
| 24-33 | Models with only 15 display lists, so one detail level. 30-33 reuse 24's files. |
| 34 | Jean-Luc, confirmed by code (the default player model) |
| 35-43 | Characters in Jean-Luc's uniform, not matched to names |
| 44-53 | Characters in their own outfits, not matched to names |
| 54-57 | Characters who use none of Jean-Luc's textures, including men in suits and a woman in a skirt |
| 58-61 | One body in four jumpsuit colours |

The game's name list is at `0x8010DFE8`: JEAN-LUC, GUNT, DUKE, LEON, RYAN, BANDERAS, SRGT. THUNDER, LILA, JIN, ASH, CECILE, DAN, KENNETH, LISA, STEVE, JAKE, MIKE, THOMAS, LAW, KEITH, MATT, SECRETARY OF DEFENSE, ADVISOR, ASSISTANT, SOLDIER, PILOT, ENGINEER. Its order doesn't follow the model ids.

## Loading

`func_8004C438` loads a stage. It passes a list of ids ending in `0xFF` to `func_8004D144`, and `func_8004D39C` loads each into the next free slot. Slot pointers are in `D_801CC6B8` (display list), `D_801B0D20` (textures) and `D_80144E18` (vertices). Ids that share files are only loaded once (`func_8004D8B0`).

Two rosters are at `D_80116A70` and `D_80116A80`, chosen by area group. Both start with Jean-Luc. Data is packed from `0x8025CA00`. The next fixed load is at `0x802A4A00`, which suggests a limit of `0x48000` bytes *(inferred)*. These rosters use 84% and 81% of that.

`func_800A8B10` copies a model's slot pointers to `obj+0x188C` (display list), `obj+0x1890` (textures) and `obj+0x1894` (vertices).

The model id is `obj+0x16F5`. The code reads it about 170 times, often comparing it with specific ids, so changing a character's model will reach hardcoded behaviour.

## Not yet known

- Which id is which character, apart from Jean-Luc.
- Where animation data is stored.
- What the display list commands outside the part lists draw.
- Which rosters the other stages and versus mode use.
