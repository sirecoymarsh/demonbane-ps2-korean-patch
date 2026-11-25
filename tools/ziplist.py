import sys
import zipfile
import collections

path = sys.argv[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
z = zipfile.ZipFile(path)
infos = z.infolist()
print(f"{path}\nentries: {len(infos)}")


def name_of(i):
    if i.flag_bits & 0x800:
        return i.filename
    raw = i.filename.encode("cp437", "replace")
    for enc in ("cp949", "cp932", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return i.filename


ext = collections.Counter()
top = collections.Counter()
total = 0
for i in infos:
    n = name_of(i)
    total += i.file_size
    if i.is_dir():
        continue
    ext["." + n.rsplit(".", 1)[-1].lower() if "." in n.rsplit("/", 1)[-1] else "(none)"] += 1
    top[n.split("/")[0]] += 1

print(f"uncompressed total: {total:,} bytes")
print("\n-- top-level --")
for k, v in top.most_common(30):
    print(f"  {v:>6}  {k}")
print("\n-- extensions --")
for k, v in ext.most_common(30):
    print(f"  {v:>6}  {k}")
print("\n-- first 60 entries --")
for i in infos[:60]:
    print(f"  {i.file_size:>12}  {name_of(i)}")
