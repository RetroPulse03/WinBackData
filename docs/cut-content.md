# Cut content

Everything suspected or confirmed to be unused in the USA ROM, with its evidence. Nothing from the game is reproduced here. [`tools/event_scripts.py`](../tools/event_scripts.py) prints the scripts and dialogue from your own ROM.

| Status | Meaning |
|---|---|
| **Confirmed** | Nothing in the game can reach it, checked in both scripts and code |
| **Suspected** | The evidence points that way, but a route to it hasn't been ruled out |
| **Not cut** | Reported as unused, but the game does use it |
| **Unverified** | Reported elsewhere. We have found nothing for or against it yet. |

## How the search was done

Each result rests on one of these checks, and each has limits.

- **Dialogue:** a line counts as unused if no event script shows it (opcode 4) and no code asks for its file. Only `func_8009A500` and `func_8009A2FC` read dialogue. Their callers ask for file `0x26`, file `0x2B`, a file named by a script, and a variable in the Versus help screen *(inferred to be file 39)*.
- **Maps:** a script moves to a map with opcode 13. Doors have their own data, which hasn't been decoded, so "no script goes there" alone doesn't prove a map is unreachable.
- **Functions:** a function counts as unreferenced if no instruction or data word names it. Tail merging can hide real callers, so this is only a list of leads.

## Scenes and dialogue

| Item | Status | Evidence |
|---|---|---|
| **The Secretary of Defense's second scene.** Dialogue file 27, all 18 lines. After the finale, a message arrives from Dan, and the Secretary orders the army to storm the complex. | **Confirmed** | No script or code reads file 27. The characters speak elsewhere (files 0, 1, 25), so only this scene is missing. |
| **A reunion with Lisa and Jake.** Dialogue file 37, lines 0-14. Jean-Luc finds them alive, they joke, and he leaves to check on Tom. | **Confirmed** | Lines 15-23 of the same file are used, and lines 0-14 are not. It looks like the opening of the scene was removed *(inferred)*. |
| **Single lines:** 2.15, 6.1, 9.3, 16.7, 21.33, 24.7, 24.8 | **Confirmed** | No script shows them. 16.7 has Jean-Luc taking Steve's shotgun. 9.3 is teammates taking over from him. 24.7 and 24.8 extend the scene where the Colonel is killed. |
| **Credits entries:** 10 lines of file 40, covering five job titles and five names | **Suspected** | The credits script (event file 84) doesn't show them. Whether they were cut or simply replaced hasn't been checked against the credits as seen in play. |
| **Item and system messages:** lines of file 38 such as 38.0, 38.5 and 38.76-80 | **Suspected** | No script shows these 37 lines, but code reads file 38 too, with a line number it works out, so many are probably in use. Each needs checking. |

## An older version of the finale

**Event file 83** (map 82 in the numbering of event files) holds 13 events: a copy of the final scenes, using dialogue files 29-32. **Status: Confirmed.**

- Nothing loads it. No script moves to map 82, no code sets it as a map, and the only "load event file" command (opcode 38) loads file 84.
- It uses flags `0x2C` and `0x2D` where the finished game uses `0x80` and `0x81`.
- It moves to **map 19**, where the finished finale uses map 62. So the map numbers were different when it was written, and map 19 is now an ordinary map in the first half of the game. This is the clearest sign in the ROM that **the maps were renumbered or rearranged during development**.

### Leftovers in map 47 (Stage 25)

Map 47 has events 17, 19 and 21 that play missile strike scenes with the game clock at **2 hours and 4 hours**, setting flags `0x2C` and `0x2D`. **Status: Suspected.**

- These are the same flags as the old finale, and only that finale reads them, so they have no effect on the finished ending.
- Their scenes move to maps 31 and 18 where the same scene in map 44 moves to map 80, so they also use the old numbering.
- This suggests that the deadlines were once 2 and 4 hours at Stage 25 and moved to 5 and 6 hours at Stages 23 and 27 *(inferred)*.
- **Open question:** their conditions look reachable. If they can still run, a slow player would be sent to the wrong map. Test this by reaching map 47 with the clock past 2 hours.

## Maps

Maps 0-63 are the story, 64-71 are Versus for 2 players, 72-79 are Versus for more, 80 is the title and 81 is training. Versus reads its lists from `D_801129D0` and `D_801129DC`.

