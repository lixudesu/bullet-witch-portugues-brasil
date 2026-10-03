import argparse
import csv
import re
import struct
from pathlib import Path


JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")
METADATA = {"wav", "face", "lip", "playtime", "priority"}
FIELDS = ("line", "offset", "voice", "japanese", "english", "pt_br")


def _strings(data, start):
    items = []
    position = start
    while position < len(data):
        end = data.find(b"\0", position)
        if end < 0:
            end = len(data)
        if end > position:
            try:
                text = data[position:end].decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            if text:
                items.append((position, text))
        position = end + 1
    return items


def extract_rows(path):
    data = Path(path).read_bytes()
    if not data.startswith(b"STMANAGE"):
        raise ValueError("arquivo não é um contêiner STMANAGE")

    string_table = struct.unpack_from("<I", data, 0x1C)[0]
    items = _strings(data, string_table)
    japanese_indexes = [i for i, (_, text) in enumerate(items) if JAPANESE.search(text)]
    if not japanese_indexes:
        raise ValueError("nenhuma fala japonesa encontrada")

    first_text = items[japanese_indexes[0]][1]
    repeated = next(
        (i for i in japanese_indexes[1:] if items[i][1] == first_text),
        len(items),
    )
    first_block = [i for i in japanese_indexes if i < repeated]

    rows = []
    for line, index in enumerate(first_block, 1):
        end = first_block[line] if line < len(first_block) else repeated
        segment = items[index + 1 : end]
        voice_index = next(
            (i for i, (_, text) in enumerate(segment) if text.startswith("VO_")),
            None,
        )
        if voice_index is None:
            raise ValueError(f"fala sem ID de voz no offset 0x{items[index][0]:X}")

        candidates = [
            text
            for _, text in segment[voice_index + 1 :]
            if text not in METADATA and not NUMBER.fullmatch(text)
        ]
        if not candidates:
            raise ValueError(f"fala sem inglês no offset 0x{items[index][0]:X}")

        rows.append(
            {
                "line": line,
                "offset": f"0x{items[index][0]:X}",
                "voice": segment[voice_index][1],
                "japanese": items[index][1],
                "english": candidates[0],
                "pt_br": "",
            }
        )
    return rows


def write_csv(rows, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Extrai falas de rtevent.bin para CSV.")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=project / "source-original" / "data" / "text" / "rtevent.bin",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=project / "build" / "rtevent-extracted.csv",
    )
    args = parser.parse_args()
    rows = extract_rows(args.input)
    write_csv(rows, args.output)
    print(f"{len(rows)} falas extraídas para {args.output}")


if __name__ == "__main__":
    main()
