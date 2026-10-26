#!/usr/bin/env python3
"""
Preprocess DOE contractor CSV into geocoded JSON for map visualization.
Geocodes via zip code centroids, categorizes NAICS into visual groups,
and identifies contract relationship links.
"""

import csv
import json
import re
import sys
from collections import defaultdict

import pgeocode


def categorize_naics(naics_desc):
    """Map NAICS descriptions into visual category groups."""
    if not naics_desc:
        return "Other Services"

    desc = naics_desc.upper()

    # R&D / Labs
    if any(kw in desc for kw in [
        "RESEARCH", "LABORATORY", "LABORATOR", "R&D", "SCIENTIFIC",
        "TESTING", "PHYSICAL SCIENCE", "LIFE SCIENCE"
    ]):
        return "Research & Labs"

    # IT / Cyber
    if any(kw in desc for kw in [
        "COMPUTER", "SOFTWARE", "CYBER", "DATA PROCESSING", "TELECOM",
        "INFORMATION TECH", "COMPUTING", "WEB HOSTING", "CLOUD"
    ]):
        return "IT & Cyber"

    # Construction / Facilities
    if any(kw in desc for kw in [
        "CONSTRUCTION", "BUILDING", "JANITORIAL", "CUSTODIAL",
        "FACILITIES", "PLUMBING", "ELECTRICAL CONTRACTOR", "HVAC",
        "DEMOLITION", "EXCAVATION", "ROOFING", "PAVING", "CONCRETE",
        "DRYWALL", "PAINTING", "FLOORING", "CARPENTRY"
    ]):
        return "Construction & Facilities"

    # Engineering
    if any(kw in desc for kw in [
        "ENGINEERING", "ARCHITECT", "SURVEYING", "DRAFTING"
    ]):
        return "Engineering"

    # Environmental
    if any(kw in desc for kw in [
        "ENVIRONMENTAL", "REMEDIATION", "WASTE", "HAZARDOUS",
        "POLLUTION", "RECYCLING", "WATER TREATMENT"
    ]):
        return "Environmental"

    # Security / Defense
    if any(kw in desc for kw in [
        "SECURITY", "GUARD", "INVESTIGATION", "INTELLIGENCE",
        "DEFENSE", "ARMORED", "SURVEILLANCE"
    ]):
        return "Security & Defense"

    # Management / Consulting
    if any(kw in desc for kw in [
        "MANAGEMENT", "CONSULTING", "STAFFING", "HUMAN RESOURCE",
        "TRAINING", "ADMINISTRATIVE", "ACCOUNTING", "LEGAL",
        "PUBLIC RELATIONS", "MARKETING"
    ]):
        return "Management & Consulting"

    # Energy / Utilities
    if any(kw in desc for kw in [
        "ELECTRIC", "ENERGY", "NUCLEAR", "POWER", "UTILITY",
        "NATURAL GAS", "PETROLEUM", "SOLAR", "WIND", "FOSSIL",
        "FUEL", "PIPELINE", "TURBINE", "GENERATOR"
    ]):
        return "Energy & Utilities"

    # Manufacturing
    if any(kw in desc for kw in [
        "MANUFACTUR", "INSTRUMENT", "MACHINERY", "EQUIPMENT",
        "FABRICAT", "ASSEMBLY", "INDUSTRIAL", "METAL", "MACHINE SHOP",
        "TOOL", "VALVE", "PUMP", "MOTOR", "SEMICONDUCTOR"
    ]):
        return "Manufacturing"

    # Transportation / Logistics
    if any(kw in desc for kw in [
        "TRANSPORT", "FREIGHT", "SHIPPING", "LOGISTICS", "TRUCKING",
        "WAREHOUSE", "COURIER", "MOVING", "STORAGE"
    ]):
        return "Transportation & Logistics"

    return "Other Services"


