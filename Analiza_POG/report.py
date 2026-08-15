from pathlib import Path
import math
import sys

_VENDOR = Path(__file__).resolve().parent / "_vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

import xlsxwriter


HEADER_FMT = {
    "bold": True,
    "font_color": "white",
    "bg_color": "#1F4E78",
    "align": "center",
    "valign": "vcenter",
    "text_wrap": True,
}
CELL_FMT = {"valign": "top", "text_wrap": True}
CONTROL_FMT = {
    "font_color": "#FF0000",
    "valign": "top",
    "text_wrap": True,
}
NUMBER_FMT = {
    "num_format": "#,##0.###",
    "valign": "top",
    "text_wrap": True,
}
PERCENT_FMT = {
    "num_format": "0.000%",
    "valign": "top",
    "text_wrap": True,
}
INTEGER_FMT = {
    "num_format": "#,##0",
    "valign": "top",
    "text_wrap": True,
}
INTEGER_BORDER_FMT = {
    "num_format": "#,##0",
    "bottom": 3,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}
INTEGER_ADDITIONAL_FMT = {
    "num_format": "#,##0",
    "bg_color": "#E7E6E6",
    "valign": "top",
    "text_wrap": True,
}
INTEGER_ADDITIONAL_BORDER_FMT = {
    "num_format": "#,##0",
    "bg_color": "#E7E6E6",
    "bottom": 2,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}
CONTROL_NUMBER_FMT = {
    "num_format": "#,##0.###",
    "font_color": "#FF0000",
    "valign": "top",
    "text_wrap": True,
}

GROUP_BORDER = {
    "bottom": 3,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}
GROUP_BORDER_NUMBER = {
    "num_format": "#,##0.###",
    "bottom": 3,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}
GROUP_BORDER_CONTROL = {
    "font_color": "#FF0000",
    "bottom": 3,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}
GROUP_BORDER_CONTROL_NUMBER = {
    "num_format": "#,##0.###",
    "font_color": "#FF0000",
    "bottom": 3,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}

ADDITIONAL_FMT = {
    "bg_color": "#E7E6E6",
    "valign": "top",
    "text_wrap": True,
}
ADDITIONAL_NUMBER_FMT = {
    "num_format": "#,##0.###",
    "bg_color": "#E7E6E6",
    "valign": "top",
    "text_wrap": True,
}
ADDITIONAL_BORDER_FMT = {
    "bg_color": "#E7E6E6",
    "bottom": 2,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}
ADDITIONAL_BORDER_NUMBER_FMT = {
    "num_format": "#,##0.###",
    "bg_color": "#E7E6E6",
    "bottom": 2,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}

PERCENT_BORDER_FMT = {
    "num_format": "0.000%",
    "bottom": 3,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}
PERCENT_ADDITIONAL_FMT = {
    "num_format": "0.000%",
    "bg_color": "#E7E6E6",
    "valign": "top",
    "text_wrap": True,
}
PERCENT_ADDITIONAL_BORDER_FMT = {
    "num_format": "0.000%",
    "bg_color": "#E7E6E6",
    "bottom": 2,
    "bottom_color": "#808080",
    "valign": "top",
    "text_wrap": True,
}

PREFERRED = {
    "MPZP": 20,
    "Część MPZP": 12,
    "Teren inwestycji": 22,
    "Oznaczenie strefy": 16,
    "Oznaczenie": 16,
    "Symbol": 10,
    "Powierzchnia POG [m²]": 18,
    "Powierzchnia w MPZP [m²]": 20,
    "Powierzchnia w terenie [m²]": 20,
    "Udział w MPZP [%]": 16,
    "Udział w terenie [%]": 16,
    "Profil podstawowy": 42,
    "Profil dodatkowy": 42,
    "Intensywność max": 16,
    "Udział zabudowy max [%]": 20,
    "Wysokość max [m]": 16,
    "PBC min [%]": 14,
    "KONTROLA": 48,
    "gml_id": 38,
    "Typ profilu": 18,
    "kod przeznaczenia": 24,
    "Nazwa": 38,
    "OUZ oznaczenie": 18,
    "Powierzchnia OUZ [m²]": 20,
    "Powierzchnia OUZ w MPZP [m²]": 24,
    "Powierzchnia OUZ w terenie [m²]": 24,
    "Powierzchnia części [m²]": 20,
    "Pokrycie POG": 16,
    "Brak [m²]": 18,
}


