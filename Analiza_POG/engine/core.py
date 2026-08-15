from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from collections import OrderedDict
from typing import Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsGeometry,
    QgsVectorLayer,
    QgsWkbTypes,
)

TOLERANCE_M2 = 1.0


@dataclass
class GroupingDecision:
    field: Optional[str]
    reason: str


def _norm_field_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def suggest_name_field(columns) -> GroupingDecision:
    cols = [c for c in columns if c != "geometry"]
    norm = {c: _norm_field_name(c) for c in cols}
    exact = [c for c, n in norm.items() if n in {"nazwa_mpzp", "nazwa_planu"}]
    if len(exact) == 1:
        return GroupingDecision(exact[0], "exact preferred name field")
    related = [c for c, n in norm.items()
               if "nazwa" in n and ("mpzp" in n or "plan" in n)]
    if len(related) == 1:
        return GroupingDecision(related[0], "unique name+plan/mpzp field")
    generic = [c for c, n in norm.items() if "nazwa" in n]
    if len(generic) == 1:
        return GroupingDecision(generic[0], "unique field containing 'nazwa'")
    if len(exact) > 1 or len(related) > 1 or len(generic) > 1:
        return GroupingDecision(
            None, "ambiguous name fields; user selection required"
        )
    return GroupingDecision(
        None, "no field containing 'nazwa'; user selection required"
    )


def available_grouping_fields(columns):
    return [c for c in columns if c != "geometry"]


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(value.isNull())
    except AttributeError:
        pass
    if isinstance(value, float):
        return math.isnan(value)
    return False


def _safe_text(value):
    if _is_missing(value):
        return ""
    return str(value).strip()


def _field_value(feature, name, default=None):
    try:
        value = feature[name]
    except Exception:
        return default
    return default if _is_missing(value) else value


def _layer_uri(gml_path: str, layer_name: str) -> str:
    # GDAL/OGR exposes named layers from GML through the layername URI.
    return f"{str(gml_path)}|layername={layer_name}"


def _open_gml_layer(gml_path, layer_name):
    path = str(gml_path)
    layer = QgsVectorLayer(_layer_uri(path, layer_name), layer_name, "ogr")
    if not layer.isValid():
        # Fallback for provider versions that expose the GML layer directly.
        layer = QgsVectorLayer(path, layer_name, "ogr")
    if not layer.isValid():
        raise ValueError(
            f"Nie udało się odczytać warstwy '{layer_name}' z pliku GML."
        )
    return layer


def _gml_crs(gml_path):
    """Read a declared srsName from GML using only the Python stdlib."""
    try:
        root = ET.parse(str(gml_path)).getroot()
        for elem in root.iter():
            for key, value in elem.attrib.items():
                if not key.lower().endswith("srsname") or not value:
                    continue
                crs = QgsCoordinateReferenceSystem()
                if crs.createFromUserInput(str(value)) and crs.isValid():
                    return crs
                match = re.search(r"(\d{4,6})$", str(value))
                if match:
                    candidate = QgsCoordinateReferenceSystem(
                        f"EPSG:{match.group(1)}"
                    )
                    if candidate.isValid():
                        return candidate
    except Exception:
        pass
    return None


def _feature_records(layer):
    fields = [f.name() for f in layer.fields()]
    records = []
    for feature in layer.getFeatures():
        attrs = {}
        for name in fields:
            attrs[name] = _field_value(feature, name)
        gid = _field_value(feature, "gml_id")
        if gid in (None, ""):
            gid = feature.id()
        records.append({
            "attrs": attrs,
            "geometry": QgsGeometry(feature.geometry()),
            "gml_id": str(gid),
        })
    return records


