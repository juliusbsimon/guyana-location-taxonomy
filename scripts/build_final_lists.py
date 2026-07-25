import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"
source=list(csv.DictReader((OUT/"guyana-gecom-authoritative-constituencies.csv").open(encoding="utf-8")))

replacements=[
    ("HEA VEN","HEAVEN"),
    ("A VENUE","AVENUE"),
    ("V ALLEY","VALLEY"),
    ("CANV AS","CANVAS"),
    ("SA V ANNAH","SAVANNAH"),
    ("STRATHA VON","STRATHAVON"),
    ("HUIS T’","HUIST’"),
    ("HUIS T'","HUIST'"),
    ("MC DOOM","MCDOOM"),
    ("NON PARIEL","NON PAREIL"),
    ("TABTINGA","TABATINGA"),
]

def display_name(name):
    value=re.sub(r"\s+"," ",name).strip()
    for old,new in replacements:
        value=value.replace(old,new)
    value=re.sub(r"\s+([,.;:)])",r"\1",value)
    value=re.sub(r"([(])\s+",r"\1",value)
    value=re.sub(r"\s*-\s*"," - ",value)
    value=re.sub(r"\s+"," ",value).strip()
    return value

records=[]
for row in source:
    official=row["constituency_name"]
    normalized=display_name(official)
    records.append({
        "region_number":int(row["region_number"]),
        "region_name":row["region_name"],
        "geo_order":row["geo_order"],
        "local_authority_name":row["local_authority_name"],
        "local_authority_type":row["local_authority_type"],
        "constituency_number":int(row["constituency_number"]),
        "constituency_name":normalized,
        "official_source_name":official,
        "name_normalized":normalized != official,
        "source":"GECOM Register of Voters for LGE 2023",
        "source_url":row["source_url"],
    })

with (OUT/"guyana-final-verified-constituencies.csv").open("w",encoding="utf-8",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(records[0]))
    writer.writeheader(); writer.writerows(records)

regions=[]
for region_number in range(1,11):
    region_rows=[r for r in records if r["region_number"]==region_number]
    authorities=[]
    for geo in sorted({r["geo_order"] for r in region_rows},key=lambda s:[int(x) for x in s.split(".")]):
        rows=[r for r in region_rows if r["geo_order"]==geo]
        authorities.append({
            "geo_order":geo,
            "name":rows[0]["local_authority_name"],
            "type":rows[0]["local_authority_type"],
            "constituencies":[{
                "number":r["constituency_number"],
                "name":r["constituency_name"],
                **({"official_source_name":r["official_source_name"]} if r["name_normalized"] else {})
            } for r in rows]
        })
    regions.append({
        "region_number":region_number,
        "region_name":region_rows[0]["region_name"],
        "local_authorities":authorities
    })

full={
    "title":"Guyana Local Authority Constituencies",
    "authority":"Guyana Elections Commission (GECOM)",
    "source_dataset":"Register of Voters for Local Government Elections 2023",
    "verification_status":"All records extracted from numbered constituency headings in the 80 official GECOM voter-register PDFs.",
    "total_regions":10,
    "total_local_authorities":80,
    "total_constituencies":len(records),
    "regions":regions
}
(OUT/"guyana-final-verified-constituencies.json").write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding="utf-8")

distinct_regions=[]
for region in regions:
    unique={}
    for authority in region["local_authorities"]:
        for constituency in authority["constituencies"]:
            name=constituency["name"]
            key=re.sub(r"[^A-Z0-9]","",name.upper())
            unique.setdefault(key,name)
    distinct_regions.append({
        "region_number":region["region_number"],
        "region_name":region["region_name"],
        "constituencies":sorted(unique.values(),key=str.casefold)
    })
distinct={
    "authority":"Guyana Elections Commission (GECOM)",
    "source_dataset":"Register of Voters for Local Government Elections 2023",
    "regions":distinct_regions,
    "total_distinct_constituencies":sum(len(r["constituencies"]) for r in distinct_regions)
}
(OUT/"guyana-final-distinct-constituencies-by-region.json").write_text(json.dumps(distinct,ensure_ascii=False,indent=2),encoding="utf-8")

print(json.dumps({
    "records":len(records),
    "normalized_names":sum(r["name_normalized"] for r in records),
    "distinct_region_names":distinct["total_distinct_constituencies"]
},indent=2))
