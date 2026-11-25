"""Disassemble a symbol out of the PS2 ELF using capstone (MIPS32 LE)."""
import struct
import sys
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

path = r"P:\AI\demonbane-ps2-kr\extract\SLPM_654.91"
data = open(path, "rb").read()

# section 'main': vaddr 0x00100000 at file offset 0x80
BASE = 0x00100000
FOFF = 0x80

# symbol table
(e_shoff,) = struct.unpack_from("<I", data, 32)
(e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHH", data, 46)
secs = []
for i in range(e_shnum):
    o = e_shoff + i * e_shentsize
    secs.append(struct.unpack_from("<IIIIIIIIII", data, o))
shstr_off = secs[e_shstrndx][4]


def sname(idx):
    o = shstr_off + idx
    return data[o:data.index(b"\0", o)].decode()


symtab = next(s for s in secs if sname(s[0]) == ".symtab")
strtab = secs[symtab[6]]
syms = {}
addr2name = {}
for i in range(symtab[5] // 16):
    o = symtab[4] + i * 16
    st_name, st_value, st_size, st_info, st_other, st_shndx = struct.unpack_from("<IIIBBH", data, o)
    so = strtab[4] + st_name
    nm = data[so:data.index(b"\0", so)].decode("latin1")
    if nm:
        syms.setdefault(nm, (st_value, st_size))
        if st_value and st_value not in addr2name:
            addr2name[st_value] = nm

md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
md.detail = False

for name in sys.argv[1:]:
    if name not in syms:
        print(f"!! symbol {name} not found")
        continue
    addr, size = syms[name]
    if size == 0:
        size = 0x200
    off = addr - BASE + FOFF
    code = data[off:off + size]
    print(f"=== {name} @ 0x{addr:08X} size={size} (file 0x{off:X}) ===")
    pos = 0
    while pos < len(code):
        got = False
        for ins in md.disasm(code[pos:], addr + pos, count=1):
            tgt = ""
            for tok in ins.op_str.replace(",", " ").split():
                if tok.startswith("0x") and tok[2:].isalnum():
                    try:
                        v = int(tok, 16)
                    except ValueError:
                        continue
                    if v in addr2name:
                        tgt = f"   ; {addr2name[v]}"
            print(f"  {ins.address:08X}  {ins.mnemonic:<10} {ins.op_str}{tgt}")
            pos += ins.size
            got = True
        if not got:
            word = struct.unpack_from("<I", code, pos)[0]
            print(f"  {addr + pos:08X}  .word      0x{word:08X}")
            pos += 4
    print()