def _is_missing(value):
    if value is None:
        return True
    try:
        return bool(value.isNull())
    except AttributeError:
        pass
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _clean_number(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        if abs(value) < 1e-9:
            return 0.0
    return value


def _num_key(value, default=10**12):
    if _is_missing(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _part_key(value):
    text = "" if _is_missing(value) else str(value)
    match = __import__("re").search(r"(\d+)", text)
    return int(match.group(1)) if match else 10**9


def _zone_key(row):
    import re
    value = row.get("Oznaczenie strefy", row.get("Oznaczenie", ""))
    text = "" if _is_missing(value) else str(value).strip()
    match = re.match(r"^(\d+)", text)
    number = int(match.group(1)) if match else 10**9
    symbol = re.sub(r"^\d+\s*", "", text).upper()
    return number, symbol


def _sort_strefy(rows):
    if not rows:
        return []
    # MPZP: keep each plan together; within a plan first part 1, part 2,
    # then the numeric zone number and symbol.
    if "MPZP" in rows[0]:
        return sorted(
            rows,
            key=lambda r: (
                str(r.get("MPZP", "")).casefold(),
                _part_key(r.get("Część MPZP")),
                _zone_key(r),
            ),
        )
    return _sort_dwz(rows)


def _sort_dwz(rows):
    if not rows:
        return []

    def key(row):
        fid = row.get("FID źródłowy")
        zone_num, zone_symbol = _zone_key(row)
        profile_type = 0
        if str(row.get("Typ profilu", "")).upper() == "DODATKOWY":
            profile_type = 1
        return (
            _num_key(fid),
            str(row.get("Teren inwestycji", "")).casefold(),
            zone_num,
            zone_symbol,
            profile_type,
        )

    return sorted(rows, key=key)


def _columns(rows):
    result = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                result.append(key)
    return result


def _profile_lines(value, width=42):
    if _is_missing(value):
        return 1
    text = str(value)
    if not text:
        return 1
    lines = 0
    for segment in text.split("\n"):
        lines += max(1, math.ceil(len(segment) / max(1, width)))
    return max(1, lines)


def _write_sheet(workbook, name, rows):
    if not rows:
        return False

    # Work on a new list so the report function never mutates analysis data.
    rows = [dict(row) for row in rows]

    is_dwz = "Teren inwestycji" in rows[0]
    if is_dwz:
        # Część terenu and FID źródłowy are technical fields in DWZ.
        # FID remains available internally for sorting but is not displayed.
        rows = _sort_dwz(rows)
        for row in rows:
            row.pop("Część terenu", None)
            row.pop("FID źródłowy", None)
    elif name == "STREFY":
        rows = _sort_strefy(rows)

    columns = _columns(rows)

    ws = workbook.add_worksheet(name)

    header = workbook.add_format(HEADER_FMT)
    cell = workbook.add_format(CELL_FMT)
    control = workbook.add_format(CONTROL_FMT)
    control_number = workbook.add_format(CONTROL_NUMBER_FMT)

    group_border = workbook.add_format(GROUP_BORDER)
    group_border_number = workbook.add_format(GROUP_BORDER_NUMBER)
    group_border_control = workbook.add_format(GROUP_BORDER_CONTROL)
    group_border_control_number = workbook.add_format(GROUP_BORDER_CONTROL_NUMBER)

    additional = workbook.add_format(ADDITIONAL_FMT)
    additional_number = workbook.add_format(ADDITIONAL_NUMBER_FMT)
    additional_border = workbook.add_format(ADDITIONAL_BORDER_FMT)
    additional_border_number = workbook.add_format(ADDITIONAL_BORDER_NUMBER_FMT)

    percent = workbook.add_format(PERCENT_FMT)
    percent_border = workbook.add_format(PERCENT_BORDER_FMT)
    percent_additional = workbook.add_format(PERCENT_ADDITIONAL_FMT)
    percent_additional_border = workbook.add_format(PERCENT_ADDITIONAL_BORDER_FMT)

    integer_fmt = workbook.add_format(INTEGER_FMT)
    integer_border = workbook.add_format(INTEGER_BORDER_FMT)
    integer_additional = workbook.add_format(INTEGER_ADDITIONAL_FMT)
    integer_additional_border = workbook.add_format(INTEGER_ADDITIONAL_BORDER_FMT)

    for c, col in enumerate(columns):
        ws.write(0, c, str(col), header)

    terrain_col = (
        columns.index("Teren inwestycji")
        if "Teren inwestycji" in columns else None
    )

    for r, row in enumerate(rows, 1):
        is_last_in_group = False
        if terrain_col is not None:
            current = str(row.get(columns[terrain_col], ""))
            if r == len(rows):
                is_last_in_group = True
            else:
                next_value = str(rows[r].get(columns[terrain_col], ""))
                is_last_in_group = current != next_value

        max_lines = 1
        if name == "STREFY":
            for profile_col in ("Profil podstawowy", "Profil dodatkowy"):
                if profile_col in columns:
                    max_lines = max(
                        max_lines,
                        _profile_lines(row.get(profile_col), 42)
                    )
        elif name == "PROFILE":
            if "Nazwa" in columns:
                max_lines = max(max_lines, _profile_lines(row.get("Nazwa"), 38))

        for c, col in enumerate(columns):
            val = row.get(col)

            if _is_missing(val):
                val = ""

            is_control = col == "KONTROLA" and str(val).strip()
            val = _clean_number(val)

            is_additional = (
                name == "PROFILE"
                and str(row.get("Typ profilu", "")).strip().upper() == "DODATKOWY"
            )

            if isinstance(val, bool):
                if is_additional and is_last_in_group:
                    fmt = additional_border
                elif is_additional:
                    fmt = additional
                elif is_control and is_last_in_group:
                    fmt = group_border_control
                elif is_control:
                    fmt = control
                elif is_last_in_group:
                    fmt = group_border
                else:
                    fmt = cell
                ws.write_boolean(r, c, val, fmt)

            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                is_percent = "[%]" in str(col) or col == "Pokrycie POG"
                is_integer = str(col).strip() == "Wysokość max [m]"

                if is_integer:
                    if is_additional and is_last_in_group:
                        fmt = integer_additional_border
                    elif is_additional:
                        fmt = integer_additional
                    elif is_last_in_group:
                        fmt = integer_border
                    else:
                        fmt = integer_fmt
                elif is_percent:
                    if is_additional and is_last_in_group:
                        fmt = percent_additional_border
                    elif is_additional:
                        fmt = percent_additional
                    elif is_last_in_group:
                        fmt = percent_border
                    else:
                        fmt = percent
                else:
                    if is_additional and is_last_in_group:
                        fmt = additional_border_number
                    elif is_additional:
                        fmt = additional_number
                    elif is_control and is_last_in_group:
                        fmt = group_border_control_number
                    elif is_control:
                        fmt = control_number
                    elif is_last_in_group:
                        fmt = group_border_number
                    else:
                        fmt = workbook.add_format(NUMBER_FMT)
                ws.write_number(r, c, float(val), fmt)

            else:
                if is_additional and is_last_in_group:
                    fmt = additional_border
                elif is_additional:
                    fmt = additional
                elif is_control and is_last_in_group:
                    fmt = group_border_control
                elif is_control:
                    fmt = control
                elif is_last_in_group:
                    fmt = group_border
                else:
                    fmt = cell
                ws.write(r, c, str(val), fmt)

        if max_lines > 1:
            ws.set_row(r, min(18 * max_lines, 180))

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(rows), len(columns) - 1)
    ws.set_row(0, 34)

    for i, col in enumerate(columns):
        width = min(PREFERRED.get(col, 20), 48)
        if name == "STREFY" and col in ("Profil podstawowy", "Profil dodatkowy"):
            width = 42
        ws.set_column(i, i, width)

    return True


def write_report(st_df, prof_df, ouz_df, ctrl_df, output_path):
    path = Path(output_path)
    if path.suffix.casefold() != ".xlsx":
        path = path.with_suffix(".xlsx")
    path.parent.mkdir(parents=True, exist_ok=True)

    workbook = xlsxwriter.Workbook(str(path), {"constant_memory": True})
    try:
        _write_sheet(workbook, "STREFY", st_df or [])

        if prof_df:
            _write_sheet(workbook, "PROFILE", prof_df)

        if ouz_df:
            _write_sheet(workbook, "OUZ", ouz_df)

        ctrl = [
            row for row in (ctrl_df or [])
            if str(row.get("KONTROLA", "")).strip()
        ]
        if ctrl:
            _write_sheet(workbook, "KONTROLA", ctrl)
    finally:
        workbook.close()

    return str(path)
