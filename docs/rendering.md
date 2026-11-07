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
- **`D_8010EDE4 != 0`, or the attract demo** (`D_8016A41C & 0x800`): field of view `D_8010375C` (35° in the ROM, set by `func_8009E1E0` and `func_800A09C8`), near 12, far 5500, with its own eye and target arrays (`D_8013A730`, `D_801BF9C0`, `D_80144E08` and `D_80188C48`, `D_8015D278`, `D_801CC620`). `D_8010EDE4` is written by event-script code (`func_8009E1E0`), so it is *inferred* to mark a scripted camera such as a cutscene. Not yet confirmed in play.
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

The parts are drawn only for a single view (`D_8016A40E & 1`), outside the attract demo (`D_8016A41C & 0x800`) and while `D_8010EDE4` is 0:

| Call | Draws | Rectangles seen |
|---|---|---|
| `func_800CF6A8(0, 212, 214)` | LIFE and the player's health bar, from player `+0x176B` | `(194,214)-(292,221)` |
| `func_800CEC1C()` | Rounds left in the magazine. Not drawn in camera mode 9. | `(27,166)-(50,221)` |
| `func_800CF7E8(0)` | Weapon icon and ammo count | `(52,199)-(82,221)` |
| `func_800CFA9C()` | Sprite `D_80110668` at (276,28) and an animated one at (279,31), with a colour that changes when an enemy in the player's room (`+0x8E`) is in a certain state *(inferred to be an alert indicator, not seen in play)* | |
| `func_800CF76C()` | A second health bar at (40,22), while `D_801D362C` is set *(not seen in play)* | |
| `func_800D0B14` to `func_800D0E54` | `func_800D0088` with the tables `D_801109EC`, `D_80110AF8`, `D_80110C04`, `D_80110D10`, which `func_800D0B44` and its neighbours fill from the projected position of a targeted object (camera `+0x164`, `D_80138EF8`) *(inferred to be target markers, not seen in play)* | |

Then, in any layout, `func_8007CBEC(dl, x1, y1, x2, y2, ...)` draws lines in `C0C0C0` at alpha `0x80`, depending on the player camera's mode (`D_80179280[0] + 0xEC`, a halfword):

- Modes 6 and 8: the corners of a camera frame, 30 pixels long, at x 56 and 264 and y 48 and 192.
- Mode 9: a crosshair, with arms from x 56 to 86 and 234 to 264 at y 120, and from y 48 to 78 and 162 to 192 at x 160.

## Frame timing

The game doesn't wait for the RSP before starting its next update, and characters are drawn directly from live memory rather than from a copy for the frame: part matrices at `obj+0x1008` and joint vertices at `D_801CC710`. In a recompilation where the renderer reads a task on another thread with no delay, that memory changed during about a quarter of scene tasks. How often this overlap happens on real hardware hasn't been measured.

## Laser sight

The laser uses L3DEX2 `G_LINE3D` (handler at IMEM `0x1618`). The line is a screen-space primitive whose width is `(w0 & 0xFF) + 3` quarter-pixels on each side: horizontal for steep lines, vertical with square ends for shallow ones. Lines ignore culling, and L3DEX2 TRI1/TRI2 draw wireframes.

It uses a dithered alpha compare (`G_AC_DITHER`) and is the first draw of its own task.

## Sky

The game writes a 16-byte `G_TEXRECT` before the sky cloud plane to load TMEM. In F3DEX2, `G_TEXRECT` only stores its words and `G_RDPHALF_2` issues the rectangle, so this draws nothing on real hardware.
