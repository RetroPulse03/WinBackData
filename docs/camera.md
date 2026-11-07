# Camera

The player camera is the object at `obj+0x2C` in `func_80035970` (input) and `func_800390EC` (placement).

| Offset | Contents |
|---|---|
| `+0x0` | Position |
| `+0x10` | Direction it faces around the vertical axis. The player's movement is relative to this. |
| `+0x18` | Controller number |
| `+0x28` | The point it looks at (the player) |
| `+0x10C` | Height |
| `+0x110` | Turn speed, in radians per frame |
| `+0xEC` | Mode, an index into the update functions at `D_80103D80` |
| `+0x132` | Flags |
| `+0x154` | Tilt (pitch) |

A direction `a` points along `(sin a, 0, cos a)`, with `(-cos a, 0, sin a)` to its right. Y is up.

## Modes

| Mode | Function | Use |
|---|---|---|
| 0 | `func_80037BA8` | Normal |
| 1 | `func_80037C30` | Normal, with extra following while the player moves *(inferred)* |
| 2 | `func_80037DDC` | While the player's state is 10 |
| 3 | `func_80037F78` | Taking cover at a wall (player `+0xF4 & 0x100000`) *(inferred from a test run)* |
| 4-8 | `func_80038070` to `func_800385FC` | Not looked at yet, except that mode 6 was active in a pause taken at the first mission's security camera view, with `+0x164` set and the game state `0x0101` underneath *(one reading)*. `func_80038CB8` sets modes 6, 7 and 8 from the flags of the floor zone the player is in (`D_801D41D2 + 60 × player +0x8A`): with `0x200` set, `0x4000` gives 7, otherwise `0x4` gives 8, and otherwise 6. In modes 6 and 8 the HUD draws a camera frame's corners (see the rendering notes). |
| 9 | `func_80036830` | While the player's state is 25. The update stops early and doesn't hand over a view. |

## Handing the view to the renderer

`func_80034DBC` is the whole camera update. At its end it calls `func_80026760(x, y, z, controller)` for the eye and `func_800266D0(x, y, z, controller)` for the point looked at. The eye's height is `+0x4 + +0x10C` plus the shakes `+0x148`, `D_801791E0` and `D_801B04C8`, and the point's is `+0x2C + 0.8 × +0x10C + +0x148`. They are stored per controller: eye in `D_8015D6D8`, `D_801B0CE8`, `D_80178FB0` and point in `D_80158748`, `D_8015D268`, `D_801C3808`.

`func_800352E4` keeps the camera out of walls, using `func_80044160` (walls, from and to points) and `func_8004394C` (objects). `+0x2C` was 153 above the player's feet at the start of stage 2, while `+0x10C` stayed 0 *(height while crouching not checked)*.

## Player movement and aiming

`func_8005AAF8` turns the player: their heading (player `+0x64`) is the stick's direction rotated by the camera's `+0x10`, so pushing up runs the way the camera faces. `D_80179280[controller]` is the camera.

- The heading doesn't change while `+0x16F0` is 3 or 4, or while `+0xF8 & 0x100` is set.
- While `+0x16F0` is 2, `func_8005AAF8` limits a change of up to ±1.57 radians to 0.14 radians per frame *(from the code, not measured)*. It leaves larger changes unlimited, unless `+0xF4 & 0x40000`, `+0xF8 & 0x4000` or `+0xF4 & 0x100000` is set.
- Setting off from standing, `func_8005B01C` chooses a clip from the size of the turn, with limits at 0.39 and 1.18 radians. The caller then sets `+0x16F0` to 3 and puts the old heading back. In one scripted run, `+0x64` kept its old value for 10-15 frames and then changed in one step, while the player was already moving the new way. Reversing during a run did the same, with `+0xF4 & 0x400000` set. When the stick changed about 8 frames into a start, the player kept going the first way until about frame 15, then turned to the new direction at the normal limit. A tap of about 5 frames didn't start a run: the state stayed 0 and the heading turned by 0.86 radians on the spot *(one scripted run)*.
- In the same run, a 45 degree stick change while running took about 6 frames, which fits the 0.14 limit, and the run covered about 12 units per frame in the open. The game ran at 30 frames per second (two graphics tasks per frame).

