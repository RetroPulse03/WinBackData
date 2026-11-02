# Rendering

## Microcode

The game uses F3DEX2 and L3DEX2 2.08 for graphics. The audio microcode in use is at ROM `0xDAD50`, size `0xC60`. The copy at `0xD9F30` is unused.

## Framebuffer

The game clears and draws only `(14,14)-(305,229)` of its 320x240 framebuffer and leaves the border black for a TV's overscan to hide. That leaves 292x216 visible pixels. The area beyond 4:3 is never cleared.

## Frame structure

Each frame is drawn with two tasks: the scene, then the laser sight.

## Laser sight

The laser uses L3DEX2 `G_LINE3D` (handler at IMEM `0x1618`). The line is a screen-space primitive whose width is `(w0 & 0xFF) + 3` quarter-pixels on each side: horizontal for steep lines, vertical with square ends for shallow ones. Lines ignore culling, and L3DEX2 TRI1/TRI2 draw wireframes.

It uses a dithered alpha compare (`G_AC_DITHER`) and is the first draw of its own task.

## Sky

The game writes a 16-byte `G_TEXRECT` before the sky cloud plane to load TMEM. In F3DEX2, `G_TEXRECT` only stores its words and `G_RDPHALF_2` issues the rectangle, so this draws nothing on real hardware.
