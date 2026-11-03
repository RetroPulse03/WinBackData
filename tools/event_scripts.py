"""Reads the game's button codes and event scripts from your ROM.

Usage: event_scripts.py rom.z64 codes
       event_scripts.py rom.z64 flag NUMBER     events that read or set a flag
       event_scripts.py rom.z64 time            events that depend on the game clock
       event_scripts.py rom.z64 map NUMBER      all events of a map
       event_scripts.py rom.z64 unused          dialogue that no script shows
       event_scripts.py rom.z64 targets         maps no script moves to

Flags and maps are numbers, such as 128 or 0x80. See docs/game-state.md and
docs/cheat-codes.md for the formats.
"""
import struct
import sys

MAIN_ROM_TO_VRAM = 0x80024C00
EVENTS = 0x931470
DIALOGUE = 0x9264B0
OPCODES = 0x8010DF38 - MAIN_ROM_TO_VRAM
CODE_TABLE = 0x8010DCB0 - MAIN_ROM_TO_VRAM
CODE_NAMES = ["L BUTTON RECOVERY", "ALL CHARACTER", "TRIAL", "MAX POWER", "SUDDEN DEATH", "BIG HEAD"]
OPCODE_COUNT = 0x2C

OP_SHOW_LINE = 4
OP_SET_FLAG = 9
OP_CHANGE_MAP = 13
CONDITION_CLOCK = 4
CONDITION_FLAG = 5

BUTTONS = [
    (0x8000, "A"), (0x4000, "B"), (0x2000, "Z"), (0x1000, "Start"),
    (0x0800, "Up"), (0x0400, "Down"), (0x0200, "Left"), (0x0100, "Right"),
    (0x0020, "L"), (0x0010, "R"),
    (0x0008, "C-Up"), (0x0004, "C-Down"), (0x0002, "C-Left"), (0x0001, "C-Right"),
]


def u16(rom, offset):
    return struct.unpack_from(">H", rom, offset)[0]


def u32(rom, offset):
    return struct.unpack_from(">I", rom, offset)[0]


def codes(rom):
    for index, name in enumerate(CODE_NAMES):
        pointer = u32(rom, CODE_TABLE + index * 4) - MAIN_ROM_TO_VRAM
        steps = []
        while u16(rom, pointer):
            mask = u16(rom, pointer)
            steps.append(" + ".join(label for bit, label in BUTTONS if mask & bit))
            pointer += 2
        print(f"{index} {name}: " + ", ".join(steps))


def argument_sizes(rom, opcode):
    entry = OPCODES + opcode * 4
    count, wide = rom[entry + 1], u16(rom, entry + 2)
    return [2 if wide >> i & 1 else 1 for i in range(count)]


def read_events(rom, file):
    """Gives the events of an event file. Map m uses file m + 1."""
    base = EVENTS + u32(rom, EVENTS + 4 + file * 4)
    count, conditions, scripts = u16(rom, base), u16(rom, base + 2), u16(rom, base + 4)
    events = []
    for index in range(count):
        entry = base + 6 + index * 8
        number, _, condition, script = struct.unpack_from(">4H", rom, entry)

        offset = base + conditions + condition
        tests = []
        for _ in range(rom[offset]):
            tests.append((rom[offset + 1], u16(rom, offset + 2)))
            offset += 3

        offset = base + scripts + script
        commands = []
        total = u16(rom, offset)
        offset += 2
        for _ in range(total):
            opcode = rom[offset]
            offset += 1
            if opcode >= OPCODE_COUNT:
                raise ValueError(f"bad opcode {opcode} in file {file}, event {number}")
            arguments = []
            for size in argument_sizes(rom, opcode):
                arguments.append(u16(rom, offset) if size == 2 else rom[offset])
                offset += size
            commands.append((opcode, arguments))
        events.append((number, tests, commands))
    return events


def all_events(rom):
    for file in range(u32(rom, EVENTS)):
        for event in read_events(rom, file):
            yield file - 1, event


def line(rom, file, number):
    base = DIALOGUE + u32(rom, DIALOGUE + 4 + file * 4)
    start = base + u16(rom, base + 2 + number * 2)
    end = rom.index(0, start + 1)
    return rom[start], rom[start + 1:end].decode("latin-1").replace("\n", " ")


def describe(map_number, event):
    number, tests, commands = event
    print(f"map {map_number} event {number}")
    for kind, value in tests:
        if kind == CONDITION_FLAG:
            print(f"  if flag {value >> 8:#x} == {value & 0xFF}")
        elif kind == CONDITION_CLOCK:
            print(f"  if game clock >= {value} minutes")
        else:
            print(f"  condition {kind} {value:#x}")
    for opcode, arguments in commands:
        if opcode == OP_SHOW_LINE:
            speaker, text = line(rom_data, arguments[1], arguments[2])
            print(f"  line {arguments[1]}.{arguments[2]} (speaker {speaker}): {text}")
        elif opcode == OP_SET_FLAG:
            print(f"  set flag {arguments[0]:#x} = {arguments[1]}")
        elif opcode == OP_CHANGE_MAP:
            print(f"  go to map {arguments[0]}, entrance {arguments[1]}")


def unused(rom):
    shown = {(c[1][1], c[1][2]) for _, e in all_events(rom) for c in e[2] if c[0] == OP_SHOW_LINE}
    for file in range(u32(rom, DIALOGUE)):
        base = DIALOGUE + u32(rom, DIALOGUE + 4 + file * 4)
        for number in range(u16(rom, base)):
            if (file, number) not in shown:
                speaker, text = line(rom, file, number)
                print(f"{file}.{number} (speaker {speaker}): {text}")


def targets(rom):
    reached = {c[1][0] for _, e in all_events(rom) for c in e[2] if c[0] == OP_CHANGE_MAP}
    print(" ".join(str(m) for m in range(u32(rom, EVENTS) - 1) if m not in reached))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    global rom_data
    with open(sys.argv[1], "rb") as file:
        rom_data = file.read()
    command = sys.argv[2]
    if command == "codes":
        codes(rom_data)
    elif command == "unused":
        unused(rom_data)
    elif command == "targets":
        targets(rom_data)
    elif command == "map":
        wanted = int(sys.argv[3], 0)
        for event in read_events(rom_data, wanted + 1):
            describe(wanted, event)
    elif command == "flag":
        wanted = int(sys.argv[3], 0)
        for map_number, event in all_events(rom_data):
            reads = any(k == CONDITION_FLAG and v >> 8 == wanted for k, v in event[1])
            sets = any(c[0] == OP_SET_FLAG and c[1][0] == wanted for c in event[2])
            if reads or sets:
                describe(map_number, event)
    elif command == "time":
        for map_number, event in all_events(rom_data):
            if any(k == CONDITION_CLOCK for k, _ in event[1]):
                describe(map_number, event)


if __name__ == "__main__":
    main()
