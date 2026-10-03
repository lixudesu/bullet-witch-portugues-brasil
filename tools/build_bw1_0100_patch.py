"""Insere a tradução da abertura sem mover os offsets de BW1_0100.bin."""

import csv
from pathlib import Path


project = Path(__file__).resolve().parents[1]
source = project / "source-original/data/text/BW1_0100.bin"
table = project / "translation/BW1_0100.csv"
output = project / "patch/data/text/BW1_0100.bin"

original = source.read_bytes()
if not original.startswith(b"STMANAGE"):
    raise ValueError("fonte não é um contêiner STMANAGE")
patched = bytearray(original)
seen = set()
with table.open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))

for row in rows:
    offset = int(row["offset"], 16)
    if offset in seen:
        raise ValueError(f"offset repetido: 0x{offset:X}")
    seen.add(offset)
    end = original.find(b"\0", offset)
    if end < 0:
        raise ValueError(f"string sem terminador: 0x{offset:X}")
    old = original[offset:end].decode("utf-8")
    if old.strip() != row["english"]:
        raise ValueError(f"texto original diferente em 0x{offset:X}: {old!r}")
    new = row["pt_br"].encode("utf-8")
    capacity = end - offset
    if len(new) > capacity:
        raise ValueError(f"0x{offset:X}: {len(new)} bytes excedem os {capacity} disponíveis")
    patched[offset:end] = new + b" " * (capacity - len(new))

output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(patched)
print(f"{len(rows)} strings traduzidas em {output}; {len(patched)} bytes (tamanho original preservado)")
