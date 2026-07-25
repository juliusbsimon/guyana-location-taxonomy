import csv
import json
import re
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REGISTER_DIR = ROOT / "work" / "gecom-voter-registers-2023"
AUTHORITY_PATH = ROOT / "work" / "bigmarket-location-package" / "database" / "seeders" / "data" / "local_authorities.json"
OUTPUT_DIR = ROOT / "outputs"

authorities = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8-sig"))
authority_by_geo = {a["geo_order"]: a for a in authorities}
register_manifest = json.loads((REGISTER_DIR / "manifest.json").read_text(encoding="utf-8"))

region_names = {
    1: "Barima-Waini",
    2: "Pomeroon-Supenaam",
    3: "Essequibo Islands-West Demerara",
    4: "Demerara-Mahaica",
    5: "Mahaica-Berbice",
    6: "East Berbice-Corentyne",
    7: "Cuyuni-Mazaruni",
    8: "Potaro-Siparuni",
    9: "Upper Takutu-Upper Essequibo",
    10: "Upper Demerara-Berbice",
}

def clean_name(value):
    value = value.replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value).strip(" :-")
    return value

records = []
audits = []
for item in register_manifest:
    geo = item["geo_order"]
    authority = authority_by_geo[geo]
    pdf = REGISTER_DIR / item["local_file"]
    found = {}
    page_count = 0

    for page_number, page in enumerate(PdfReader(str(pdf)).pages, 1):
        page_count += 1
        text = page.extract_text() or ""
        # Voter-list pages repeat this stable block:
        # "Local Authority Area:" + official constituency heading +
        # "Constituency Name:" ... "Constituency #: N".
        # The heading may wrap across multiple lines.
        for match in re.finditer(
            r"Local Authority Area:\s*\r?\n(.*?)Constituency Name:\s*\r?\n.*?"
            r"Constituency\s*#:\s*(\d{1,2})",
            text,
            flags=re.I | re.S,
        ):
            name = clean_name(match.group(1))
            number = int(match.group(2))
            # Exclude accidental captures of table headings or authority labels.
            if not name or "LOCAL AUTHORITY AREA" in name.upper() or len(name) > 250:
                continue
            found.setdefault(number, {
                "name": name,
                "first_source_page": page_number,
            })

    numbers = sorted(found)
    max_number = max(numbers, default=0)
    missing = [n for n in range(1, max_number + 1) if n not in found]
    for number in numbers:
        records.append({
            "region_number": authority["region_id"],
            "region_name": region_names[authority["region_id"]],
            "geo_order": geo,
            "local_authority_name": authority["name"],
            "local_authority_type": authority["authority_type"],
            "constituency_number": number,
            "constituency_name": found[number]["name"],
            "source": "GECOM Register of Voters for LGE 2023",
            "source_url": item["url"],
            "source_page_first_observed": found[number]["first_source_page"],
        })
    audits.append({
        "geo_order": geo,
        "local_authority_name": authority["name"],
        "pdf_pages": page_count,
        "constituencies_extracted": len(numbers),
        "highest_constituency_number": max_number,
        "missing_numbers": missing,
        "status": "COMPLETE" if numbers and not missing else "INCOMPLETE",
    })

records.sort(key=lambda r: (
    r["region_number"],
    [int(x) for x in r["geo_order"].split(".")],
    r["constituency_number"],
))

with (OUTPUT_DIR / "guyana-gecom-authoritative-constituencies.json").open("w", encoding="utf-8") as f:
    json.dump({
        "source": "GECOM Register of Voters for Local Government Elections 2023",
        "regions": [
            {
                "region_number": region,
                "region_name": region_names[region],
                "local_authorities": [
                    {
                        "geo_order": geo,
                        "name": authority_by_geo[geo]["name"],
                        "type": authority_by_geo[geo]["authority_type"],
                        "constituencies": [
                            {
                                "number": r["constituency_number"],
                                "name": r["constituency_name"],
                            }
                            for r in records if r["geo_order"] == geo
                        ],
                    }
                    for geo in sorted(
                        [a["geo_order"] for a in authorities if a["region_id"] == region],
                        key=lambda v: [int(x) for x in v.split(".")],
                    )
                ],
            }
            for region in range(1, 11)
        ],
        "total_local_authorities": len(authorities),
        "total_constituencies": len(records),
    }, f, ensure_ascii=False, indent=2)

fields = list(records[0])
with (OUTPUT_DIR / "guyana-gecom-authoritative-constituencies.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fields)
    writer.writeheader()
    writer.writerows(records)

with (OUTPUT_DIR / "guyana-gecom-authoritative-constituencies-audit.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, list(audits[0]))
    writer.writeheader()
    writer.writerows(audits)

summary = {
    "local_authorities_processed": len(audits),
    "constituencies_extracted": len(records),
    "complete_authorities": sum(a["status"] == "COMPLETE" for a in audits),
    "incomplete_authorities": [a for a in audits if a["status"] != "COMPLETE"],
}
(OUTPUT_DIR / "guyana-gecom-authoritative-constituencies-summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
