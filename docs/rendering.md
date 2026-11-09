# Rendering

## Microcode

The game uses F3DEX2 and L3DEX2 2.08 for graphics. The audio microcode in use is at ROM `0xDAD50`, size `0xC60`. The copy at `0xD9F30` is unused.

## Framebuffer

The game clears and draws only `(14,14)-(305,229)` of its 320x240 framebuffer and leaves the border black for a TV's overscan to hide. That leaves 292x216 visible pixels. The area beyond 4:3 is never cleared.

Scissors seen in a `WINBACK_DLDUMP` log of the intro and attract mode: a full-screen `(0,0)-(319,239)` every frame (the laser sight is drawn under it), `(14,14)-(306,230)` for the 3D and the clears, and `(14,28)-(306,212)` (inferred to be the cutscene letterbox, not confirmed).

## Frame structure

Each frame is drawn with two tasks: the scene, then the laser sight.

`func_80025F10` builds both. For each view it calls `func_80026A10(dl, view, layout, aspect, passes)`, which sets the scissor, the projection and camera (`func_800262FC`) and then draws every object whose pass bits (halfword at `obj+0x36`) match `passes` (`func_800280C4`). The scene task uses passes `0x36F`, the laser task `0x80`. Objects are created by `func_80027470`; `obj+0x24` is their update function and `obj+0x28` their draw function.

