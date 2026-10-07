"""Aplica as traduções preenchidas no CSV aos textos ingleses de rtevent.bin."""

import argparse
import csv
import re
import struct
from pathlib import Path

from extract_rtevent import JAPANESE, METADATA, NUMBER


def translated_spans(data):
    start = struct.unpack_from("<I", data, 0x1C)[0]
    strings = []
    pos = start
    while pos < len(data):
        end = data.find(b"\0", pos)
        if end < 0:
            break
        if end > pos:
            try:
                value = data[pos:end].decode("utf-8")
            except UnicodeDecodeError:
                value = ""
            if value:
                strings.append((pos, end, value))
        pos = end + 1

    jp_indices = [i for i, (_, _, value) in enumerate(strings) if JAPANESE.search(value)]
    if not jp_indices:
        raise ValueError("nenhuma fala japonesa encontrada")
    first_text = strings[jp_indices[0]][2]
    repeated = next((i for i in jp_indices[1:] if strings[i][2] == first_text), len(strings))
    block = [i for i in jp_indices if i < repeated]

    result = []
    for line, index in enumerate(block, 1):
        end_index = block[line] if line < len(block) else repeated
        segment = strings[index + 1:end_index]
        voice_at = next((i for i, item in enumerate(segment) if item[2].startswith("VO_")), None)
        if voice_at is None:
            raise ValueError(f"fala sem ID de voz na linha {line}")
        candidates = [item for item in segment[voice_at + 1:]
                      if item[2] not in METADATA and not NUMBER.fullmatch(item[2])]
        if not candidates:
            raise ValueError(f"fala sem texto inglês na linha {line}")
        result.append((line, candidates[0][0], candidates[0][1]))
    return result


def build(source, table, output):
    original = Path(source).read_bytes()
    patched = bytearray(original)
    spans = {line: (start, end) for line, start, end in translated_spans(original)}
    applied = 0
    with Path(table).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            text = row["pt_br"].strip()
            if not text:
                continue
            line = int(row["line"])
            start, end = spans[line]
            encoded = text.encode("utf-8")
            capacity = end - start
            if len(encoded) > capacity:
                raise ValueError(f"linha {line}: {len(encoded)} bytes traduzidos excedem o limite de {capacity}")
            patched[start:end] = encoded + b" " * (capacity - len(encoded))
            applied += 1
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(patched)
    print(f"{applied} fala(s) aplicada(s); tamanho preservado: {len(original)} bytes")


def main():
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=project / "arquivos/originais/data/text/rtevent.bin")
    parser.add_argument("--table", type=Path, default=project / "traducoes/rtevent.csv")
    parser.add_argument("--output", type=Path, default=project / "patches/data/text/rtevent.bin")
    args = parser.parse_args()
    build(args.source, args.table, args.output)


if __name__ == "__main__":
    main()
