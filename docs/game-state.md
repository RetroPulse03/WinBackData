# Game state, stages and checkpoints

## Main loop

`D_80187FB8` is the main loop state: 0 runs the front end (`func_80073600` each frame), 1 runs gameplay (`func_8004BA40`).

In the front end, `D_8010DBEA = 2` with a mode in `D_8010DBE9` (`func_8008F29C`) switches to gameplay after a 15-frame fade, setting `D_8016A41C = 0x0101` (normal play). The title intro and attract demo are gameplay with `D_8016A41C = 0x0808`, which skips loading event scripts, and `D_801390D4 = 1`.

During gameplay, `D_8016A418 = 1` with a map in `D_8016A41A` makes the frame callback reload into that map, as doors and map-change scripts do.

## Stages and maps

- `D_80158761` is the stage number (0-30).
- `D_8010D5F4[stage]` is a stage's first map, and its maps run up to the next stage's first map (64 maps): 0, 1, 3, 4, 5, 7, 10, 14, 18, 19, 21, 24, 25, 28, 30, 32, 33, 35, 37, 39, 40, 43, 44, 46, 47, 50, 51, 53, 57, 58, 62.
- `func_8008EEAC(stage)` starts a stage: it sets `D_80158761`, the map `D_8016A4EA` and the area group `D_8016A390 = D_8010D5A0[map]`.
- `func_8008F3E0` is the New Game path (`func_8008EEAC(0)`, `D_8010DBF8 = 8`, `func_8008F29C(9)`).
- `func_80092754(slot)` loads a game: it copies the 0xA0-byte save record from `D_8010DD10 + slot * 0xA0` to `D_80158760`, then calls `func_8008EEAC`.

The game has no stage names. It has four area names (`char*` table at `0x80111EF0`), chosen from the first map's area group: 0-8 OUTER GROUND, 9-15 MAIN OFFICE, 16-19 FACTORY, 20 and above CONTROL CENTER. These ranges are *(inferred)* from how the groups run through the stages. Versus mode also uses GROUND-1/2, OFFICE-1/2, FACTORY-1/2/3 and CENTER-1/2. The stage clear screen prints `STAGE-%02d CLEAR -<difficulty>-`.

## Progress and checkpoints

| Data | Size | Contents |
|---|---|---|
| `D_80137990` | 0x89C | Event block: checkpoint id at `+0x894`, its map at `+0x895` |
| `D_80158760` | 0x12E0 | Progress block: difficulty at `+0`, stage at `+1`, stored health at `+2`. The first 0xA0 bytes are the Controller Pak save record. |

Live health is at `+0x176B` in the player object. `func_800518D4` and `func_80051914` copy it to and from the stored value.

- `func_8009C8E0` saves a checkpoint, copying both blocks to `D_8011DAB0` and `D_8011E350`. The script command and the stage init `func_8004BD7C` call it.
- `func_8009C998` restores one, also setting the map, `D_8016A4BF = 1` and `D_8016A40E |= 1`. It is called on the continue screen (`func_800904E4`).
- `func_8009CAD8` clears checkpoint state.
- `func_8008EF28` resets the mission: it clears the event block and the progress block's first 0xA0 bytes, and makes the next stage init take a start snapshot.

## Event scripts

Entering map `m` loads event file `m + 1` from the archive at ROM `0x931470` (`u32 count`, then `count + 1` offsets from the archive start).

An event file has `u16 count, condition offset, script offset` and then 8-byte events (`id, ?, condition, script`). Each script is a `u16` command count followed by commands: an opcode byte, then the arguments listed in `D_8010DF38[opcode]` (`flags, argc, u16 mask of 2-byte arguments`).

The script interpreter is `func_8009AA9C`, with a jump table by opcode:

- Opcode 42 (entry `0x8009BADC`) is a checkpoint. Its first argument is the checkpoint id. The command calls `func_8009C8E0` at `0x8009BB00` and still changes the saved copy afterwards.
- Opcode 38 (entry `0x8009BA34`) loads another event file.

A stage's checkpoints are its unique (map, id) pairs in script order. Map entry scripts often trigger a checkpoint straight away.