def _profile_records(gml_path):
    root = ET.parse(str(gml_path)).getroot()
    nsmap = root.tag
    # Namespace URIs are discovered from the root rather than hard-coded
    # except for standard xlink/gml fallbacks.
    app = None
    xlink = "http://www.w3.org/1999/xlink"
    gml = "http://www.opengis.net/gml/3.2"

    for elem in root.iter():
        tag = elem.tag
        if tag.startswith("{"):
            uri, local = tag[1:].split("}", 1)
            if local == "StrefaPlanistyczna":
                app = uri
        for key, value in elem.attrib.items():
            if key.startswith("{"):
                uri, local = key[1:].split("}", 1)
                if local == "href":
                    xlink = uri

    if app is None:
        # Namespace may be declared on a child rather than visible through
        # the first object in malformed/non-standard files.
        match = re.search(r"\{([^}]+)\}StrefaPlanistyczna", nsmap)
        if match:
            app = match.group(1)

    if app is None:
        return {}

    ns = {"app": app, "xlink": xlink, "gml": gml}
    out = {}

    for obj in root.findall(".//app:StrefaPlanistyczna", ns):
        gid = obj.get(f"{{{gml}}}id") or obj.get("id") or ""
        basic = []
        additional = []

        for kind, target in (
            ("profilPodstawowy", basic),
            ("profilDodatkowy", additional),
        ):
            for p in obj.findall(f"app:{kind}", ns):
                href = p.get(f"{{{xlink}}}href") or ""
                title = p.get(f"{{{xlink}}}title") or ""
                code = href.rsplit("-", 1)[-1] if "KPT-MPZP-" in href else href
                target.append((code, title))

        out[str(gid)] = {"basic": basic, "additional": additional}

    return out


def _extract_strefy(gml_path):
    st_layer = _open_gml_layer(gml_path, "StrefaPlanistyczna")
    ouz_layer = _open_gml_layer(gml_path, "ObszarUzupelnieniaZabudowy")

    declared = _gml_crs(gml_path)
    st_crs = st_layer.crs() if st_layer.crs().isValid() else declared
    ouz_crs = ouz_layer.crs() if ouz_layer.crs().isValid() else declared

    strefy = _feature_records(st_layer)
    ouz = _feature_records(ouz_layer)

    # Store CRS alongside the records without introducing a DataFrame.
    for rec in strefy:
        rec["crs"] = st_crs
    for rec in ouz:
        rec["crs"] = ouz_crs

    return strefy, ouz, _profile_records(gml_path)


def _transform_geometry(geometry, source_crs, target_crs):
    if geometry is None or geometry.isEmpty():
        return QgsGeometry()
    if not source_crs or not source_crs.isValid() or source_crs == target_crs:
        return QgsGeometry(geometry)
    transform = QgsCoordinateTransform(
        source_crs, target_crs, QgsCoordinateTransformContext()
    )
    result = QgsGeometry(geometry)
    result.transform(transform)
    return result


def _multipart_parts(geom):
    if geom is None or geom.isEmpty():
        return []
    if QgsWkbTypes.geometryType(geom.wkbType()) != QgsWkbTypes.PolygonGeometry:
        raise ValueError(
            "Granica MPZP ma niedopuszczalny typ geometrii: "
            f"{QgsWkbTypes.displayString(geom.wkbType())}"
        )
    if not geom.isMultipart():
        return [QgsGeometry(geom)]
    return [QgsGeometry(part) for part in geom.asGeometryCollection()]


def _group_label(value, idx):
    if _is_missing(value) or _safe_text(value) == "":
        return f"Obiekt bez wartości ({idx})"
    return _safe_text(value)


