"""A small MIPS interpreter that runs the game's own functions from your ROM.

Some data only exists once the game has computed it, such as the display lists
for character joints. Running the original code gets it exactly right, without
translating thousands of lines by hand. It has no hardware: functions that use
any have to be given a replacement through `stubs`.
"""
import math
import struct

MAIN_ROM = 0x1000
MAIN_ROM_END = 0xF87B0
MAIN_VRAM = 0x80025C00
RAM_SIZE = 0x800000
RETURN_ADDRESS = 0x80000000
STACK = 0x807FFF00
MASK = 0xFFFFFFFF


def signed(value):
    return value - 0x100000000 if value & 0x80000000 else value


def signed16(value):
    return value - 0x10000 if value & 0x8000 else value


class Cpu:
    def __init__(self, rom):
        self.rom = rom
        self.ram = bytearray(RAM_SIZE)
        self.put(MAIN_VRAM, rom[MAIN_ROM:MAIN_ROM_END])
        self.r = [0] * 32
        self.f = [0] * 32
        self.lo = self.hi = 0
        self.condition = False
        self.stubs = {}

    def offset(self, address):
        return (address & MASK) & (RAM_SIZE - 1)

    def put(self, address, data):
        start = self.offset(address)
        self.ram[start:start + len(data)] = data

    def get(self, address, size):
        start = self.offset(address)
        return bytes(self.ram[start:start + size])

    def u8(self, address):
        return self.ram[self.offset(address)]

    def u16(self, address):
        return struct.unpack_from(">H", self.ram, self.offset(address))[0]

    def u32(self, address):
        return struct.unpack_from(">I", self.ram, self.offset(address))[0]

    def w8(self, address, value):
        self.ram[self.offset(address)] = value & 0xFF

    def w16(self, address, value):
        struct.pack_into(">H", self.ram, self.offset(address), value & 0xFFFF)

    def w32(self, address, value):
        struct.pack_into(">I", self.ram, self.offset(address), value & MASK)

    def single(self, n):
        return struct.unpack(">f", struct.pack(">I", self.f[n]))[0]

    def set_single(self, n, value):
        self.f[n] = struct.unpack(">I", struct.pack(">f", value))[0]

    def double(self, n):
        return struct.unpack(">d", struct.pack(">II", self.f[n + 1], self.f[n]))[0]

    def set_double(self, n, value):
        self.f[n + 1], self.f[n] = struct.unpack(">II", struct.pack(">d", value))

    def call(self, function, *args):
        """Runs a function to its return and gives back $v0."""
        self.r = [0] * 32
        self.r[29] = STACK
        self.r[31] = RETURN_ADDRESS
        for i, arg in enumerate(args):
            self.r[4 + i] = arg & MASK
        pc = function
        next_pc = pc + 4
        while pc != RETURN_ADDRESS:
            pc, next_pc = self.step(pc, next_pc)
            self.r[0] = 0
        return self.r[2]

    def step(self, pc, next_pc):
        if pc in self.stubs:
            self.r[2] = (self.stubs[pc](self) or 0) & MASK
            target = self.r[31]
            return target, target + 4
        word = self.u32(pc)
        r = self.r
        op = word >> 26
        rs, rt, rd = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        shift = (word >> 6) & 31
        funct = word & 63
        imm = signed16(word & 0xFFFF)
        after = next_pc + 4

        def branch(taken, likely=False):
            if taken:
                return next_pc, (pc + 4 + (imm << 2)) & MASK
            if likely:
                return after, after + 4
            return next_pc, after

        if op == 0:
            if funct == 0: r[rd] = (r[rt] << shift) & MASK
            elif funct == 2: r[rd] = r[rt] >> shift
            elif funct == 3: r[rd] = (signed(r[rt]) >> shift) & MASK
            elif funct == 4: r[rd] = (r[rt] << (r[rs] & 31)) & MASK
            elif funct == 6: r[rd] = r[rt] >> (r[rs] & 31)
            elif funct == 7: r[rd] = (signed(r[rt]) >> (r[rs] & 31)) & MASK
            elif funct == 8: return next_pc, r[rs]
            elif funct == 9:
                r[rd] = after
                return next_pc, r[rs]
            elif funct == 16: r[rd] = self.hi
            elif funct == 18: r[rd] = self.lo
            elif funct in (24, 25):
                a, b = (signed(r[rs]), signed(r[rt])) if funct == 24 else (r[rs], r[rt])
                product = a * b
                self.lo, self.hi = product & MASK, (product >> 32) & MASK
            elif funct in (26, 27):
                a, b = (signed(r[rs]), signed(r[rt])) if funct == 26 else (r[rs], r[rt])
                if b:
                    quotient = int(a / b)
                    self.lo, self.hi = quotient & MASK, (a - quotient * b) & MASK
            elif funct in (32, 33): r[rd] = (r[rs] + r[rt]) & MASK
            elif funct in (34, 35): r[rd] = (r[rs] - r[rt]) & MASK
            elif funct == 36: r[rd] = r[rs] & r[rt]
            elif funct == 37: r[rd] = r[rs] | r[rt]
            elif funct == 38: r[rd] = r[rs] ^ r[rt]
            elif funct == 39: r[rd] = ~(r[rs] | r[rt]) & MASK
            elif funct == 42: r[rd] = int(signed(r[rs]) < signed(r[rt]))
            elif funct == 43: r[rd] = int(r[rs] < r[rt])
            else: raise NotImplementedError(f"{pc:08X}: {word:08X}")
        elif op == 1:
            value = signed(r[rs])
            taken = value < 0 if rt in (0, 2) else value >= 0
            return branch(taken, rt in (2, 3))
        elif op == 2 or op == 3:
            if op == 3:
                r[31] = after
            return next_pc, (pc & 0xF0000000) | ((word & 0x3FFFFFF) << 2)
        elif op == 4: return branch(r[rs] == r[rt])
        elif op == 5: return branch(r[rs] != r[rt])
        elif op == 6: return branch(signed(r[rs]) <= 0)
        elif op == 7: return branch(signed(r[rs]) > 0)
        elif op in (8, 9): r[rt] = (r[rs] + imm) & MASK
        elif op == 10: r[rt] = int(signed(r[rs]) < imm)
        elif op == 11: r[rt] = int(r[rs] < (imm & MASK))
        elif op == 12: r[rt] = r[rs] & (word & 0xFFFF)
        elif op == 13: r[rt] = r[rs] | (word & 0xFFFF)
        elif op == 14: r[rt] = r[rs] ^ (word & 0xFFFF)
        elif op == 15: r[rt] = ((word & 0xFFFF) << 16) & MASK
        elif op == 17:
            return self.cop1(word, rs, rt, rd, shift, funct, pc, next_pc, branch)
        elif op == 20: return branch(r[rs] == r[rt], True)
        elif op == 21: return branch(r[rs] != r[rt], True)
        elif op == 22: return branch(signed(r[rs]) <= 0, True)
        elif op == 23: return branch(signed(r[rs]) > 0, True)
        else:
            address = (r[rs] + imm) & MASK
            if op == 32:
                value = self.u8(address)
                r[rt] = (value - 256 if value > 127 else value) & MASK
            elif op == 33: r[rt] = signed16(self.u16(address)) & MASK
            elif op == 35: r[rt] = self.u32(address)
            elif op == 36: r[rt] = self.u8(address)
            elif op == 37: r[rt] = self.u16(address)
            elif op == 34:  # lwl
                bytes_in = 4 - (address & 3)
                value = int.from_bytes(self.get(address, bytes_in), "big") << ((4 - bytes_in) * 8)
                keep = (1 << ((4 - bytes_in) * 8)) - 1
                r[rt] = (r[rt] & keep) | value
            elif op == 38:  # lwr
                bytes_in = (address & 3) + 1
                value = int.from_bytes(self.get(address - bytes_in + 1, bytes_in), "big")
                keep = MASK ^ ((1 << (bytes_in * 8)) - 1)
                r[rt] = (r[rt] & keep) | value
            elif op == 40: self.w8(address, r[rt])
            elif op == 41: self.w16(address, r[rt])
            elif op == 43: self.w32(address, r[rt])
            elif op == 42:  # swl
                count = 4 - (address & 3)
                self.put(address, r[rt].to_bytes(4, "big")[:count])
            elif op == 46:  # swr
                count = (address & 3) + 1
                self.put(address - count + 1, r[rt].to_bytes(4, "big")[4 - count:])
            elif op == 49: self.f[rt] = self.u32(address)
            elif op == 53:
                self.f[rt + 1], self.f[rt] = self.u32(address), self.u32(address + 4)
            elif op == 57: self.w32(address, self.f[rt])
            elif op == 61:
                self.w32(address, self.f[rt + 1])
                self.w32(address + 4, self.f[rt])
            else: raise NotImplementedError(f"{pc:08X}: {word:08X}")
        return next_pc, after

    def cop1(self, word, fmt, ft, fs, fd, funct, pc, next_pc, branch):
        after = next_pc + 4
        if fmt == 0: self.r[ft] = self.f[fs]
        elif fmt == 4: self.f[fs] = self.r[ft]
        elif fmt == 2: self.r[ft] = 0  # cfc1: rounding mode, always the default
        elif fmt == 6: pass  # ctc1
        elif fmt == 8:
            return branch(self.condition == bool(ft & 1), bool(ft & 2))
        elif fmt in (16, 17):
            read = self.single if fmt == 16 else self.double
            write = self.set_single if fmt == 16 else self.set_double
            a = read(fs)
            b = read(ft)
            if funct == 0: write(fd, a + b)
            elif funct == 1: write(fd, a - b)
            elif funct == 2: write(fd, a * b)
            elif funct == 3: write(fd, a / b if b else math.inf)
            elif funct == 4: write(fd, math.sqrt(a) if a >= 0 else math.nan)
            elif funct == 5: write(fd, abs(a))
            elif funct == 6: write(fd, a)
            elif funct == 7: write(fd, -a)
            elif funct == 13: self.f[fd] = int(a) & MASK
            elif funct == 32: self.set_single(fd, a)
            elif funct == 33: self.set_double(fd, a)
            elif funct == 36: self.f[fd] = int(a) & MASK
            elif funct == 50: self.condition = a == b
            elif funct == 60: self.condition = a < b
            elif funct == 62: self.condition = a <= b
            else: raise NotImplementedError(f"{pc:08X}: {word:08X}")
        elif fmt == 20:
            value = signed(self.f[fs])
            if funct == 32: self.set_single(fd, float(value))
            elif funct == 33: self.set_double(fd, float(value))
            else: raise NotImplementedError(f"{pc:08X}: {word:08X}")
        else:
            raise NotImplementedError(f"{pc:08X}: {word:08X}")
        return next_pc, after