| Map | Status | Evidence |
|---|---|---|
| **74** | **Suspected**, likely the unused multiplayer map reported elsewhere | In neither Versus list. It alone uses area group 33 (`D_8010D5A0`), so it isn't a copy of another map. Its event file has one event. Not yet viewed. |
| **79** | **Suspected** | In neither Versus list, and has no events. It uses area group 27, the same as map 68, so it may be only a spare slot. |
| 12, 13, 15, 17, 22, 27, 41, 60, 63 | Not cut, as far as we can tell | No script moves to them, but stage starts or doors can (for example, map 63 is set directly at `0x80090EE0`). Listed only because the tool's `targets` command prints them. |

## Weapons

Value `0x1758` in a character holds their weapon. GameShark lists treat values 4-9 as hidden weapons, but `func_800937C4` shows that Versus hands out nearly all of them. The names in this table are the GameShark list's.

| Value | Name in GameShark lists | Who has it in Versus | Status |
|---|---|---|---|
| 4 | M16 | Terrorist 2 (model 3) | **Not cut.** It is only "new" in Jean-Luc's hands. |
| 5 | "New cooler handgun" | Jin, Terrorist 1, Kevin, Nancy, and model 25 *(inferred to be Dan's body for 3 or more players)* | **Not cut** |
| 6 | "Invisible gun 1" | Banderas, as both his weapons | **Not cut** |
| 7 | "Invisible gun 2" | Lila | **Not cut** |
| 8 | "Odd invisible shotgun" | Thunder | **Not cut** |
| 9 | "Cool rocket launcher" | Nobody | **Suspected** |
| 13 | None | Nobody | **Suspected** |

These weapons probably look invisible or odd because their models belong to other characters and aren't loaded for Jean-Luc *(inferred)*.

Weapon 9 has the same stats table entry as the rocket launcher (`D_8010D470`) and the same class (`D_80105C70`). Weapon 13 has a handgun's entry and a submachine gun's class. Nothing we found assigns either one, but values set from data, such as enemy spawn tables, haven't been checked. The other weapons are:

| Value | Owner |
|---|---|
| 0, 1, 2, 3 | Jean-Luc's handgun; submachine gun; shotgun; rocket launcher (Gunt) |
| 10, 11, 12 | Duke; Cecile; model 43 |
| 20 | Silenced handgun, set during play by `func_8005DC88` |

## Animations

**612 of the 2387 animation clips are named by nothing in the game. Status: Confirmed**, and the true number never played is higher. They include complete sets of evasive hops in four directions, side and backward rolls, a somersault, a lunge, death falls and long drops. This settles the report of unused jump and dodge animations from The Cutting Room Floor. Clips forced onto Jean-Luc in the game played correctly. See [Animations](animations.md#unused-clips) for the evidence and the list.

## Code

87 functions in the game's code have no reference we could find. This is a list of leads, not a result, as explained above. The clearest are:

| Function | What it does | Status |
|---|---|---|
| `func_8009959C` | Prints the state of every flag with `osSyncPrintf`. A debugging tool. | **Suspected** |
| `func_8008EA1C` | Turns the game clock into a value from 0 to 255, reaching the top at 120 minutes. Possibly a colour or level that changed with time. | **Suspected** |

The game also keeps many `osSyncPrintf` messages, such as `Jean BUSY!!` and `MUGEN LOOP`. They can't be seen on a normal console. The code uses NuSystem 2.05.

## Reported elsewhere, not yet checked

| Report | Source | Notes |
|---|---|---|
| Early, unfinished models of the S.C.A.T. team and Engineer, playable in Versus | The Cutting Room Floor | Might be models 24-33, which have one detail level. If so they aren't early or unused: they appear to be the bodies used in games for 3 or more players *(inferred; see [Characters](characters.md#model-ids))*. Models 59-61 share the Engineer's body but have no joint data, and are a better candidate. |
| An untextured multiplayer map | The Cutting Room Floor | Probably map 74, above |

## Still to look at

- Map 74 in the game, through a mod or a Level Select jump.
- The `CAPTURE` label next to `FIRE` and `RELOAD` at `0x8011BF80`, and whether `HELP` is reachable.
- Flags `0x5E` and `0x61`, the gaps in the system flags. Nothing we found sets or reads them.
- Any data that isn't reached by the ROM's tables, such as unused textures.
