import os
import re


def unescape_commas(s: str) -> str:
    r"""Convert escaped commas \, back to literal commas."""
    return s.replace("\\,", ",")


def escape_commas(s: str) -> str:
    """Escape literal commas as \\, in the NAME column so the target format
    won't mis-split fields.
    """
    return s.replace(",", "\\,")


def split_preserving_escaped_commas(line: str) -> list[str]:
    """Split on commas that are NOT escaped with a backslash.
    Keep the backslash in '\\,' as part of the field.
    """
    fields = []
    buf = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == ",":
            if buf and buf[-1] == "\\":
                buf.append(",")
            else:
                fields.append("".join(buf))
                buf = []
            i += 1
            continue
        else:
            buf.append(ch)
            i += 1
    fields.append("".join(buf))
    return fields


def join_preserving_escaped_commas(fields: list[str]) -> str:
    """Join fields back with ','.
    We assume NAME was already run through escape_commas().
    """
    return ",".join(fields)


def is_header_row(row: list[str]) -> bool:
    """Check if a row appears to be a header row."""
    if not row:
        return False
    header_patterns = ["index", "name", "duration", "encoding", "bitrate"]
    first_field = row[0].strip().lower()
    return first_field in header_patterns or bool(re.match(r"^[a-z_]+$", first_field))


def read_csv(path: str) -> list[list[str]]:
    """Read CSV using custom splitting logic that preserves escaped commas."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n\r")
            if line == "":
                continue
            row = split_preserving_escaped_commas(line)
            rows.append(row)
    return rows


def write_csv(path: str, rows: list[list[str]]) -> None:
    """Convert row arrays back into CSV text lines and write to file."""
    out_lines = []
    for row in rows:
        normalized_row = row[:11] if len(row) > 11 else row + [""] * (11 - len(row))
        out_lines.append(join_preserving_escaped_commas(normalized_row))

    csv_text = "\n".join(out_lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(csv_text)


def inject_names_by_index(
    rows: list[list[str]],
    playlist_name: str,
    track_names: list[str]
) -> tuple[list[list[str]], list[str]]:
    """Merge names into the NAME column (col 4) using INDEX column (col 0).

    Returns:
        Tuple of (updated_rows, warnings)
    """
    warnings = []
    updated_rows = []
    header_found = False

    for row in rows:
        normalized_row = row[:11] if len(row) > 11 else row + [""] * (11 - len(row))

        if not header_found and is_header_row(normalized_row):
            header_found = True
            updated_rows.append(normalized_row)
            continue

        if header_found:
            index_field = normalized_row[0].strip()

            try:
                idx_val = int(index_field)
            except ValueError:
                updated_rows.append(normalized_row)
                continue

            if idx_val == 0:
                if playlist_name:
                    normalized_row[4] = escape_commas(playlist_name)
                else:
                    original_name = unescape_commas(normalized_row[4])
                    normalized_row[4] = escape_commas(original_name)
            else:
                track_pos = idx_val - 1
                if 0 <= track_pos < len(track_names):
                    normalized_row[4] = escape_commas(track_names[track_pos])
                elif track_pos >= len(track_names):
                    original_name = unescape_commas(normalized_row[4])
                    normalized_row[4] = escape_commas(original_name)
                    warnings.append(f"Track index {idx_val}: no matching Apple Music track, preserved original name")

        updated_rows.append(normalized_row)

    return updated_rows, warnings
