# Animations

How the game stores and plays character animations, and which ones it never plays. Everything here comes from the USA ROM's code and data unless it's marked *(inferred)*. [`tools/animations.py`](../tools/animations.py) reads all of it from your own ROM.

## Clips

There are **2387 clips**, numbered from 1, holding 84,786 frames. Each has an entry in two tables in the [asset file](characters.md#asset-file) at ROM `0xF87B0`:

| Table | Asset file offset | Pointer | Holds |
|---|---|---|---|
| Headers | `+0xA8D0` | `D_80165540` | An offset within the asset file for each clip's header |
| ROM offsets | `+0xCE1C` | `D_80165E64` | Each clip's offset from ROM `0x53F990`, in increasing order |

Clip `n` uses entry `n - 1`. The clip data ends `0x2FE9A8` bytes after `0x53F990`.

### Header

A `u32`, followed by its events:

| Bits | Meaning |
|---|---|
| 30-31 | [Skeleton type](characters.md#skeleton) the clip was made for. 2034 clips use type 0, 218 use type 1 and 135 use type 2. |
| 16-29 | Number of events |
| 0-15 | Length in frames (also read at `0x8006ADC4`) |

Each event is a `u32`. Those with the top bit set are skipped. The others are stored at `obj+0x1772` for the lower body and `obj+0x1784` for the upper body, as three values: bits 28-30, bits 16-27 and bits 0-15. They look like sounds timed to the clip *(inferred)*.

### Data

| Offset | Holds |
|---|---|
| `0x00` | `u16[60]`: where each track's keys start, from the start of the clip |
| `0x78` | `u8[60]`: how many keys each track has |
| `0xB4` | Keys |

A key is a `u32`, then 0, 1 or 2 floats (`func_80058274`):

| Bits | Meaning |
|---|---|
| 31 | Two tangents follow, in and out |
| 30 | No tangents, both are 0 |
| 29 | The value is negative |
| 16-28 | Time in frames |
| 14-15 | Exponent `e` |
| 0-13 | Value, multiplied by `0.1` a total of `e + 1` times |

With neither bit 31 nor bit 30 set, one tangent follows and is used for both. Between keys the value follows a Hermite curve, with tangents scaled by 1/30 (`func_80057FB4`).

### Tracks

Tracks 0-29 are the lower half of the clip and 30-59 the upper half. Each half is loaded by itself and has its own clip number and clock, so a character's legs and upper body can play different clips. A half can be at most `0x1388` bytes, or the game prints an error instead of loading it. Each character has a `0x2710`-byte buffer at `0x8020EB00`, with the upper half at `+0x1388`.

Track values go to `obj+0xD28 + track * 4`, and `func_80069D44` builds the body parts from them. The meanings below are our reading of the code and the values *(inferred)*:

| Tracks | Value |
|---|---|
| 0-2, 30-32 | Whole-body rotation |
| 3-5, 33-35 | Whole-body position, with height in 4 and 34. Differences between frames move the character through the world (`func_80068104`), so clips carry their own travel. |
| 18-20, 27-29 | Foot positions |
| 48-50, 57-59 | Hand positions |
| The rest | Joint rotations in radians, and hip and chest offsets |

## Playing a clip

`obj+0x16E2` (lower body) and `obj+0x16E0` (upper body) are requests. `func_800532CC` runs for each character every frame. If a request isn't 0, it starts that clip, copies the number to `obj+0x16E6` or `obj+0x16E4` as the current clip, and clears the request. The clocks are `obj+0x16CC` and `obj+0x16C8`, in frames.

The numbers come from three places.

- **Code:** about 200 constants written directly.
- **Tables** in the game's data, mostly between `0x80105430` and `0x80105B84`. For example, `D_80105430[D_80105C70[weapon]]` is the standing clip for the weapon's class, with 16 classes per row. Others are chosen by model (`D_801053E2`) or direction.
- **Event scripts:** opcode 2's first two arguments are the actor and the clip (handler `0x8009AC84`), and it appears 2719 times. Opcode 36's fifth argument is also a clip. Actor 255 is the player *(inferred)*.

## Unused clips

**612 clips, or 19,983 frames (24% of the total), are named by nothing in the game.** `animations.py <rom> unused` prints the list.

### How this was decided

1. Every instruction that stores to `0x16E0` or `0x16E2` (411 of them) was traced back through registers, the stack, function arguments and return values to where its value comes from. This gave the constants and the tables, and led to the two script opcodes above.
2. A clip counts as used if a constant, **any** entry in those tables or any script command names it.
3. The game was run with a test mod that logged every clip started, through mission 1 and stages 5, 12, 20 and 26. It saw 105 different clips, and none were on the unused list. That only tests a small part of the game, so it can't prove the list on its own.

The test is generous, so the true number of clips never played is **higher**. A table entry the game never looks up, or a script event that can't run, still counts as used. For example, no table column has been checked for whether its weapon class ever does that action.

### Do they really play?

Yes. A test mod forced clips 1474, 149, 1833, 2209 and 1687 onto Jean-Luc in mission 1. He held the right poses with his real model: mid-roll, upside down in a flip, and so on. Nothing in them is broken, and no change to the engine was needed.

### What's in them

The names below are ours, from watching the figures. The game has no names for clips. Directions assume a clip's +Z is forward *(inferred)*.

| Clips | Skeleton | What they show | Status |
|---|---|---|---|
| 14-17, 103-105, 1376-1379, 1409-1411, 1445-1448, 1520-1523, 1552-1555, 1580-1583 | 2, 0 | **Evasive hops.** The character leaps 180-220 units from standing and lands standing, with both feet off the ground. Each group holds a set of directions: forward, back, left and right. All take 33-40 frames, and most have one event, perhaps a landing sound *(inferred)*. Every clip we measured starts and ends at the same height. | **Confirmed** unused |
| 1855-1858, 2031-2034 | 1 | The same hops for the type 1 skeleton | **Confirmed** unused |
| 1473, 1474 | 0 | **Side roll** from standing, one clip each way, ending crouched. The body turns over completely. | **Confirmed** unused |
| 1492, 1493, 1865, 1866 | 0, 1 | **Side roll** from standing back to standing | **Confirmed** unused |
| 1253, 2194 | 0 | **Backward roll** from a crouch, back to a crouch. The game's own crouching rolls to the sides (such as 1272 and 1276) are used, and these are the same kind of move in a direction the game doesn't use. | **Confirmed** unused |
| 149, 1882 | 0, 1 | **Somersault**, from a crouch to a crouch. The feet rise about 200 units over a short distance. | **Confirmed** unused |
| 1833 | 0 | **Lunge:** a long step forward with the body low, then back to standing | **Confirmed** unused |
| 2209 | 0 | Knocked into the air from a crouch, travelling about 360 units, and landing in a heap | **Confirmed** unused |
| 2165 | 0 | Raises the gun with one arm while climbing about 80 units. Possibly a climb onto something. | **Confirmed** unused |
| 998, 999 | 0 | A long run or charge of about 630 units with a hop in it | **Confirmed** unused |
| 1830, 1831 | 0 | A leap about 600 units forward that ends crouching, and a recovery | **Confirmed** unused |
| 1093, 1516, 1372, 1679, 1686, 1765, 8 and others | Mixed | **Death falls** that aren't otherwise in the game | **Confirmed** unused |
| 462, 836, 1687 and others | 0 | **Getting up** from crouching or lying | **Confirmed** unused |
| 44-52, 232-265, 1896-1906 | Mixed | **Long drops.** These fall 100 to 500 units in steps of 100, with sets like 47-52. A few of the same family are used, such as 46, so these may be heights no map needs *(inferred)*. | **Confirmed** unused |

Of the rest:

- About 86 are nearly identical to a used clip, usually its neighbour. In a run from 1154 to 1186 and another from 1290 to 1321, every other clip is unused and differs only slightly from the one before it. These are likely alternatives that were replaced *(inferred)*.
- About 50 hold a single pose.
- The rest are standing actions for other weapons and characters, which haven't been looked at individually.

### What this says about the game

The hops and rolls are the strongest result. They form complete sets, with every direction, for several weapon classes and for two other skeletons. So this looks like a designed evasive move, built for many characters, that was removed *(inferred)*. This fits the report of unused jump and dodge animations. Whether it was meant for the player or for enemies isn't known.

### Still open

- Who each group of clips belongs to. Table columns follow weapon class, but no column has been matched to a weapon yet.
- Whether used clips can actually be reached, which would add to the unused list.
- What the event values mean.
- Other animated things in the game, if any, don't use these tables and haven't been looked at.

## Looking at them

```
python tools/animations.py <rom.z64> viewer output/animations.html
```

This builds a page that plays every clip as a stick figure, with filters for unused clips, type of motion and skeleton. The motion labels are rough guesses made by a simple test, so "standing" also covers a lot of arm movement. It takes about 10 minutes to build. It's made from the ROM, so it must never be committed or shared.

```
python tools/animations.py <rom.z64> sheet out.png 1474 149
```

This draws each clip in the order given as a row of eight poses, with the same warning.