def _group_boundary_objects(mpzp, group_field):
    if not mpzp:
        raise ValueError("Warstwa granicy MPZP nie zawiera obiektów.")

    warnings = []

    if len(mpzp) == 1:
        value = mpzp[0]["attrs"].get(group_field) if group_field else None
        labels = {0: _group_label(value, 1) if group_field else "MPZP"}
        if group_field and _safe_text(value) == "":
            warnings.append(
                f"Pole grupujące '{group_field}' nie zawiera wartości dla "
                "jedynego obiektu. Zastosowano identyfikator techniczny."
            )
        return OrderedDict([(0, [mpzp[0]])]), labels, warnings

    if group_field is None:
        raise ValueError(
            "Warstwa zawiera więcej niż jeden obiekt. "
            "Należy wskazać pole grupujące."
        )

    if group_field not in mpzp[0]["attrs"]:
        raise ValueError(
            f"Wybrane pole grupujące nie istnieje: {group_field}"
        )

    counts = {}
    for rec in mpzp:
        value = _safe_text(rec["attrs"].get(group_field))
        if value:
            counts[value] = counts.get(value, 0) + 1

    repeated = [(v, n) for v, n in counts.items() if n > 1]
    if repeated:
        details = ", ".join(f"'{v}' ({n} ob.)" for v, n in repeated)
        warnings.append(
            f"Pole grupujące '{group_field}' zawiera powtarzające się wartości: "
            f"{details}. Obiekty o tej samej wartości zostaną potraktowane "
            "jako jedna grupa. Jeżeli wartości nie identyfikują jednego MPZP, "
            "wybierz inne pole."
        )

    empty_count = sum(
        1 for rec in mpzp
        if _safe_text(rec["attrs"].get(group_field)) == ""
    )
    if empty_count:
        warnings.append(
            f"Pole grupujące '{group_field}' nie zawiera wartości dla "
            f"{empty_count} obiekt(ów). Obiekty te zostaną zachowane jako "
            "osobna grupa / grupy techniczne."
        )

    groups = OrderedDict()
    labels = {}
    key_to_id = {}
    seen_empty = 0
    next_id = 1

    for rec in mpzp:
        value = _safe_text(rec["attrs"].get(group_field))
        if not value:
            seen_empty += 1
            key = ("__empty__", seen_empty)
            labels[next_id] = f"Obiekt bez wartości ({seen_empty})"
        else:
            key = ("value", value)
            if key not in key_to_id:
                key_to_id[key] = next_id
                labels[next_id] = value
            else:
                next_id = key_to_id[key]
                groups.setdefault(next_id, []).append(rec)
                continue

        key_to_id.setdefault(key, next_id)
        groups.setdefault(next_id, []).append(rec)
        next_id += 1

    return groups, labels, warnings


def _union_intersections(geoms):
    if not geoms:
        return None
    result = QgsGeometry(geoms[0])
    for geom in geoms[1:]:
        result = result.combine(geom)
    return result


def _attrs(rec):
    return rec["attrs"]