CATEGORY_STYLES = {
    "Research & Labs":         {"color": "#00e5ff", "shape": "hexagon"},
    "IT & Cyber":              {"color": "#7c4dff", "shape": "diamond"},
    "Construction & Facilities": {"color": "#ff9100", "shape": "square"},
    "Engineering":             {"color": "#00e676", "shape": "triangle"},
    "Environmental":           {"color": "#76ff03", "shape": "pentagon"},
    "Security & Defense":      {"color": "#ff1744", "shape": "star"},
    "Management & Consulting": {"color": "#ffd740", "shape": "circle"},
    "Energy & Utilities":      {"color": "#ff6d00", "shape": "bolt"},
    "Manufacturing":           {"color": "#e040fb", "shape": "gear"},
    "Transportation & Logistics": {"color": "#18ffff", "shape": "arrow"},
    "Other Services":          {"color": "#b0bec5", "shape": "circle"},
}


def parse_dollar(val):
    """Parse dollar string to float."""
    if not val:
        return 0.0
    try:
        return float(val.replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return 0.0


def truncate_text(text, max_len=300):
    """Truncate text with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def main():
    csv_path = "/Users/rstarzl/Documents/GitHub/DOE_RedTeam/doe_contractor_due_diligence.csv"

    print("Loading CSV...")
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"  {len(rows)} rows loaded")

    # Initialize geocoder
    print("Initializing geocoder...")
    nomi = pgeocode.Nominatim("us")

    # Collect unique zip codes for batch geocoding
    zip_codes = set()
    for r in rows:
        zc = r.get("zip_code", "").strip()[:5]
        if zc and len(zc) == 5:
            zip_codes.add(zc)

    print(f"  Geocoding {len(zip_codes)} unique zip codes...")
    zip_coords = {}
    for zc in zip_codes:
        result = nomi.query_postal_code(zc)
        if result is not None and not (result.latitude != result.latitude):  # NaN check
            zip_coords[zc] = (float(result.latitude), float(result.longitude))

    print(f"  Successfully geocoded {len(zip_coords)} zip codes")

    # Build contract relationship map
    print("Building contract relationships...")
    contract_to_contractors = defaultdict(set)
    for idx, r in enumerate(rows):
        contract_ids = r.get("contract_id_numbers", "")
        for cid in contract_ids.split(" | "):
            cid = cid.strip()
            if cid and cid != "+4 more":
                contract_to_contractors[cid].add(idx)

    # Find relationships (shared contracts)
    relationships = []
    seen_pairs = set()
    for cid, contractor_indices in contract_to_contractors.items():
        if len(contractor_indices) > 1:
            indices = sorted(contractor_indices)
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    pair = (indices[i], indices[j])
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        relationships.append({
                            "source": indices[i],
                            "target": indices[j],
                            "contract_id": cid
                        })

    print(f"  Found {len(relationships)} contractor relationships")

    # Process contractors
    print("Processing contractors...")
    contractors = []
    skipped = 0

    for idx, r in enumerate(rows):
        zc = r.get("zip_code", "").strip()[:5]
        coords = zip_coords.get(zc)

        if not coords:
            skipped += 1
            continue

        lat, lon = coords

        # Add small jitter so overlapping markers don't stack exactly
        import hashlib
        name_hash = int(hashlib.md5(r.get("contractor_name", "").encode()).hexdigest()[:8], 16)
        lat += (name_hash % 100 - 50) * 0.001
        lon += ((name_hash >> 8) % 100 - 50) * 0.001

        naics_desc = r.get("naics_descriptions", "")
        # Take first NAICS if multiple
        first_naics = naics_desc.split(" | ")[0] if " | " in naics_desc else naics_desc
        category = categorize_naics(first_naics)

        # Parse obligation value for marker sizing
        obligation = parse_dollar(r.get("sum_federal_action_obligation", ""))

        # Parse key personnel
        personnel = []
        kp_raw = r.get("key_personnel", "")
        if kp_raw:
            for person in kp_raw.split(" | ")[:10]:
                personnel.append(person.strip())

        contractor = {
            "id": idx,
            "name": r.get("contractor_name", "").strip(),
            "dba": r.get("doing_business_as", "").strip(),
            "parent": r.get("parent_name", "").split(" | ")[0].strip() if r.get("parent_name") else "",
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "address": r.get("physical_address", "").strip(),
            "city": r.get("city", "").strip(),
            "state": r.get("state_code", "").strip(),
            "zip": r.get("zip_code", "").strip(),
            "category": category,
            "style": CATEGORY_STYLES[category],
            "naics": first_naics.strip(),
            "naics_code": r.get("naics_codes", "").split(".")[0].strip() if r.get("naics_codes") else "",
            "psc": r.get("psc_descriptions", "").split(" | ")[0].strip() if r.get("psc_descriptions") else "",
            "role": truncate_text(r.get("primary_role_for_doe", ""), 500),
            "contract_ids": [c.strip() for c in r.get("contract_id_numbers", "").split(" | ") if c.strip() and "more" not in c][:10],
            "fiscal_years": r.get("fiscal_years_seen", "").strip(),
            "performance_start": r.get("period_of_performance_start", "").strip(),
            "performance_end": r.get("period_of_performance_current_end_latest", "").strip(),
            "awarding_agencies": [a.strip() for a in r.get("awarding_sub_agencies", "").split(" | ") if a.strip()][:5],
            "funding_agencies": [a.strip() for a in r.get("funding_sub_agencies", "").split(" | ") if a.strip()][:5],
            "obligation": obligation,
            "obligation_fmt": f"${obligation:,.2f}" if obligation else "N/A",
            "max_award": parse_dollar(r.get("max_potential_total_value_of_award", "")),
            "max_award_fmt": f"${parse_dollar(r.get('max_potential_total_value_of_award', '')):,.2f}",
            "business_size": r.get("business_size_determination", "").strip(),
            "small_business": "SMALL BUSINESS" in r.get("business_size_determination", "").upper(),
            "woman_owned": r.get("woman_owned_flag", "").strip().lower() in ("yes", "true", "1"),
            "veteran_owned": r.get("veteran_owned_flag", "").strip().lower() in ("yes", "true", "1"),
            "minority_owned": r.get("minority_owned_flag", "").strip().lower() in ("yes", "true", "1"),
            "for_profit": r.get("for_profit_flag", "").strip().lower() in ("yes", "true", "1"),
            "nonprofit": r.get("nonprofit_flag", "").strip().lower() in ("yes", "true", "1"),
            "personnel": personnel,
            "url": r.get("company_url", "").strip(),
            "phone": r.get("phone_numbers", "").strip(),
            "email": r.get("emails", "").strip(),
            "uei": r.get("recipient_uei", "").strip(),
            "cage": r.get("cage_code", "").strip(),
            "record_count": int(r.get("record_count", "0") or "0"),
            "contract_count": int(r.get("distinct_contract_count", "0") or "0"),
            "award_types": r.get("award_types", "").strip(),
            "pricing_types": r.get("contract_pricing_types", "").strip(),
        }
        contractors.append(contractor)

    print(f"  Processed {len(contractors)} contractors ({skipped} skipped - no geocode)")

    # Remap relationship indices to match the new contractor list
    old_to_new = {}
    for new_idx, c in enumerate(contractors):
        old_to_new[c["id"]] = new_idx

    valid_relationships = []
    for rel in relationships:
        src = old_to_new.get(rel["source"])
        tgt = old_to_new.get(rel["target"])
        if src is not None and tgt is not None:
            valid_relationships.append({
                "source": src,
                "target": tgt,
                "contract_id": rel["contract_id"]
            })

    print(f"  {len(valid_relationships)} valid relationships after remapping")

    # Category summary
    cat_counts = defaultdict(int)
    for c in contractors:
        cat_counts[c["category"]] += 1

    print("\nCategory distribution:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        style = CATEGORY_STYLES[cat]
        print(f"  {count:4d} - {cat} ({style['shape']}, {style['color']})")

    # Build output
    output = {
        "generated": "2026-03-23",
        "total_contractors": len(contractors),
        "total_relationships": len(valid_relationships),
        "categories": CATEGORY_STYLES,
        "category_counts": dict(cat_counts),
        "contractors": contractors,
        "relationships": valid_relationships,
    }

    out_path = "/Users/rstarzl/Documents/GitHub/DOE_RedTeam/frontend/static/contractors.json"
    print(f"\nWriting to {out_path}...")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    file_size = len(json.dumps(output, separators=(",", ":")))
    print(f"  JSON size: {file_size / 1024 / 1024:.1f} MB")
    print("Done!")


if __name__ == "__main__":
    main()