`func_800AD6BC` fills `D_801659C0[controller]`: `+0` is stick X and `+4` stick Y. It negates Y unless option bit `D_8015D6AC[controller] & 1` is set and player `+0xF4 & 0x80`. The bit was set in test runs, where pushing the stick up aims down *(which menu option sets it isn't known)*. Bit 1 of the same byte chooses which C button turns the view which way. `func_80035970` (the player camera update) makes C-Right raise the camera's turn speed `+0x110` and C-Left lower it, and swaps them when the bit is set (`$t1`/`$t2` at 0x80035B04, reading the byte for player `+0x90`). A positive speed turns the view left, so with the bit set C-Left looks left and C-Right looks right *(scripted runs: screenshots, and the player's movement with the stick held left)*. `func_80092EF8` sets the byte to 0x17, so the bit is set by default; it was set in both saves tried (0x17 and 0x16). `func_8008F318` sets it to 0x14 (bit clear) for the attract demo and `func_8008F350` puts the old value back.

`+0x16F0` is the movement phase: `func_8005AAF8` leaves the heading alone in phases 3 and 4, and `func_8005BFA4` (phase 2) starts a reversal through `func_8005C760` when the change is over π/2 *(from the code)*. Setting phase 2 straight away and zeroing `+0x118` before `func_8005B01C` made the player run off in the new direction at once, in scripted runs with the Modern scheme.

`D_80187FC0[controller * 8]` holds the N64 buttons for three actions: `+0` fire and action, `+2` reload and `+4` enemy lock *(names inferred from where they're read)*. `func_800AD8F0` fills them from bits 6-7 of `D_8015D6AC[controller]`.

Player state `+0x16EC` is 0 standing, 1 moving, 2 raising the weapon and 3 aiming *(from test runs)*. While aiming:

- The aim's direction is the heading plus a twist in `+0x158`. Stick right lowers it, by about 0.05 radians per frame at full deflection. At about ±1.57 it stops and the heading turns instead.
- The aim's height is `+0x154`, where positive is down, limited to about ±0.8 radians.
- `D_80138EF8[controller]` is the locked-on target, or 0.
- `func_80052600` moves the aim. Each frame's step is stick × sensitivity × band × π / 3600 radians. Sensitivity is bits 4-5 of `D_8015D6AC[controller]`: 0 gives 1.0, 2 gives 0.4, and 1 or 3 give 0.7. The band is 0.8 below a value of 33, 1.0 from 33 to 70, and 1.8 from 70 up, compared after sensitivity is applied. A full stick of about 80 at 0.7 gives the 0.05 radians above *(inferred)*.
- `func_8005C984` raises the weapon and sets `+0x174C` to 0. `func_80052600` ignores the stick until that reaches 10. `func_8005DC88` counts it up by one and sets it to 10 when the stick is centred. In one scripted run with the stick held throughout, the aim first moved 10-15 frames after state 3 began, later than counting from the raise would predict *(what starts the count isn't known)*.
- The state goes from 2 to 3 when `+0xF4 & 0x4` is set, probably when the raising clip ends *(inferred)*. That step calls `func_80058438`, which uses the heading to choose the target *(inferred)*, so a target is chosen from where the body faces.

## Weapon order

`func_80062AE8` switches to the next weapon in `+0x1758`, through the jump table at `0x80117720`: 0, 1, 2, then 3 if progress block `+0x6B` is set, then 20 if `+0x64` is set, then back to 0. Going to 20 sets `+0xF8 & 0x400` and leaving it clears the bit. Going to 3 takes the player out of cover. Weapon 0 shows infinite ammunition on screen.

`+0xF4 & 0x800` is set while crouching, and the camera's `+0x10C` then falls to -40 *(scripted run)*.

## Turning

Holding C-Left/C-Right adds 1° per frame to `+0x110` while it is below 6°, and it falls by 0.5° per frame towards zero. `func_800390EC` adds it, with other short-lived offsets (`+0x11C`, `+0x150`, `+0x158`, `+0x168`, `+0x16C`), to the current angle around the player.

## Height and tilt

The camera sits `+0x10C` above a pivot at 0.8 × `+0x10C` above the player. `+0x154` is applied after the turn, and it only changes the camera's height: the horizontal distance stays the same.

The game sets the tilt itself (`func_80036CD8`, at most 2° per frame and limited to ±0.3 rad) and sets flag 0x10 to keep it. Without flags 0x10 and 0x400 it shrinks by ×0.8 each frame.