def _analyse_strefy_for_part(strefy, profiles, part_geom, target_crs,
                             target_label, part_label, target_area,
                             output_kind):
    st_rows = []
    prof_rows = []
    intersections = []

    for s in strefy:
        s_geom = _transform_geometry(
            s["geometry"], s.get("crs"), target_crs
        )
        if s_geom.isEmpty() or not s_geom.intersects(part_geom):
            continue

        inter = s_geom.intersection(part_geom)
        if inter.isEmpty() or inter.area() <= 0:
            continue

        area_in = float(inter.area())
        intersections.append(inter)
        a = _attrs(s)
        gid = s.get("gml_id")
        p = profiles.get(str(gid), {"basic": [], "additional": []})

        if output_kind == "DWZ":
            row = {
                "Teren inwestycji": target_label,
                "FID źródłowy": target_label.get("_fid") if isinstance(target_label, dict) else None,
            }
        else:
            row = {"MPZP": target_label}

        row.update({
            "Część terenu" if output_kind == "DWZ" else "Część MPZP": part_label,
            "Oznaczenie strefy": _safe_text(a.get("oznaczenie")),
            "Symbol": _safe_text(a.get("symbol")),
            "Powierzchnia POG [m²]": float(s_geom.area()),
            ("Powierzchnia w terenie [m²]" if output_kind == "DWZ"
             else "Powierzchnia w MPZP [m²]"): area_in,
            ("Udział w terenie [%]" if output_kind == "DWZ"
             else "Udział w MPZP [%]"): area_in / target_area if target_area else None,
            "Profil podstawowy": "\n".join(t for _, t in p["basic"]),
            "Profil dodatkowy": "\n".join(t for _, t in p["additional"]),
            "Intensywność max": a.get("maksNadziemnaIntensywnoscZabudowy"),
            "Udział zabudowy max [%]": (
                float(a["maksUdzialPowierzchniZabudowy"]) / 100
                if not _is_missing(a.get("maksUdzialPowierzchniZabudowy"))
                else None
            ),
            "Wysokość max [m]": a.get("maksWysokoscZabudowy"),
            "PBC min [%]": (
                float(a["minUdzialPowierzchniBiologicznieCzynnej"]) / 100
                if not _is_missing(a.get("minUdzialPowierzchniBiologicznieCzynnej"))
                else None
            ),
            "KONTROLA": (
                "WERYFIKACJA – fragment < 1 m²"
                if area_in < TOLERANCE_M2 else ""
            ),
            "gml_id": gid,
        })
        st_rows.append(row)

        for typ, items in (
            ("PODSTAWOWY", p["basic"]),
            ("DODATKOWY", p["additional"]),
        ):
            for code, title in items:
                prow = {
                    "Oznaczenie": _safe_text(a.get("oznaczenie")),
                    "Symbol": _safe_text(a.get("symbol")),
                    "Typ profilu": typ,
                    "kod przeznaczenia": code,
                    "Nazwa": title,
                }
                if output_kind == "DWZ":
                    prow.update({
                        "Teren inwestycji": target_label,
                        "FID źródłowy": (
                            target_label.get("_fid")
                            if isinstance(target_label, dict) else None
                        ),
                        "Część terenu": part_label,
                    })
                else:
                    prow.update({
                        "MPZP": target_label,
                        "Część MPZP": part_label,
                    })
                prof_rows.append(prow)

    return st_rows, prof_rows, intersections


def _ouz_rows_for_part(ouz, part_geom, target_crs, target_label,
                       part_label, part_area, output_kind):
    rows = []
    for o in ouz:
        o_geom = _transform_geometry(
            o["geometry"], o.get("crs"), target_crs
        )
        if o_geom.isEmpty() or not o_geom.intersects(part_geom):
            continue
        inter = o_geom.intersection(part_geom)
        if inter.isEmpty() or inter.area() <= 0:
            continue
        area_in = float(inter.area())
        a = _attrs(o)
        row = {
            "OUZ oznaczenie": _safe_text(a.get("oznaczenie")),
            "Powierzchnia OUZ [m²]": float(o_geom.area()),
            ("Powierzchnia OUZ w terenie [m²]" if output_kind == "DWZ"
             else "Powierzchnia OUZ w MPZP [m²]"): area_in,
            "Udział w terenie [%]" if output_kind == "DWZ"
            else "Udział w MPZP [%]": area_in / part_area if part_area else None,
            "gml_id": o.get("gml_id"),
        }
        if output_kind == "DWZ":
            row.update({
                "Teren inwestycji": target_label,
                "FID źródłowy": (
                    target_label.get("_fid")
                    if isinstance(target_label, dict) else None
                ),
                "Część terenu": part_label,
            })
        else:
            row.update({
                "MPZP": target_label,
                "Część MPZP": part_label,
            })
        rows.append(row)
    return rows


def _read_vector_layer(path, layer_name):
    layer = QgsVectorLayer(
        f"{str(path)}|layername={layer_name}",
        layer_name,
        "ogr",
    )
    if not layer.isValid():
        layer = QgsVectorLayer(str(path), layer_name, "ogr")
    if not layer.isValid():
        raise ValueError(
            f"Nie udało się odczytać warstwy '{layer_name}'."
        )
    return layer


def _vector_records(layer):
    fields = [f.name() for f in layer.fields()]
    result = []
    for feature in layer.getFeatures():
        attrs = {
            name: _field_value(feature, name)
            for name in fields
        }
        result.append({
            "attrs": attrs,
            "geometry": QgsGeometry(feature.geometry()),
            "gml_id": str(feature.id()),
            "crs": layer.crs(),
        })
    return result


