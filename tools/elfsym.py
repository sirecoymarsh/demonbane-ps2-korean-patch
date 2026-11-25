"""Dump ELF32 little-endian sections and symbols (PS2 MIPS ELF)."""
import struct
import sys

path = sys.argv[1]
filt = sys.argv[2].lower() if len(sys.argv) > 2 else None
data = open(path, "rb").read()
assert data[:4] == b"\x7fELF"

(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
 e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIIIIIHHHHHH", data, 16)

print(f"type={e_type} machine={e_machine} entry=0x{e_entry:08X} shnum={e_shnum} phnum={e_phnum}")

secs = []
for i in range(e_shnum):
    o = e_shoff + i * e_shentsize
    (name, stype, flags, addr, off, size, link, info, align, entsize) = struct.unpack_from("<IIIIIIIIII", data, o)
    secs.append(dict(name=name, type=stype, addr=addr, off=off, size=size, link=link, entsize=entsize))

shstr = secs[e_shstrndx]


def sname(idx):
    o = shstr["off"] + idx
    return data[o:data.index(b"\0", o)].decode()


print("\nSections:")
for s in secs:
    s["sname"] = sname(s["name"])
    print(f"  {s['sname']:<16} type={s['type']:<4} addr=0x{s['addr']:08X} off=0x{s['off']:08X} size={s['size']}")

print("\nProgram headers:")
for i in range(e_phnum):
    o = e_phoff + i * e_phentsize
    (p_type, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align) = struct.unpack_from("<IIIIIIII", data, o)
    print(f"  type={p_type} off=0x{p_off:08X} vaddr=0x{p_vaddr:08X} filesz={p_filesz} memsz={p_memsz} flags={p_flags}")

symtab = next((s for s in secs if s["sname"] == ".symtab"), None)
if symtab:
    strtab = secs[symtab["link"]]
    n = symtab["size"] // 16
    print(f"\nSymbols: {n}")
    out = []
    for i in range(n):
        o = symtab["off"] + i * 16
        st_name, st_value, st_size, st_info, st_other, st_shndx = struct.unpack_from("<IIIBBH", data, o)
        so = strtab["off"] + st_name
        nm = data[so:data.index(b"\0", so)].decode("latin1")
        typ = st_info & 0xF
        if typ == 2 or (typ == 1 and st_size):
            out.append((st_value, st_size, "FUNC" if typ == 2 else "OBJ", nm))
    out.sort()
    for v, sz, t, nm in out:
        if filt and filt not in nm.lower():
            continue
        print(f"  0x{v:08X} {sz:>7} {t:<5} {nm}")