The layout depends on `D_8016A40E` and `D_8016A41C` *(inferred to be the versus mode's split screen, not confirmed in play)*:

| Condition | Views | Aspect passed |
|---|---|---|
| `D_8016A40E & 1`, or `D_8016A41C & 0x600` | 1 | 4:3 |
| otherwise `D_8016A40E & 2` | 2 | 8:3 each |
| otherwise | 4 | 4:3 each |

## Projection

`func_800262FC` calls `guPerspective` with one of three cameras:

- **Normal play** (`D_8016A41C & 0x100` and `D_8010EDE4 == 0`): field of view `D_80103758`, copied from `D_80103754` (50°, changed by the camera code) when the camera is placed (`func_80026760`). Near 10, far 5500, or 10000 when `func_8003F53C` returns non-zero.
- **`D_8010EDE4 != 0`, or the attract demo** (`D_8016A41C & 0x800`): field of view `D_8010375C` (35° in the ROM, set by `func_8009E1E0` and `func_800A09C8`), near 12, far 5500, with its own eye and target arrays (`D_8013A730`, `D_801BF9C0`, `D_80144E08` and `D_80188C48`, `D_8015D278`, `D_801CC620`). `D_8010EDE4` is written by event-script code (`func_8009E1E0`), and it was 1 exactly while the scripted scene near the start of stage 1 played (scripted run, 2026-11-08), so it marks a scripted camera. That the 35° field of view is used then is from the code, not measured.
- **Otherwise** (menus): 50°, near 12, far 5500, with the camera at the origin.

The camera for view `n` looks from (`D_8015D6D8[n]`, `D_801B0CE8[n]`, `D_80178FB0[n]`) at (`D_80158748[n]`, `D_8015D268[n]`, `D_801C3808[n]`).

## View test

`func_80028BB4(pos, radius)` returns whether an object can be seen, and about 20 object types skip drawing when it returns 0. It works only in the horizontal plane:

1. In normal play, anything further than 5000 from the camera is hidden.
2. The square `pos ± radius` (x and z) is tested against two lines through the camera, at its heading ± a half angle. If all four corners are outside either line, the object is hidden.
3. The half angle is `fov × π / 180 × 0.5 × k`, with `k = 1.21667` for a 4:3 view and `2.02778` for an 8:3 view (`D_8016A40E & 2`). In normal play, 0.2 is added to `k` when the camera object's `+0xEC` is 6. In normal play the heading is the camera's `+0x10` plus π; otherwise it comes from the eye and target arrays.

For a 50° 4:3 view, the true horizontal half angle is 31.9° and the game uses 30.4°, relying on the radius for the margin. Since `k` is fixed, a wider picture shows objects being hidden at its sides.

## HUD

The gameplay HUD is one object (pass `0x100`) whose draw function, `func_800D20CC`, writes texture rectangles straight into the scene display list (`D_801D2C80`). It brackets them with two static display lists, `D_8010AF58` (setup) and `D_8010AF88` (closing), and sets no scissor, so it draws under the view's `(14,14)-(306,230)`. Everything goes through the sprite routines around `func_8007A754`.

`func_800D20CC` draws nothing unless `D_8016A40E & 1` is set. That bit is set in Story and clear in Versus, which has its own HUD (see [Story and Versus](#story-and-versus) below). A Story game with two players keeps it set, so this HUD still draws once over the whole screen. The parts in the table are skipped during the attract demo (`D_8016A41C & 0x800`) and while `D_8010EDE4` (scripted camera) is set:

| Call | Draws | Rectangles seen |
|---|---|---|
| `func_800CF6A8(0, 212, 214)` | LIFE and the player's health bar, from player `+0x176B` | `(194,214)-(292,221)` |
| `func_800CEC1C(0)` | Rounds left in the magazine. Not drawn in camera mode 9. | `(27,166)-(50,221)` |
| `func_800CF7E8()` | Weapon icon and ammo count. Not drawn in camera mode 9. | `(52,199)-(82,221)` |
| `func_800CFA9C()` | Sprite `D_80110668` at (276,28) and an animated one at (279,31), plus a sound (`func_800D34F4`). It turns on when one of the 84 objects at `D_801B2780` (0x240 bytes each) has `+0x92 == 2`, `+0x130 & 1`, `+0x120 >> 8 == 0x0A` and `+0x120 & 0x80`, is in player 0's room (`+0x8E`), and its flag byte `D_8015881E[+0x126]` doesn't have bit 4 set. Only shown while `D_801587C8` is set. *(What these objects are isn't known; they aren't the character slots. Not seen in play.)* | |
| `func_800CF76C()` | A second health bar at (40,22), while `D_801D362C` is set (see below) *(inferred to be a boss's, not seen in play)* | |
| `func_800D0B14(0)`, `func_800D0BE0(0)`, `func_800D0CCC(0)`, `func_800D0E54()` | Target markers, drawn by `func_800D0088` at an object's projected position (see below) *(not seen in play)* | |

Then, also during the demo and the scripted camera, `func_8007CBEC(dl, x1, y1, x2, y2, ...)` draws lines in `C0C0C0` at alpha `0x80`, depending on player 0's camera mode (`D_80179280[0] + 0xEC`, a halfword):

- Modes 6 and 8: the corners of a camera frame, 30 pixels long, at x 56 and 264 and y 48 and 192.
- Mode 9: a crosshair, with arms from x 56 to 86 and 234 to 264 at y 120, and from y 48 to 78 and 162 to 192 at x 160.

These are full-screen coordinates, so with two views they would cross both.

### What feeds the HUD

The HUD object's update function, `func_800D1E24`, does the per-frame work. Its creation (`func_800D23AC`) sets both draw and update. In Story (`D_8016A40E & 1`) it updates only player 0. In Versus it updates players 1 to `D_8016A4EE - 1` too.

- **Health bars** ease towards the real value. `D_801B1168` holds a shown value per entry (s16, ten times the health). Entry 0 is player 0. In Versus entries 1 to 3 are the other players. In Story entry 1 belongs to the second health bar: `func_800ADA40` stores a health in `D_801BE482` and an index in `D_801BE480` (which picks the bar's label from `D_8010F668`, 6 bytes each), and `func_800D24D4` copies `D_801BE482 × 10` into entry 1. `func_8002C86C` (the spawner's character maker) sets `D_801D362C = 1` and `D_801AADD8` to the new character when its `+0x92` is 2, which turns the bar on; stage init (`func_80034364`) clears it. What sets `+0x92` to 2 at that point hasn't been traced. *(Inferred to be a boss bar. Not seen in play.)* The bar doesn't read any character slot: its health is the global `D_801BE482`, which the boss's own code lowers and checks against per-boss thresholds (`func_800ADE7C`, `D_8010F66A`) and zeroes (`func_800AF368`). `D_801AADD8` is only checked for state `0xCE` (`+0x16EC`), which hides the bar. The "1" in entry 1 is the bar's row in the HUD's table, not character slot 1, so a second player in slot 1 doesn't touch it. The clash is only within the HUD table: `func_800CF6A8(1, …)` would read row 1, the boss bar's, for player 1's health. Rows 2 and 3 are written only by Versus with 3 or 4 players *(inferred from the writers: `func_800D1E24`'s Versus loop, `func_800B5944`, `func_800A1404`)*. `func_800CF6A8(player, x, y)` takes the player's health from `D_801390C0[player] + 0x176B` and the shown value from entry `player`.
- **Magazine.** `func_800CEC1C(player)` reads per-player HUD state at `D_8011FB80 + player × 0x2C`.
- **Weapon and ammo count.** `func_800CF7E8` reads player 0's weapon (`D_801390C0[0] + 0x1758`) and two counts at `D_801587C0` and `D_801587C1`, which are in the progress block (player 0's).
- **Target markers.** Each of the four marker kinds has a table with a part per player, and an update function that picks the object to mark:

| Table | Draw (colour) | Update | Object marked | Players |
|---|---|---|---|---|
| `D_801109EC` | `func_800D0B14` (00 FF 28, green) | `func_800D0B44` | The player camera's target (`D_80179280[p] + 0x164`) | Each |
| `D_80110AF8` | `func_800D0BE0` | `func_800D0C10` | `D_80138EF8[p]`, while the player has `+0xF8 & 0x80000` (inferred: aiming) | Each |
| `D_80110C04` | `func_800D0CCC` | `func_800D0CF8` | `D_80188C38[p]` *(not identified)* | Each |
| `D_80110D10` | `func_800D0E54` (00 DE FF) | `func_800D0E88` | `D_801CC6F8`, one object for the whole game *(not identified)* | Player 0, Story only |

### Story and Versus

Versus draws each view's HUD with `func_800B4FD4(player)`, called from `func_800B5400`. Compared with the Story HUD:

| Part | Story (`func_800D20CC`) | Versus (`func_800B4FD4(p)`) |
|---|---|---|
| Health bar | Player 0 | Each player, in their own view |
| Magazine | Player 0 | Each player |
| Weapon icon and ammo count | Player 0 | Not drawn |
| Indicator at (276,28) | Player 0's room | Not drawn |
| Second (boss) health bar | Uses shown-health entry 1 | Not drawn (entry 1 is player 1's health bar) |
| Target markers 1-3 | Player 0 | Each player |
| Target marker 4 | Player 0 | Not drawn |
| Camera frame, crosshair | Player 0's camera mode, full-screen coordinates | Not drawn |
| Rule counters, timer | None | Per view, depending on the match settings (`D_8016A495`, `D_8016A4C1`, `D_8016A4A5`, `D_8016A4B9`, `D_801A8C70`) *(not looked at one by one)* |

The Versus HUD changes with the number of players (`D_8016A4EE`). With 1 or 2 the magazine is full size and the health bar is at (212, 109 + 109 × p), at the bottom right of each half. With 3 or 4 the magazine is drawn at half size, and the health bar is at (70 + 148 × (p mod 2), 109 + 109 × (p div 2)), so each part sits in its quarter.

## Frame timing

The game doesn't wait for the RSP before starting its next update, and characters are drawn directly from live memory rather than from a copy for the frame: part matrices at `obj+0x1008` and joint vertices at `D_801CC710`. In a recompilation where the renderer reads a task on another thread with no delay, that memory changed during about a quarter of scene tasks. How often this overlap happens on real hardware hasn't been measured.

## Laser sight

The laser uses L3DEX2 `G_LINE3D` (handler at IMEM `0x1618`). The line is a screen-space primitive whose width is `(w0 & 0xFF) + 3` quarter-pixels on each side: horizontal for steep lines, vertical with square ends for shallow ones. Lines ignore culling, and L3DEX2 TRI1/TRI2 draw wireframes.

It uses a dithered alpha compare (`G_AC_DITHER`) and is the first draw of its own task.

The functions that write `G_LINE3D` (`0x08000200` with the two vertices loaded just before). All but `func_8008DBE8` are object draw functions (`obj+0x28`); which pass each object uses wasn't checked:

| Function | Line | Notes |
|---|---|---|
| `func_80047498` | A character's laser sight, `obj+0x0` to `obj+0x78` | Update `func_80046E84` |
| `func_800D5884` | A map object's beam, from its parent's position to the parent's `obj+0x78` | Created with its parent by `func_800D49A0` (parent draw `func_800D500C`, update `func_800D5094`). Hidden while flag bit 5 of `D_8015881E[parent+0x126]` is clear, beyond a distance (`D_8011B950`) from the player and, in a single view, when `parent+0x8E` isn't the current area. No on-screen test. *Inferred to be the environmental lasers, not confirmed.* |
| `func_80029464` | A shot's tracer, `obj+0x0` to `obj+0x78` | Created with update `func_80029260` |
| `func_800C2588` | A short falling vertical line | Update `func_800C249C` |
| `func_800845CC` | 7 lines through 14 points | Update `func_800843F0` (scattered pieces) |
| `func_8008DBE8` | Many coloured lines | Not identified |

## Sky

The game writes a 16-byte `G_TEXRECT` before the sky cloud plane to load TMEM. In F3DEX2, `G_TEXRECT` only stores its words and `G_RDPHALF_2` issues the rectangle, so this draws nothing on real hardware.
