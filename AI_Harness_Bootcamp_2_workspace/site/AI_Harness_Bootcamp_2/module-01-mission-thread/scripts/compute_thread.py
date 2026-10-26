#!/usr/bin/env python3
"""Reference arithmetic for the fictional Cold Lantern practice case.

Default output shows each result function's arithmetic. ``--json`` prints only
the values the visible checker and the oracle compare.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

MDT = timezone(timedelta(hours=-6), name="MDT")
UTC = timezone.utc

SCANNED_TOTES = 12
RELEASED_TOTES = 10
KITS_PER_TOTE = 18
GROSS_KG_PER_TOTE = 132
RACK_KG = 84
PAYLOAD_LIMIT_KG = 1650
LOAD_MINUTES = 20
DEPOT_TO_GATE_MINUTES = 28
GATE_TO_CLINIC_MINUTES = 40


def local_label(value: datetime) -> str:
    return value.astimezone(MDT).strftime("%H:%M MDT")


def _zulu(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%H:%MZ")


def _mdt_hours_behind_utc() -> int:
    offset = MDT.utcoffset(datetime(2026, 10, 6, 20, 50, tzinfo=UTC))
    if offset is None:
        raise RuntimeError("MDT offset is missing")
    return -int(offset.total_seconds() // 3600)


def _decision() -> datetime:
    return datetime(2026, 10, 6, 14, 5, tzinfo=MDT)


def _deadline() -> datetime:
    return datetime(2026, 10, 6, 16, 0, tzinfo=MDT)


def _v5_close() -> datetime:
    return datetime(2026, 10, 6, 20, 50, tzinfo=UTC)


def _v6_close() -> datetime:
    return datetime(2026, 10, 6, 21, 20, tzinfo=UTC)


def _departure() -> datetime:
    return _decision() + timedelta(minutes=LOAD_MINUTES)


def _gate() -> datetime:
    return _departure() + timedelta(minutes=DEPOT_TO_GATE_MINUTES)


def _clinic() -> datetime:
    return _gate() + timedelta(minutes=GATE_TO_CLINIC_MINUTES)


def scanned_kits() -> int:
    return SCANNED_TOTES * KITS_PER_TOTE


def usable_kits() -> int:
    return RELEASED_TOTES * KITS_PER_TOTE


def released_mass_kg() -> int:
    return RELEASED_TOTES * GROSS_KG_PER_TOTE


def mission_payload_kg() -> int:
    return released_mass_kg() + RACK_KG


def payload_margin_kg() -> int:
    return PAYLOAD_LIMIT_KG - mission_payload_kg()


def all_scanned_payload_kg() -> int:
    return SCANNED_TOTES * GROSS_KG_PER_TOTE + RACK_KG


def all_scanned_overage_kg() -> int:
    return all_scanned_payload_kg() - PAYLOAD_LIMIT_KG


def v5_closure_local() -> str:
    return local_label(_v5_close())


def earliest_departure() -> str:
    return local_label(_departure())


def earliest_gate_arrival() -> str:
    return local_label(_gate())


def v5_gate_margin_minutes() -> int:
    return int((_v5_close() - _gate().astimezone(UTC)).total_seconds() // 60)


def clinic_arrival_if_admitted() -> str:
    return local_label(_clinic())


def clinic_margin_if_admitted_minutes() -> int:
    return int((_deadline() - _clinic()).total_seconds() // 60)


def v6_closure_local() -> str:
    return local_label(_v6_close())


def v6_gate_margin_minutes() -> int:
    return int((_v6_close() - _gate().astimezone(UTC)).total_seconds() // 60)


def calculations() -> list[tuple[str, str, object]]:
    """Each result function, the arithmetic it uses, and the value it returns."""
    scanned = scanned_kits()
    usable = usable_kits()
    released_mass = released_mass_kg()
    payload = mission_payload_kg()
    margin = payload_margin_kg()
    all_payload = all_scanned_payload_kg()
    overage = all_scanned_overage_kg()
    closure = v5_closure_local()
    departure = earliest_departure()
    gate = earliest_gate_arrival()
    gate_margin = v5_gate_margin_minutes()
    clinic = clinic_arrival_if_admitted()
    clinic_margin = clinic_margin_if_admitted_minutes()
    changed_closure = v6_closure_local()
    changed_margin = v6_gate_margin_minutes()
    hours = _mdt_hours_behind_utc()
    return [
        ("scanned_kits", f"{SCANNED_TOTES} totes * {KITS_PER_TOTE} kits/tote = {scanned} kits", scanned),
        ("usable_kits", f"{RELEASED_TOTES} released totes * {KITS_PER_TOTE} kits/tote = {usable} kits", usable),
        ("released_mass_kg", f"{RELEASED_TOTES} released totes * {GROSS_KG_PER_TOTE} kg/tote = {released_mass} kg", released_mass),
        ("mission_payload_kg", f"{released_mass} kg + {RACK_KG} kg rack = {payload} kg", payload),
        ("payload_margin_kg", f"{PAYLOAD_LIMIT_KG} kg - {payload} kg = {margin} kg", margin),
        ("all_scanned_payload_kg", f"{SCANNED_TOTES} totes * {GROSS_KG_PER_TOTE} kg/tote + {RACK_KG} kg rack = {all_payload} kg", all_payload),
        ("all_scanned_overage_kg", f"{all_payload} kg - {PAYLOAD_LIMIT_KG} kg = {overage} kg", overage),
        ("v5_closure_local", f"{_zulu(_v5_close())} - {hours} h = {closure}", closure),
        ("earliest_departure", f"{local_label(_decision())} + {LOAD_MINUTES} min = {departure}", departure),
        ("earliest_gate_arrival", f"{departure} + {DEPOT_TO_GATE_MINUTES} min = {gate}", gate),
        ("v5_gate_margin_minutes", f"{closure} - {gate} = {gate_margin} min", gate_margin),
        ("clinic_arrival_if_admitted", f"{gate} + {GATE_TO_CLINIC_MINUTES} min = {clinic}", clinic),
        ("clinic_margin_if_admitted_minutes", f"{local_label(_deadline())} - {clinic} = {clinic_margin} min", clinic_margin),
        ("v6_closure_local", f"{_zulu(_v6_close())} - {hours} h = {changed_closure}", changed_closure),
        ("v6_gate_margin_minutes", f"{changed_closure} - {gate} = {changed_margin} min", changed_margin),
    ]


def compute() -> dict[str, object]:
    return {name: value for name, _formula, value in calculations()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()
    if args.json:
        print(json.dumps(compute(), indent=2, sort_keys=True))
    else:
        for name, formula, _value in calculations():
            print(f"{name}(): {formula}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
