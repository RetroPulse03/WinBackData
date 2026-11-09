# Game state, stages and checkpoints

## Main loop

`D_80187FB8` asks the main loop to change state: 0 runs the front end (`func_80073600` each frame), 1 runs gameplay (`func_8004BA40`). It isn't a record of the current state: it read `0xFFFFFFFF` throughout a running mission, so that value looks like "no change asked for" *(inferred)*.

`D_8016A41C` is what the game is currently running. Each object has a mask at `+0x36`, and `func_80028060` only updates an object if the mask's low byte shares a bit with this value's low byte. The high byte is checked the same way in the function after it *(probably for drawing, inferred)*.

| Value | Seen during |
|---|---|
| `0x0101` | Normal play, including the camera's scripted views |
| `0x0102`, then `0x0202` | The pause menu. `func_8007F708` saves the old value in `D_8011D5E0`, and closing the menu restores it. |
| `0x0404` | The front end |
| `0x0420` | One front end screen *(which one wasn't identified)* |
| `0x0808` | The title intro and attract demo |

The code at `0x800935DC` sets the low bits to `0x20`, and `func_800B5944` swaps `0x01` and `0x20` *(what these screens are wasn't identified)*.

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

- Opcodes 2 and 36 play an [animation](animations.md#playing-a-clip).
- Opcode 4 shows a dialogue line. Opcode 9 sets a flag (`func_800993AC`). Opcode 13 moves to a map and entrance.

An event's condition is a `u8` count, then 3-byte tests: a kind byte and a big-endian `u16` value, read by `func_8009BBB8` (table `jtbl_801195E0`). Kind 4 passes when the game clock `D_8010DD60`, in minutes, is at least the value. Kind 5 passes when flag `value >> 8` equals `value & 0xFF`. Kind 11 ends the list and passes. [`tools/event_scripts.py`](../tools/event_scripts.py) reads all of this. See [Cheat codes](cheat-codes.md#endings) for how the endings use it.

- Continuing doesn't put the player where the checkpoint triggered. `func_8004C108` uses spawn 0 of the checkpoint's map unless `D_80159A3C` is set, and then it uses the spawn numbered like the checkpoint id (`D_80138224`). In map 0, the event that holds checkpoint 6 warps the player to entrance 6 first (`13(0, 6)`, then `42(6)`), so the two match there. Elsewhere, that the id always names the entrance is *(inferred)*: all 28 checkpoints tried had a matching spawn.
- We found no code that sets `D_80159A3C`: its only direct references are the clear in `func_80073738` and reads in `func_8004C108` and `func_80099548`. Events with flag 0x40 don't run while it is set. It sits in the progress block, at `+0x12DC`. Its purpose is *(unconfirmed)*.
- Spawns are at `D_80144700`, 0x1C bytes each, with the count in `D_8016A398`. `+0x18` is the spawn number and `+0x19` the type (0 player, 1 camera); `func_800513FC` needs both.

A stage's checkpoints are its unique (map, id) pairs in script order. Map entry scripts often trigger a checkpoint straight away.

## Players and split screen

`D_8016A4EE` is the number of players, set when a mode starts. `D_8016A40E` holds the mode: bit 0 is Story (one player, one view) and bit 1 the 2P split. About 140 functions test bit 0, so it stands for "this is Story" rather than only for the layout.

- **Creating players.** Stage init (`func_8004BD7C`, run on every map entry, doors included) calls `func_800593EC(i)` for each player. It stores the player object in `D_801390C0[i]` and the index at `+0x90`, sets the model id at `+0x16F5` (always `0x22`, Jean-Luc, in Story; otherwise `D_8010D59C[i]`) and creates the player's camera with `func_800347F0`, whose controller number (`camera+0x18`) is the player index.
- **Start points.** `func_8004C108` fills each player's start point before that: position `D_8016A424` (12 bytes per player), `D_8016A39A` (u16), heading `D_8016A454` (float) and the camera's start position `D_8016A464` (12 bytes). In Story it only picks a spawn for player 0, so a second player's spawn id is left uninitialised. Map reloads (`D_8016A418` set) write only player 0's.
- **Views.** `func_80025F10` builds each frame's two graphics tasks (scene, then laser sight). It draws one view if bit 0 of `D_8016A40E` is set or `D_8016A41C & 0x600`, two if bit 1 is set (`func_80026A10(views, view, 1, 8/3, flags)` for views 0 and 1, top and bottom), and four otherwise. `func_80026A10` stores the view in `D_8016A40F`, and its camera comes from per-controller arrays the camera writes through `func_80026760` / `func_800266D0`.
- **Two players in Story** work with the game's own code: keeping the count at 2 from the start point lookup on, giving player 1 player 0's start point and drawing the two-view split gives each player their own controller and view (tested in a scripted run on stage 1, 2026-11-08). The Story HUD (`func_800D20CC`) still draws once over the whole screen for player 0, and its update only follows player 0 (see [Rendering > Story and Versus](rendering.md#story-and-versus) for each part). How the game treats player 1's health, death and pause hasn't been checked.
- **Character slots.** Characters live in 8 slots of `0x1980` bytes from `0x80179350`; players take the first ones (`D_801390C0[0]` = `0x80179350`, `[1]` = `0x8017ACD0`). The allocator (`func_80027470(0, …)` → `func_80027A38`) takes the first slot whose `+0x92` halfword is 0, and `func_800593EC` sets it to 1 for each player. After making the players, stage init calls `func_80034364`, which creates the enemy spawner (`func_8003463C`) and clears `+0x92` in slots 1-7, because Story has only one player. A second player in Story is therefore overwritten by the first enemy spawned: when player 0 enters a zone, `func_8003463C` finds it (`func_8004DF54`) and `func_80034420` spawns its enemies from the table at `D_80158904` (0x16 bytes each) with `func_8002C86C`. Seen in a scripted run on stage 1 (2026-11-08, lldb watchpoints): the guard of the first scripted scene was written into slot 1. `func_80034310` looks for existing enemies in slots 1-7 by `+0x34 == 2` on their object, which a player's (1) doesn't match.
- **When the slots run out.** `func_80027A38` returns 0 when all 8 slots are in use, and `func_8002C86C` then returns 0 without making the enemy; nothing else happens. The only other code that makes a character is `func_80093F20`, called from the front end (`func_8007F224`, `func_800E2320`, `func_800E2AFC`) *(inferred to be the Versus character screen's model: it sets `+0x16F5` and calls the Versus weapon function `func_800937C4`)*. So in Story every character besides the player comes from the spawner, and 7 are the most that can exist at once.
- **Where enemies come from.** The map loader `func_80050750` copies the map's placement list (24 bytes each, ending with `-1`) to `D_801BED70`, with the zone at `+0xA`. On a map's first visit, `func_80051E34` turns it into the stage's table at `D_80158904`, and `D_801588E6` (6 bytes each, up to 5 maps) records each map's first entry and count. An entry's `+0xB` is the enemy's health. When an enemy is removed, `func_8005196C` writes its position, zone, health and state back into its entry, so it comes back as it was. The spawner only looks at the zone player 0 is in: `func_8004DF54(2, 0, …)`.
- **How many at once.** The map files are an archive at ROM `0x279D00` (a count, then offsets), read by `func_8008E728` and unpacked. The placement list is the eleventh list in the unpacked file. An entry's `+0xC` is its kind, which gives the starting health (`D_80103BB0[kind]`; kind `0x29` gets 127, kinds from `0x2B` and entries with `+0xF & 0x80` get 1). [`tools/enemy_placements.py`](../tools/enemy_placements.py) runs the map loader for every map and counts each zone's characters. Of the 82 map files, 63 place characters. Across all of them, 288 zones have 1 character, 284 have 2, 123 have 3 and 25 have 4; none has more. So entering a zone never needs more than 4 slots, and with one player at most 5 of the 8 are in use from a single zone. Only two calls write an enemy back into its entry: `func_8002E350` (death) and `func_8002C448`, which runs from a script command (`func_8009F238`) or when the event code names that entry (`D_80165544`, `D_8013822C`). A slot itself is freed whenever its object is freed (`func_800277A4` → `func_80027F94` clears `+0x92`), which about 90 functions do, so whether enemies left behind stay in their slots is *not yet known*. If they do, the slots fill only when 3 or more are still alive as the player enters a 4-character zone (with fewer in the zone, more must be left over). An entry whose enemy is still alive is not made twice (`func_80034310`). A map change rebuilds the slots, and live enemies come back from the table on the next visit.
- **Story and Versus.** Stage init makes the enemy spawner only in Story. Versus has only players, and with 3 players the empty quarter gets a camera that follows player 0 (`func_800347F0`, `D_801BE490 = 1`). Versus draws its HUD per view with `func_800B4FD4(player)`; the Story HUD draws once for player 0. The Story bullet code takes its camera from view 0, where Versus uses the shooter's camera (`func_80039CEC`). The aim and lock-on searches go through all 8 slots. Versus for 4 players has team modes, so a team check probably exists somewhere *(not yet found)*.
- **Versus by player count.** 2-player Versus and 3- or 4-player Versus aren't the same mode with more views. With 3 or 4 players the game uses low-detail models in set colours and a much shorter character list (seen in play by the project's author, not yet traced in code); models 24-33 are probably those bodies (see [Characters > Model ids](characters.md#model-ids)). The HUD also changes: with 3 or 4 players the magazine is drawn at half size and each part sits in its quarter ([Rendering > Story and Versus](rendering.md#story-and-versus)). Other cut-downs for 3 or 4 players may exist. Findings about Versus should say which player count they hold for.
- **Player update.** `func_80058360` is each player's update. It runs the attract-demo timer (`D_801390D4`), then: while `D_8010EDE4` is set in Story, `func_800CB660` (the event script moves the player); otherwise `func_80059E5C` (normal control) when `D_8016A41C & 1`, else `func_8009F238`. `D_8010EDE4` was 1 during the scripted scene near the start of stage 1 and 0 again when it ended (scripted run, 2026-11-08).
- **Menus from the game.** `func_8007F708(kind, sub)` opens a menu or message screen (`D_8010C26A` = kind) and sets `D_8016A41C` to `0x0102`, then `0x0202`. Kind 10 is opened by `func_800613C0`, a character action, when both of its clips end (`+0xF4 & 0xC`) *(what screen kind 10 is hasn't been seen: in the run above it showed a black screen and never closed)*.