def analyse_dwz(gml_path, terrain_path, layer, id_field, selected_fids=None):
    """Analiza terenów inwestycji DWZ względem POG."""
    strefy, ouz, profiles = _extract_strefy(gml_path)

    if not ouz:
        raise ValueError(
            "W POG nie wyznaczono OUZ. W trybie DWZ nie można wygenerować raportu."
        )

    terrain_layer = _read_vector_layer(terrain_path, layer)
    if terrain_layer.featureCount() == 0:
        raise ValueError("Warstwa terenów inwestycji nie zawiera obiektów.")

    fields = [f.name() for f in terrain_layer.fields()]
    if id_field not in fields:
        raise ValueError(
            f"Wybrane pole identyfikujące teren nie istnieje: {id_field}"
        )

    terrain_records = _vector_records(terrain_layer)

    if selected_fids is not None:
        selected = {str(v) for v in selected_fids}
        filtered = []
        for rec in terrain_records:
            source_fid = rec["attrs"].get("_source_fid")
            if source_fid is None:
                source_fid = rec["gml_id"]
            if str(source_fid) in selected:
                filtered.append(rec)
        terrain_records = filtered

    if not terrain_records:
        raise ValueError(
            "Nie znaleziono zaznaczonych obiektów w warstwie terenów inwestycji."
        )

    target_crs = terrain_layer.crs()
    if not target_crs.isValid():
        raise ValueError("Brak CRS w warstwie terenów inwestycji.")

    st_rows = []
    prof_rows = []
    ouz_rows = []
    controls = []

    for seq, area in enumerate(terrain_records, 1):
        attrs = area["attrs"]
        raw_label = _safe_text(attrs.get(id_field))
        label = raw_label if raw_label else f"Teren bez wartości ({seq})"

        source_fid = attrs.get("_source_fid")
        if source_fid is None:
            source_fid = area["gml_id"]

        geom = area["geometry"]
        if geom.isEmpty():
            controls.append({
                "Teren inwestycji": label,
                "FID źródłowy": source_fid,
                "Część terenu": "",
                "Powierzchnia części [m²]": 0.0,
                "Pokrycie POG": 0.0,
                "Brak [m²]": 0.0,
                "KONTROLA": "UWAGA – teren inwestycji nie posiada geometrii.",
            })
            continue

        parts = _multipart_parts(geom)

        for part_no, part_geom in enumerate(parts, 1):
            part_area = float(part_geom.area())
            if part_area <= 0:
                continue

            part_label = f"Cz. {part_no}" if len(parts) > 1 else "Teren inwestycji"
            target = {"label": label, "_fid": source_fid}

            rows, prows, intersection_geoms = _analyse_strefy_for_part(
                strefy, profiles, part_geom, target_crs,
                target, part_label, part_area, "DWZ"
            )

            # Convert internal target wrapper to the actual report label.
            for row in rows:
                row["Teren inwestycji"] = label
                row["FID źródłowy"] = source_fid
            for row in prows:
                row["Teren inwestycji"] = label
                row["FID źródłowy"] = source_fid

            st_rows.extend(rows)
            prof_rows.extend(prows)

            coverage_geom = _union_intersections(intersection_geoms)
            covered = float(coverage_geom.area()) if coverage_geom else 0.0
            gap = max(0.0, part_area - covered)
            coverage = covered / part_area if part_area else 0.0

            msg = (
                f"WERYFIKACJA – pokrycie POG {coverage:.4%}; brak {gap:.3f} m²"
                if gap > TOLERANCE_M2 else ""
            )
            controls.append({
                "Teren inwestycji": label,
                "FID źródłowy": source_fid,
                "Część terenu": part_label,
                "Powierzchnia części [m²]": part_area,
                "Pokrycie POG": coverage,
                "Brak [m²]": gap,
                "KONTROLA": msg,
            })

            orows = _ouz_rows_for_part(
                ouz, part_geom, target_crs, target,
                part_label, part_area, "DWZ"
            )
            for row in orows:
                row["Teren inwestycji"] = label
                row["FID źródłowy"] = source_fid
            ouz_rows.extend(orows)

    return st_rows, prof_rows, ouz_rows, controls


