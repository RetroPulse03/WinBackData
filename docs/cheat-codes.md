# Cheat codes and unlocks

Everything here comes from the USA ROM's code and data unless it says otherwise. [`tools/event_scripts.py`](../tools/event_scripts.py) prints the code table and the event scripts from your own ROM.

Status words used on this page:

- **Tested:** the code was entered in a scripted run of [WinBack Recompiled](https://github.com/RetroPulse03/WinBackRecomp) and the game's memory or picture changed as described.
- **Code:** read from the game's code, not run.
- *(inferred)*: a conclusion that the code doesn't state outright.

## Button codes

The game has **exactly six** codes. They are in a table of six pointers at `D_8010DCB0`, and the matching loop in `func_800904E4` stops at six. The developers' debug messages name five of them (`D_80118C8C` onward); Big Head has no message.

| # | Name in the ROM | Buttons | Effect | Status |
|---|---|---|---|---|
| 0 | `L BUTTON RECOVERY` | L, C-Up + C-Left, C-Down + C-Right, C-Left + C-Right, C-Up + C-Down, C-Left + C-Right, then hold L and press Start | Holding L in play sets health to 100 | Tested: code accepted (`D_8010DC7C = 1`). Healing is Code. |
| 1 | `ALL CHARACTER` | Up, Down, Down, Right, Right, Right, Left, Left, Left, Left, then hold C-Up and press Start | Sets the 20 character flags `0x40`-`0x53` | Tested: `D_8015D410 = 0x000FFFFF` |
| 2 | `TRIAL` | The same directions, then hold C-Down and press Start | Unlocks Trial mode (flag `0x5D`) | Tested: `D_8015D410 = 0x20000000` |
| 3 | `MAX POWER` | L, C-Right, C-Left, C-Right, C-Left, C-Down, C-Up, C-Down, C-Up, then hold L and press Start | Unlocks Max Power mode (flag `0x60`) | Tested: `D_8015D414 = 1` |
| 4 | `SUDDEN DEATH` | C-Left, C-Right, C-Left, C-Right, C-Up, C-Down, C-Up, C-Down, then hold L and press Start | Unlocks Sudden Death mode (flag `0x5F`) | Tested: `D_8015D410 = 0x80000000` |
| 5 | None | R, L, R, L, R, R, R, L, Start | Draws heads twice as large | Tested: visible in play (`D_8010DCCC = 1`) |

### Entering a code

The codes are read on the "Press Start" screen (front-end state `0x0A`), from controller 1 only.

- **Time limit:** the screen's timer `D_8010DBEC` moves on to the attract demo at 300, which also clears all progress through the codes.
- **Chords** don't need to be pressed on the same frame. A step counts once all of its buttons have been held together and then released. Pressing a button that isn't part of the step starts that code over.
- **The last step** is only checked when Start or A is pressed, and only Start can complete a step that includes Start.
- **Several codes at once:** progress is tracked for each code separately, but Start leaves the screen, so one visit can only finish codes that end on the same press.

### The confirmation sound

`func_8008EFFC` plays the sound only if the code changed something (`$s2`). Entering a code that is already unlocked plays no sound, even though it was entered correctly. If `ALL CHARACTER` finds every character already unlocked, it is silent too.

### How long they last

| Codes | Stored in | Lasts |
|---|---|---|
| All Character, Trial, Max Power, Sudden Death | System flags, `D_8015D410` onward | As long as the system data is kept *(inferred: saved to the Controller Pak with the rest of it)* |
| L Button Recovery, Big Head | `D_8010DC7C`, `D_8010DCCC` | Until the power is turned off. Nothing in the game clears them. |

The codes are applied when the title moves on to state `0x0C`, which comes a couple of seconds after Start if the game checks the Controller Pak first.

L Button Recovery is ignored while `D_8010DD31` is `0xFF` *(inferred: no Controller Pak slot in use)*. Its effect in `func_800588FC` only runs when bit `0x01` of `D_8016A40E` is set, which means one player (see [Rendering > HUD](rendering.md#hud)). It works while L is held, so it makes you very hard to kill rather than healing once.

Big Head is in `func_80057100`'s drawing loop: part 9 of every character gets a scale of 2. It applies to everyone drawn, not only the player.

## Codes that aren't in the game

These were tested in the same way and did nothing, and neither sequence is in the code table.

| Claim | Source | Result |
|---|---|---|
| "Max Power Trial Mode": Up, C-Right x2, C-Left, Z x2, hold L and press Z | AbsolutCheats | **Not a code.** A press of Z can't end a code at all. |
| Down, Up x2, Down x3, C-Left, C-Up, hold C-Up and press Start | Cheating Dome | **Not a code** |
| Max Power beginning with Left instead of L | A 2021 walkthrough | **Typo confirmed.** Doesn't work. |
| All characters with C-Down instead of C-Up | A 2021 walkthrough | **Typo confirmed.** That sequence is Trial. |

## Game modes

`D_8016A40E` holds the mode bits. The difficulty label comes from `func_800D6AFC`.

| Bit | Mode | What the code shows |
|---|---|---|
| `0x10` | Trial | Shows `TOTAL BEST POINTS` on the stage results |
| `0x20` | Sudden Death | Labelled `SUDDEN`. Sets `D_801BE482` to 0 in `func_800AF368`, and clears timers in `func_8002A570`, `func_80064BD0` and `func_800652C0`. |
| `0x40` | Max Power | Labelled `EASY/M`, `NORMAL/M` or `HARD/M`. Ammunition isn't spent (`func_8005FA70`), and `func_800A8ED0` skips adding picked-up ammunition. |

Not yet confirmed:

- **Sudden Death:** "one-hit kills for everyone" is the usual description, but the code that applies damage hasn't been followed far enough to confirm it.
- **Max Power:** "all weapons" has not been traced. Only the unlimited ammunition has.

## Modes unlocked by playing

All of this is decided on the `MISSION COMPLETE` screen, `func_800DF0AC`. The total score `D_801587DC` must not be 0, and none of the mode bits `0x70` may be set, so finishing Trial, Max Power or Sudden Death earns none of these.

| Unlock | Requirement | Message |
|---|---|---|
| Trial | Finish on any difficulty | `YOU MAY NOW USE TRIAL MODE!` |
| Max Power | Normal or Hard, with a total score of 20,000 or more | `YOU MAY NOW USE MAX POWER MODE!` |
| Sudden Death | Hard, with the game clock under 5 hours | `YOU MAY NOW USE SUDDEN DEATH MODE!` |
| Hidden characters | See below. Requires no missile strikes. | `YOU MAY NOW USE HIDDEN CHARACTERS!` |

This settles the conflict between sources:

- Beating Hard does **not** unlock all three at once by itself, though a fast Hard game with 20,000 points does earn all three.
- Trial does **not** depend on the ending. The ending isn't checked for it.
- Sudden Death does **not** check for the Good Ending. It checks only the clock, and the clock limit is a separate 5-hour test from the one that decides the ending.

## Versus characters

The list is at `0x801129E4`, and `func_800B4574` and `func_800E04E0` decide who can be chosen. Jean-Luc's team, the first 10 entries, is always available.

### Unlocked by clearing the game

The game must end with no missile strikes (`D_801587EE = 0`). `D_80112AF4` holds the last flag for each difficulty, and each one includes the ones before it.

| Difficulty | Flags | Characters |
|---|---|---|
| Easy | `0x4A`-`0x4D` | Terrorist 1, 2 and 3, Engineer |
| Normal | Also `0x4E`-`0x51` | George, Kevin, Nancy, Kenneth |
| Hard | Also `0x52`-`0x53` | Lisa and Steve, in games for 3 or more players |

The Hard row is **new**: none of the guides we checked list it. With anything other than 2 players (`D_8016A4EE`), the character screen uses the short list of 6 names, and two of them are locked behind flags that only clearing Hard or `ALL CHARACTER` can set.

### Unlocked by score

`func_800DE38C` works out `(score - 11000) / 2000` and unlocks that many characters in list order. It runs on stage results, using the total score.

| Score | Character | Flag | | Score | Character | Flag |
|---|---|---|---|---|---|---|
| 13,000 | Lila | `0x40` | | 23,000 | Gunt | `0x45` |
| 15,000 | Leon | `0x41` | | 25,000 | Banderas | `0x46` |
| 17,000 | Ryan | `0x42` | | 27,000 | Jin | `0x47` |
| 19,000 | Thunder | `0x43` | | 29,000 | Deathmask (`ASH` in the ROM *(inferred)*) | `0x48` |
| 21,000 | Duke | `0x44` | | 31,000 | Cecile | `0x49` |

The formula has no upper limit, so a score of 33,000 or more goes on to the Easy unlocks in the same order: Terrorist 1 at 33,000, and so on *(from the code, not tested in play)*.

## Endings

The N64 version records **three outcomes**, but they use **two routes**. The sources that said "two endings" and "three endings" were each partly right. The time limits usually quoted, however, don't match the ROM.

### The game clock

`D_8010DD60` counts up during play. It was measured at 30 counts per second (152 in 5 seconds), and event scripts compare it in minutes. It is the clock on the results screen, and it is saved with the game.

### The two flags

| Flag | Set by | Meaning *(inferred from the scene it plays)* |
|---|---|---|
| `0x80` | Map 44 (Stage 23), event 12: on entering with the clock at **5:00:00 or more**, if flags `0x28` and `0x29` are clear | First missile strike |
| `0x81` | Map 52 (Stage 27), event 56: flag `0x74` set and the clock at **6:00:00 or more** | Later strike |
| `0x81` | Map 52, event 50: flag `0x74` set and `0x80` already set, whatever the time | Later strike |

The usual guide figures are 3 hours at Stage 23 and 5 hours at Stage 27. The ROM says **5 hours and 6 hours**. Stage 23 and 27 themselves are right, taking map 44 and map 52 as those stages *(inferred from `D_8010D5F4`, counting from 1)*. Flag `0x74` is set partway through the game, and its exact place wasn't traced, so the "second checkpoint" detail can't be confirmed.

Map 61 also has two events (1 and 2) that set these flags when a button is pressed in certain trigger areas. These haven't been traced, and may be left over from testing *(inferred)*.

### The outcomes

`func_800DE3F8` turns the flags into `D_801587EE` at the end of the game.

| `D_801587EE` | Flags | Route on map 62 | Hidden characters awarded |
|---|---|---|---|
| 0 | Neither | Dan, then Cecile | Yes |
| 1 | `0x81` only | Dan, then Cecile. A different event plays after Dan's fight. | No |
| 2 | `0x80` | Cecile only, with a scene on map 52 if both flags are set | No |

The middle row is why a simple two-endings description falls short. It hasn't been played through, so what the player sees in it is known only from the scripts.

## Versus extras

These have **not been confirmed**, and are listed so they aren't lost. All come from a single source, AbsolutCheats.

| Claim | What the code shows |
|---|---|
| Thunder's flamethrower: R for the laser, then Reload | Thunder starts with his own weapon, 8. Several functions check for his model (`0x33`). The flamethrower itself wasn't found. |
| On Factory-1, everyone can use C-4 with Down | No code compares the map number with a Versus map, so if true it isn't a simple check of the map. |
| Jump off rails with A + B | Not looked at |
| A hidden animation after the demo cycles a few times | Not looked at |

## Sources for the claims

The claims above were collected from GameFAQs, GameSpot, The Cutting Room Floor, a 2021 N64 walkthrough, Nintendo64EVER, GamesRadar, AbsolutCheats, CheatCC, Cheating Dome and the Koei wiki. They were checked against the ROM as summarised for us; the pages themselves weren't all read.
