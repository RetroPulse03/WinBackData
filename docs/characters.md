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

`D_80109540[id]` points to `{u32 type, near, mid, far}`. Each of the last three points to 15 display list pointers in segment 7, one for each rigid body part, drawn whole under its own matrix. On models from 34 up, [joints](#joints) built each frame fill the gaps between some of them.

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

Across all 62 models and all three detail levels, no part uses a vertex loaded by an earlier part, relies on an earlier part's texture or primitive colour, changes a segment, or calls another list, and each leaves the colour combiner on its default. A part from one model can therefore be drawn in place of any other, though the joints around it still belong to the object's own model.

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

Each part's vertices are relative to its own joint. These axes come from matrices logged in the running game, reduced to a character standing straight:

| Parts | +X | +Y | +Z |
|---|---|---|---|
| Hips, legs | Down the limb | Forward | Towards the character's right |
| Arms, hands | Down the limb | Backward | Towards the character's left |
| Torso | Up | Forward | Towards the character's left |
| Head | Forward | Up | Towards the character's right |

Arms and legs are built the same way but face opposite ways. `func_8006A508` always bends a limb's second bone towards its first bone's -Y, which is backward at the knee and forward at the elbow. Jean-Luc's elbow pads therefore sit on the arm's +Y side. In the logged poses each arm also twists about +X, and the upper arm and forearm always share +Z, the elbow's hinge. A hand with its stored angles at zero would match its forearm *(from the code, not logged)*. Its wide faces are ±Z, so the palm would face the leg *(inferred)*.

`func_80069D44` places the hips and torso at the same point, sets the torso and head from angles, then calls `func_8006A508` for each limb. That function works out the two long bones from a target position (`obj+0xF08 + n * 12`, with `n` 2, 3, 6, 7) using the bone lengths, so a limb's bend is solved each frame rather than stored. The hand or foot then takes its own angles. Because targets are positions, the same animation can probably drive any skeleton *(inferred)*. Animation data itself isn't located yet.

`func_80057100` also scales some parts: the head by (2.5, 2, 2.5) while `D_8010DCCC` is set. While bit `0x40000000` of `obj+0xF4` is set, it scales the torso by (1, `obj+0x1968`, `obj+0x196C`) and each upper arm by (1, `obj+0x196C`, `obj+0x196C`), so they widen and deepen but keep their length. `func_80069D44` moves `+0x1968` by `+0x1974` each frame between 1.0 and 1.15 (1.1 outside normal play), with `+0x196C` moving at half that rate, and `+0x1970` sets the speed. This looks like breathing *(inferred)*. Logged on Jean-Luc in mission 1, the flag was set in every sample, `+0x1968` reached 1.155 and `+0x196C` 1.077. The scale is never below 1, so the torso is always at or above the width of its model.

Scale checks, on Jean-Luc in mission 1 *(one frame's matrices, and one comparison screenshot measured by eye)*:

- Each row of the torso's final matrix (`obj+0x1008 + 7 * 0x40`) equals the matching row of its float matrix (`obj+0x13F8 + 7 * 0x30`) times 1, `+0x1968` and `+0x196C`. Row Y is forward and row Z is sideways, so depth changes twice as much as width. The other parts have rows of length 1, apart from the upper arms.
- Forcing the scale to 1.0 and to 1.15 changed only thin lines at the edges of the body in a captured frame.
- The torso's model is 44 units wide and 27 deep, and the head is 16 wide. The torso's width and depth are nearly the same at all three detail levels. If a unit is about 1 cm, they are believable human sizes *(inferred from the skeleton's lengths)*.
- Compared with a Switch Online screenshot taken from behind (a different scene and pose), torso width over torso height was about 0.87 there and 0.84 in the recompilation, head height over torso height about 0.33 in both, and torso height over belt-to-knee length about 1.25 and 1.22. This is Nintendo's emulation, not an N64.

## Joints

Models 34 to 58 leave real holes at the waist, hips, knees and elbows, which the game fills with a stretched tube of 16 vertices rebuilt every frame. These tubes are where the crotch, knee areas and much of the elbow pads come from. Models 0-33 have no joints and don't need them. Models 59-61 need them but have [no joint data](#models-59-61).

| Vertices in the slot | Joint | Between parts |
|---|---|---|
| `+0x208`, `+0x308` | Hips | 0 and 4, 0 and 1 |
| `+0x008`, `+0x108` | Knees | 4 and 5, 1 and 2 |
| `+0x608` | Waist | 0 and 7 |
| `+0x408` | Right elbow | 12 and 13 |
| `+0x508` | Left elbow | 9 and 10 |

- `func_8006B3B8` claims one of 8 slots of `0xC48` bytes at `D_801CC710`, storing its number at `obj+0x179B`. It reads `0x700` bytes from ROM `0x83E340 + (id - 0x22) * 0x700` to `0x8020E400`, holding the texture coordinates and other fixed values of each tube. The table therefore exists only for ids `0x22` to `0x3A`; what follows it is unrelated data.
- `func_8006B564` places the tubes. `func_8006B5B4`, `func_8006B9C0`, `func_8006E8B4` and `func_8006DCA4` take four points from each of the two parts and transform them by those parts' matrices. The points are signed bytes in tables indexed by `id - 0x22` in the asset file below, such as `D_2003150`, `D_20031B4`, `D_20032E0` and `D_2003344`. Each point becomes two vertices, each with a flat normal, so a tube has hard edges. `func_800337A8` and `func_80059E5C` call this, so it runs when a character's detail level is chosen each frame *(inferred)*.
- `func_8006C68C` draws the hips and knees, and `func_8006EF90` the waist and elbows, right after the parts. Each loads a texture chosen by model id, from the object's texture file (`obj+0x1890`) or slot 0's (`D_801B0D20[0]`), then calls the same 16-vertex triangle list, `D_20036C8`.
- `obj+0x1768` is the detail level in use: 1 near, 2 mid, 3 far. `func_80057100` only draws joints for Jean-Luc at near and mid, and for other ids above 34 at near. The mid and far part lists therefore don't rely on them, at least beyond Jean-Luc.

[`tools/character_viewer.py`](../tools/character_viewer.py) runs these functions through [`tools/game_code.py`](../tools/game_code.py), a small MIPS interpreter, so it gets each model's joints without restating that logic. Compared with Jean-Luc's vertices logged from the running game, given the same part matrices, its positions and texture coordinates were identical on two standing poses, while a third was up to 21 units off, probably because the logged vertices were a frame older than the matrices *(inferred)*. Normals differed by at most 1 in 127. The waist's normals are a fixed table, `D_80105DD0`, turned by the matrix of the whole object at `obj+0x13C8` (`func_8006E73C`), rather than taken from its two parts.

Tubes don't close every gap. Thin slits remain at the elbows, knees and the outside of the right hip, and the same code leaves them in Jean-Luc's logged poses, so they aren't caused by the viewer. Other models' poses in the game haven't been compared. Straight arms make the elbow slits largest, so the viewer bends its elbows by 15°, which isn't a pose taken from the game.

Measured on one frame of Jean-Luc in mission 1, from a copy of the game's memory taken as the frame was submitted, the elbow tubes' ends lie up to about 0.5 units from the upper arm and 0.5 to 1.5 units from the forearm. The tubes are stored in whole world units: `func_80071B60` places each point, itself a whole number in the signed-byte tables, and truncates the result with `trunc.w.d`. That alone can move a point up to about 1.7 units *(that this causes the gaps is inferred from the code; the gaps are measured)*. At the usual camera distance a unit is about 0.15 pixels of the 320x240 picture, so these slits are a fraction of an N64 pixel, but they show at higher resolutions. Jean-Luc's near and mid detail levels give identical arm gaps, so a higher detail level would not close them.

### Models 59-61

The joint tables and the vertex template both have exactly 25 entries, for ids 34 to 58, and the texture jump tables in the drawing functions stop at the same id. Models 59-61 would read past the end at the near detail level, which gives long stray triangles and wrong images. They aren't in the two [rosters](#loading) identified so far, which only hold Jean-Luc and soldiers. Which stages use them isn't known, so the game may never show them up close *(inferred)*.

These three share model 58's body, so the viewer gives them 58's joints with the model's own textures, and says so on screen. Models 59 and 61 keep the joint images at 58's offsets. Model 60 stores the identical hip and knee images elsewhere, at `0x1EE0` and `0x24E0` with palettes at `0x22E0` and `0x26E0`, and has a camouflage image at 58's offset. None of this is how the game draws them.

## Asset file

Segment 2 points at `0x80229A00`, which holds ROM `0xF87B0` onwards. This was found from tables in the code: `D_2003150` is at ROM `0xFB900`. The code that loads it hasn't been traced. It holds the joint tables and the triangle list above, and at `+0xA8D0` the headers of the 2387 [animation](animations.md) clips.

## Mixing parts

This has been tested in the game on Jean-Luc, with parts from three other type 0 models. They drew with the right textures and lighting. This was only seen on a standing character from behind, so the front, walking and shooting are unchecked. The joints stayed Jean-Luc's, so his trousers showed at the crotch of the orange legs. Nothing in the game's code needs changing for the parts themselves. Each part list entry is pointed at a small display list that selects the other model's files, calls its part and selects the original files again:

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

- Models 0-33 have no joint data, so mixing their parts onto a model with joints depends on how those parts' ends happen to meet.

Not yet tested: mixing onto models other than the player, and skeleton types other than 0.

## Replacing the main character

The player can be given files of their own, with no changes to the game's code and without affecting anyone else. This was tested on mission 1, the opening helicopter cutscene and versus mode, in scripted runs only. The character stands, walks and aims with the right textures, while models 35-43 in the same cutscene keep the original uniform.

The object keeps id `0x22`. The code compares the id about 170 times, so changing it would reach hardcoded behaviour. Everything is changed only while `func_80057100` draws that object and is put back when it returns:

- **Files:** load private copies at `0x80400000` and up, and point `obj+0x188C`, `+0x1890` and `+0x1894` at them. Model files themselves are private to their id. Only textures are shared.
- **Parts:** point `obj+0x1744` at lists that set segments 7, 8, 9 and A, then call the part. Jean-Luc's part lists read all of their images through segment A and none through segment 9, and most models from 35 up read some of theirs from it too. So A must point at the private copy of his textures during the draw, and back at the real ones afterwards (one `G_SEGMENT` appended to the display list when the function returns).
- **Detail:** set `obj+0x1768` to 1. It is only read by `func_80057100`, so the character always draws at near detail, the level that joints are built for.

### Joints from other models

The model id decides a joint's look in several functions. Each can be given a different id for a moment, then have `0x22` put back:

| Function | Reads the id for | Joints |
|---|---|---|
| `func_8006B3B8` | Fixed vertex values from the ROM, once when the slot is claimed | Each tube separately |
| `func_8006B5B4`, `func_8006B9C0` | Positions | One leg's hip and knee each |
| `func_8006E8B4`, `func_8006DCA4` | Positions | Elbows, waist |
| `func_8006C68C` | Texture and its format | Hips and knees together |
| `func_8006EF90` | Texture and its format | Waist and elbows together |

Since `func_8006EF90` handles the waist and elbows as one, swapping the id gives one source for the hips and knees and one for the waist and elbows. A waist that matches the torso while the elbows match different arms would need more work. The fixed values are 7 blocks of `0x100` bytes in the `0x700` read from ROM: elbows at `+0x100` and `+0x200`, waist at `+0x000`, hips at `+0x300` and `+0x400`, knees at `+0x500` and `+0x600`. Each is copied into the slot by `func_8006DC18` and `func_8006DB10` (see `func_8006B3B8` for destinations). `func_8006C68C` and `func_8006EF90` also read `D_801B0D20[0]` directly rather than through segment A, so it must point at the private textures while drawing.

Joints only exist for ids 34 to 58. Tested with hips and knees from model 51, and waist and elbows from model 53. Elbow creases similar to the [slits](#joints) in Jean-Luc's own joints remain.

Also tested with model 34's parts and model 37's forearms, in a scripted mission 1 run. In the viewer, on a bright background, model 34's elbows leave a slit across the top of model 37's forearm and model 37's elbows close it, so the arm joints should follow the forearms. The waist looks the same from either of the two models from the front; other angles weren't compared.

Model 34 is drawn in the opening cutscene as well as in play, sitting with the team, so replacing it covers that scene too. Other cutscenes haven't been checked. In that cutscene, models 35-43 are all drawn.

### Repainting the private copies

Since the files are private copies, a mod can overwrite bytes in them after loading, and nothing else in the game changes. Tested in a scripted mission 1 run, where the player's repainted head and clothes drew correctly. Whether the team in the opening cutscene keeps its look with repainted files wasn't checked.

Jean-Luc's head at near detail reads these images, at offsets in his texture file:

| Image | Format | Shows |
|---|---|---|
| `0x1040`, palette `0x1440` | CI8 64x16, mirrored in T | The front of the face. U runs down the head (hairline near U 17, eyes near 33, mouth near 52, chin at 64) and T runs out from the centre line, so left and right are the same pixels. |
| `0x1640`, palette `0x1E40` | CI8 64x32 | Both sides of the head: hair, cheek and jaw |
| `0x120`, `0x300`, `0x59B0` | CI4, CI4, RGBA16 | The back and top of the hair |
| `0x240` | CI4 16x12 | Ear |
| `0x2C0` | CI4 8x8 | Under the chin |
| `0x0`, `0x55B0` | CI4, RGBA16 | Neck and collar |

His eyebrow and the dark contouring over his eye are painted as one dark band, roughly U 28 to 33. The brow is the part above about 13.7 units up the head *(judged by eye)*.

Colours on the clothes aren't all in images. The blue stripe on each boot is an I4 image tinted by `G_SETPRIMCOLOR` `0x4040FFFF`, at display list offsets `0x1930`, `0x1AD8`, `0x3190` and `0x3310`, so recolouring it means changing the private display list too. The offsets above are read from the display lists. The landmark positions along U were read by eye *(inferred)*.

## Model ids

| Ids | Contents |
|---|---|
| 0-17 | Soldiers *(inferred from their appearance)*: 3 body builds in 6 colour schemes. All colours of a build share vertices and textures. Only `G_SETPRIMCOLOR` in the display list differs, tinting mostly greyscale textures. |
| 18-23 | Other models, not yet identified |
| 24-33 | Models with only 15 display lists, so one detail level. 30-33 reuse 24's files. `D_8011285C` lists them as 29, 24, 25, 26, 27, 28, 30, 31, 32, 33. Compared with the short names at `0x80112A80` (see [Text](text.md#name-lists)), 29 is Steve, 24 Jean-Luc, 25 Dan, 26 Mike, 27 Matt and 28 Lisa, which suggests they are the bodies for 3 or more players *(inferred)*. This fits what 3- and 4-player Versus shows in play: low-detail models in set colours and a much shorter character list than 2-player Versus. Which model each Versus character uses hasn't been traced. Models 24 and 30-33 read Jean-Luc's head images through segment A, including the face at `0x1040`. |
| 34 | Jean-Luc, confirmed by code (the default player model) |
| 35-43 | The rest of Jean-Luc's S.C.A.T. team, in his uniform. The character screen's model table (`0x8011283C`, see [Text > Name lists](text.md#name-lists)) gives 35 Lisa, 36 Law, 37 Jake, 38 Mike, 39 Keith, 40 Matt, 41 Steve, 42 Tom and 43 Dan. |
| 44-53 | Characters in their own outfits, not matched to names |
| 54-57 | Characters who use none of Jean-Luc's textures, including men in suits and a woman in a skirt |
| 58-61 | One body in four jumpsuit colours. Only 58 has joint data. |

The game's name list is at `0x8010DFE8`: JEAN-LUC, GUNT, DUKE, LEON, RYAN, BANDERAS, SRGT. THUNDER, LILA, JIN, ASH, CECILE, DAN, KENNETH, LISA, STEVE, JAKE, MIKE, THOMAS, LAW, KEITH, MATT, SECRETARY OF DEFENSE, ADVISOR, ASSISTANT, SOLDIER, PILOT, ENGINEER. Its order doesn't follow the model ids.

## Loading

`func_8004C438` loads a stage. It passes a list of ids ending in `0xFF` to `func_8004D144`, and `func_8004D39C` loads each into the next free slot. Slot pointers are in `D_801CC6B8` (display list), `D_801B0D20` (textures) and `D_80144E18` (vertices). Ids that share files are only loaded once (`func_8004D8B0`).

Two rosters are at `D_80116A70` and `D_80116A80`, chosen by area group, in Story. Both start with Jean-Luc. Data is packed from `0x8025CA00`. The next fixed load is at `0x802A4A00`, which suggests a limit of `0x48000` bytes *(inferred)*. These rosters use 84% and 81% of that. With more than one player there is no roster: `func_8004C438` loads Jean-Luc and each player's model, taking player `p`'s id from `D_8016A4A9 + 3 × p + D_8016A4B9[p]` and storing it in `D_8010D59C[p]` for player creation. The 3 entries per player fit Team Battle's three members, used in turn (`D_8016A4B9[p]`, see [Rendering](rendering.md#story-and-versus)) *(inferred)*.

`func_800A8B10` sets a character up from its model id: the skeleton type (`obj+0x175A`) and the part list for the detail level (`obj+0x1744`) from `D_80109540[id]`, then copies the model's slot pointers to `obj+0x188C` (display list), `obj+0x1890` (textures) and `obj+0x1894` (vertices). If the id isn't loaded (`func_8004D570` returns -1) it uses the files at `D_80138EEC`, `D_80138EF0` and `D_80138EF4`. Player creation (`func_800593EC`) writes the id just before calling it.

`func_8004D6E8(obj, n)` loads one character's own three files to `0x8027CA00` (`n` = 0) or `0x80322400 + (n - 1) × 0x12000`, and points the character at them. It is only called from `func_800937C4` *(inferred to be the Versus character screen, see [Game state](game-state.md#players-and-split-screen))*.

Model 35 has skeleton type 1. Its files are 0x3920 bytes of display list, 0x4A00 of vertices and 0x4FF0 of textures unpacked, about 53 KB, more than either Story roster leaves free (16-19% of `0x48000`, 47-56 KB). The story co-op mod loads it at `0x80700000`, outside the game's memory, and points player 2 at it after `func_800A8B10`.

The model id is `obj+0x16F5`. The code reads it about 170 times, often comparing it with specific ids, so changing a character's model will reach hardcoded behaviour.

## Not yet known

- Which id is which character, apart from Jean-Luc and (by eye) Jake.
- What the display list commands outside the part lists draw.
- Which rosters the other stages and versus mode use.