def analyse(gml_path, mpzp_path, layer=None, group_field=None,
            force_single_group=False, mpzp_crs_override=None):
    """Analiza granic MPZP względem POG."""
    strefy, ouz, profiles = _extract_strefy(gml_path)

    mpzp_layer = _read_vector_layer(mpzp_path, layer)
    mpzp = _vector_records(mpzp_layer)
    if not mpzp:
        raise ValueError("Warstwa granicy MPZP nie zawiera obiektów.")

    target_crs = mpzp_layer.crs()
    if mpzp_crs_override:
        override = (
            mpzp_crs_override
            if isinstance(mpzp_crs_override, QgsCoordinateReferenceSystem)
            else QgsCoordinateReferenceSystem(str(mpzp_crs_override))
        )
        if override.isValid():
            target_crs = override

    if not target_crs.isValid():
        raise ValueError(
            "Brak CRS w GML albo warstwie granicy MPZP."
        )

    if len(mpzp) > 1 and force_single_group:
        groups = OrderedDict([(1, mpzp)])
        labels = {1: "MPZP"}
        grouping_warnings = [
            "Wymuszono jedną grupę dla wszystkich obiektów granicy MPZP. "
            "To ustawienie jest przeznaczone wyłącznie do testów / świadomego użycia."
        ]
        gd = GroupingDecision(None, "force_single_group")
    else:
        if len(mpzp) > 1 and group_field is None:
            suggestion = suggest_name_field(
                [f.name() for f in mpzp_layer.fields()]
            )
            group_field = suggestion.field
            gd = suggestion
            if group_field is None:
                raise ValueError(suggestion.reason)
        else:
            gd = GroupingDecision(group_field, "explicitly supplied")

        groups, labels, grouping_warnings = _group_boundary_objects(
            mpzp, group_field
        )

    st_rows = []
    prof_rows = []
    ouz_rows = []
    controls = []

    for warning in grouping_warnings:
        controls.append({
            "MPZP": "",
            "Część MPZP": "",
            "Powierzchnia części [m²]": None,
            "Pokrycie POG": None,
            "Brak [m²]": None,
            "KONTROLA": "UWAGA – " + warning,
        })

    for group_id, frame in groups.items():
        geometries = [
            _transform_geometry(
                rec["geometry"], rec.get("crs", mpzp_layer.crs()), target_crs
            )
            for rec in frame
        ]
        merged = _union_intersections(geometries)
        if merged is None:
            continue

        parts = _multipart_parts(merged)

        for part_no, part_geom in enumerate(parts, 1):
            part_label = f"Cz. {part_no}"
            part_area = float(part_geom.area())
            if part_area <= 0:
                continue

            rows, prows, intersection_geoms = _analyse_strefy_for_part(
                strefy, profiles, part_geom, target_crs,
                labels[group_id], part_label, part_area, "MPZP"
            )
            st_rows.extend(rows)
            prof_rows.extend(prows)

            coverage_geom = _union_intersections(intersection_geoms)
            covered = float(coverage_geom.area()) if coverage_geom else 0.0
            gap = max(0.0, part_area - covered)
            coverage = covered / part_area if part_area else 0.0

            msg = (
                f"WERYFIKACJA – pokrycie POG {coverage:.4%}; brak {gap:.3f} m²"
                if gap > TOLERANCE_M2 else ""
            )
            controls.append({
                "MPZP": labels[group_id],
                "Część MPZP": part_label,
                "Powierzchnia części [m²]": part_area,
                "Pokrycie POG": coverage,
                "Brak [m²]": gap,
                "KONTROLA": msg,
            })

            ouz_rows.extend(_ouz_rows_for_part(
                ouz, part_geom, target_crs, labels[group_id],
                part_label, part_area, "MPZP"
            ))

    return st_rows, prof_rows, ouz_rows, controls, gd, layer
