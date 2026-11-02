# Camera

The player camera is the object at `obj+0x2C` in `func_80035970` (input) and `func_800390EC` (placement).

| Offset | Contents |
|---|---|
| `+0x0` | Position |
| `+0x18` | Controller number |
| `+0x28` | The point it looks at (the player) |
| `+0x10C` | Height |
| `+0x110` | Turn speed, in radians per frame |
| `+0x132` | Flags |
| `+0x154` | Tilt (pitch) |

## Turning

Holding C-Left/C-Right adds 1° per frame to `+0x110` while it is below 6°, and it falls by 0.5° per frame towards zero. `func_800390EC` adds it, with other short-lived offsets (`+0x11C`, `+0x150`, `+0x158`, `+0x168`, `+0x16C`), to the current angle around the player.

## Height and tilt

The camera sits `+0x10C` above a pivot at 0.8 × `+0x10C` above the player. `+0x154` is applied after the turn, and it only changes the camera's height: the horizontal distance stays the same.

The game sets the tilt itself (`func_80036CD8`, at most 2° per frame and limited to ±0.3 rad) and sets flag 0x10 to keep it. Without flags 0x10 and 0x400 it shrinks by ×0.8 each frame.
