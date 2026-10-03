"""Extract translation candidates from every local STMANAGE text container."""

import csv
import re
import struct
import unicodedata
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT / "source-original/data/text"
OUTPUT_DIR = PROJECT / "translation"
MASTER_CSV = OUTPUT_DIR / "all_text.csv"
INVENTORY_CSV = OUTPUT_DIR / "extraction_inventory.csv"

JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")
IDENTIFIER = re.compile(
    r"(?:VO_[A-Z0-9_]+|(?:sys|arg|res|nwp|onm|sts)\.?\d{3,}(?:\.\d{2})*|"
    r"(?:cmtxt|costxt)\d{2}|BW\d_\d{4}|dm\d{2})",
    re.I,
)
FOREIGN_HINT = re.compile(
    r"\b(?:facile|difficile|leicht|schwer|punkte|punti|puntos|"
    r"points de mort|temps effectue|dificultad|sopravvivenza|"
    r"infernale|caos)\b|[àâçéèêëîïôûùüÿñöä]",
    re.I,
)
METADATA = {"starttime", "playtime", "wav", "face", "lip", "priority", "beginwait"}
FIELDS = (
    "file",
    "record",
    "source_offset",
    "english_offset",
    "voice",
    "japanese",
    "english",
    "pt_br",
    "status",
)
INVENTORY_FIELDS = (
    "file",
    "size_bytes",
    "decoded_strings",
    "japanese_records",
    "english_pairs",
    "japanese_only",
    "english_candidates_without_japanese",
    "notes",
)


def read_strings(path):
    data = path.read_bytes()
    if not data.startswith(b"STMANAGE"):
        raise ValueError(f"{path.name}: cabeçalho STMANAGE ausente")
    start = struct.unpack_from("<I", data, 0x1C)[0]
    if start >= len(data):
        raise ValueError(f"{path.name}: início da tabela inválido (0x{start:X})")

    strings = []
    position = start
    for chunk in data[start:].split(b"\0"):
        if not chunk:
            position += 1
            continue
        try:
            value = chunk.decode("utf-8")
        except UnicodeDecodeError:
            position += len(chunk) + 1
            continue
        strings.append((position, value))
        position += len(chunk) + 1
    return data, strings


def is_text_candidate(value):
    normalized = unicodedata.normalize("NFKC", value).strip()
    lowered = normalized.casefold()
    if not normalized or lowered in METADATA or NUMBER.fullmatch(normalized) or lowered == "x":
        return False
    if IDENTIFIER.fullmatch(normalized):
        return False
    return any(char.isalpha() for char in normalized)


def existing_translations():
    translations = {}
    bw1_path = OUTPUT_DIR / "BW1_0100.csv"
    if bw1_path.exists():
        with bw1_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("pt_br", "").strip():
                    translations[("BW1_0100.bin", int(row["offset"], 16))] = row["pt_br"]

    rtevent_path = OUTPUT_DIR / "rtevent.csv"
    if rtevent_path.exists():
        with rtevent_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                text = row.get("pt_br", "").strip()
                if text:
                    translations[("rtevent.bin", row.get("voice", ""), row.get("english", "").strip())] = text
    return translations


def extract_localized_records(filename, strings, translations):
    jp_indexes = [i for i, (_, value) in enumerate(strings) if JAPANESE.search(value)]
    rows = []
    english_pairs = 0
    for record, index in enumerate(jp_indexes, 1):
        next_index = jp_indexes[record] if record < len(jp_indexes) else len(strings)
        segment = strings[index + 1 : next_index]
        voice = next((value for _, value in segment if value.startswith("VO_")), "")
        selected = next(
            ((offset, value) for offset, value in segment if is_text_candidate(value)),
            None,
        )
        english_offset, english = selected if selected else ("", "")
        if english:
            english_pairs += 1
            pt_br = translations.get((filename, english_offset), "")
            if filename == "rtevent.bin":
                pt_br = translations.get((filename, voice, english.strip()), pt_br)
            status = "já traduzido" if pt_br else "aguardando tradução/revisão"
        else:
            pt_br = ""
            status = "sem par em inglês; traduzir a partir do japonês"
        rows.append(
            {
                "file": filename,
                "record": record,
                "source_offset": f"0x{strings[index][0]:X}",
                "english_offset": f"0x{english_offset:X}" if english_offset != "" else "",
                "voice": voice,
                "japanese": strings[index][1],
                "english": english,
                "pt_br": pt_br,
                "status": status,
            }
        )
    return rows, len(jp_indexes), english_pairs


def extract_without_japanese(filename, strings):
    """Keep known English-only locale groups visible with an explicit review flag."""
    rows = []
    if filename.startswith("costxt"):
        # These files have no Japanese text. English is the first localized
        # string, with duplicate display strings stored at separate offsets.
        for index, (offset, value) in enumerate(strings):
            if value.casefold() == "playtime":
                previous = strings[index - 1] if index else None
                if previous and is_text_candidate(previous[1]):
                    rows.append((previous[0], previous[1]))
        # Some costume files store a second English copy next to the ID block.
        seen_offsets = {offset for offset, _ in rows}
        for offset, value in strings:
            if unicodedata.normalize("NFKC", value).startswith("Special Costume") and offset not in seen_offsets:
                rows.append((offset, value))
        return rows

    if filename == "res.bin":
        # Result-screen labels contain no Japanese source. The language slot
        # order is not uniform in this file, so retain the first likely English
        # variants and mark them for language-pair verification.
        boundaries = [i for i, (_, value) in enumerate(strings) if re.fullmatch(r"res\d{4}", value)]
        for boundary_number, start in enumerate(boundaries):
            end = boundaries[boundary_number + 1] if boundary_number + 1 < len(boundaries) else len(strings)
            candidates = [(offset, value) for offset, value in strings[start + 1 : end] if is_text_candidate(value)]
            for offset, value in candidates:
                if FOREIGN_HINT.search(unicodedata.normalize("NFKC", value)):
                    break
                rows.append((offset, value))
        return rows

    return rows


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Pasta ausente: {SOURCE_DIR}")
    translations = existing_translations()
    master_rows = []
    inventory_rows = []

    for path in sorted(SOURCE_DIR.glob("*.bin")):
        data, strings = read_strings(path)
        rows, jp_count, paired = extract_localized_records(path.name, strings, translations)
        no_jp = extract_without_japanese(path.name, strings) if jp_count == 0 else []
        for number, row in enumerate(rows, 1):
            row["record"] = number
        master_rows.extend(rows)

        uncertain = 0
        if no_jp:
            for number, (offset, value) in enumerate(no_jp, 1):
                master_rows.append(
                    {
                        "file": path.name,
                        "record": f"EN-{number}",
                        "source_offset": "",
                        "english_offset": f"0x{offset:X}",
                        "voice": "",
                        "japanese": "",
                        "english": value,
                        "pt_br": "",
                        "status": "candidato sem fonte japonesa; conferir idioma e duplicatas",
                    }
                )
            uncertain = len(no_jp)

        inventory_rows.append(
            {
                "file": path.name,
                "size_bytes": len(data),
                "decoded_strings": len(strings),
                "japanese_records": jp_count,
                "english_pairs": paired,
                "japanese_only": jp_count - paired,
                "english_candidates_without_japanese": uncertain,
                "notes": "texto de teste" if path.name == "txtsamp.bin" else "",
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(MASTER_CSV, FIELDS, master_rows)
    write_csv(INVENTORY_CSV, INVENTORY_FIELDS, inventory_rows)
    print(f"Arquivos analisados: {len(inventory_rows)}")
    print(f"Registros na planilha: {len(master_rows)}")
    print(f"Pares japonês/inglês: {sum(int(row['english_pairs']) for row in inventory_rows)}")
    print(f"Sem par em inglês: {sum(int(row['japanese_only']) for row in inventory_rows)}")
    print(f"Candidatos sem fonte japonesa para conferir: {sum(int(row['english_candidates_without_japanese']) for row in inventory_rows)}")
    print(f"Planilha: {MASTER_CSV}")
    print(f"Inventário: {INVENTORY_CSV}")


if __name__ == "__main__":
    main()
