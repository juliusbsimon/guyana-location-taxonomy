# GuyNode Boundary Source Audit

Audit date: 2026-07-25

## Purpose

This audit evaluates GuyNode spatial layers as a bridge between:

- the 80 Local Authority Areas and 610 constituencies published by GECOM for
  the 2023 Local Government Elections; and
- the 6,628 point locations in the Guyana National Gazetteer.

GECOM remains the naming and electoral-structure authority. GuyNode supplies
useful research geometry, but its own catalogue warns that some layers are
compiled or digitized and should be verified before legal, cadastral,
electoral, engineering, or regulatory use.

## Sources inspected

- [GuyNode boundary catalogue](https://www.guynode.com/admin_boundaries.html)
- [Combined local-government areas](https://www.guynode.com/Local_Govt_Areas_Guyana.zip)
- [NDC boundary layer](https://www.guynode.com/All_NDCs.zip)
- [Constituency catalogue](https://www.guynode.com/constituencies.html)
- [Municipality catalogue](https://www.guynode.com/municipalities.html)
- 33 downloadable municipality and constituency archives linked by those
  catalogues

The downloaded shapefiles were inspected directly: DBF schemas and record
counts, projection files, XML metadata dates, layer names, and correspondence
with the GECOM 2023 hierarchy.

## Main findings

### Combined local-government layer

The combined shapefile contains 224 polygon features:

| Status | Features |
|---|---:|
| Amerindian Village | 110 |
| Neighbourhood Democratic Council | 65 |
| Not Classified | 40 |
| Municipality | 8 |
| Conservancy | 1 |

The file was processed/exported in November 2025 and uses Web Mercator
(`EPSG:3857`). Its 2025 packaging date must not be interpreted as proof that
every source boundary was revised in 2025.

After name normalization and manual review:

- 68 of the 80 GECOM 2023 Local Authority Areas can be crosswalked to the
  combined layer;
- 3 additional areas have potentially usable supplemental layers; and
- 9 areas remain unresolved.

The supplemental candidates are:

| Geo Order | GECOM area | Supplemental geometry | Assessment |
|---|---|---|---|
| 2.07 | Annandale/Riverstown | Union of nine constituency polygons | Medium confidence; polygon count agrees with 2023 |
| 8.01 | Municipality of Mahdia | Separate Mahdia boundary | Medium confidence; visually verify against GECOM |
| 9.01 | Municipality of Lethem | Union of six constituency polygons | Low confidence; GECOM 2023 has five constituencies |

The nine unresolved areas are:

1. `2.01` Moruka/Providence
2. `2.02` The Nile/Cozier
3. `4.01` Hauraruni/Yarowkabra
4. `4.02` Lamaha/Yarowkabra
5. `6.01` Plegt Anker/Kortberaad
6. `6.02` Wyburg/Caracas
7. `6.19` No.52/No.63
8. `6.20` No.64/No.74
9. `9.02` Aranaputa/Upper Burro Burro

See `data/local-authority-boundary-crosswalk.json` for the complete 80-area
crosswalk, match method, source and confidence.

### Standalone NDC layer

The standalone layer is named `Guyana_NDCs__v1_2025`, but its attributes
include 2012 population estimates. XML lineage records schema cleanup and an
export in December 2025; it does not document a nationwide redelineation.

It contains only 69 features: 62 marked NDC and 7 marked non-NDC. It also
contains duplicated, unnamed and obsolete records. The combined
local-government layer is therefore a better starting point.

### Constituency layers

Thirty-one extracted shapefile layers were inspected. Twenty-two layers,
covering 191 polygons, have:

- a recognizable 2023 GECOM Local Authority Area; and
- a feature count equal to that area's 2023 constituency count.

This is useful evidence, not proof of boundary equivalence. Several catalogue
entries are explicitly labelled draft, and many lack complete metadata.

Some obvious vintage mismatches remain:

- Mabaruma: 6 polygons versus 7 in GECOM 2023;
- Lethem: 6 versus 5;
- Corriverton: 7 versus 8;
- Bartica: 8 versus 9;
- Farm/Woodlands: 8 versus 9;
- Toevlugt/Patentia: 11 versus 9.

The complete machine-readable inventory is
`data/guynode-layer-inventory.csv`.

## Recommended merge strategy

### Stage 1: regions

Assign every Gazetteer point to one of the ten regional polygons. This should
provide the most complete and stable first-level spatial join.

### Stage 2: Local Authority Areas

Use the combined GuyNode layer with the explicit GECOM crosswalk:

1. reproject Gazetteer points from WGS 84 to the polygon coordinate system, or
   reproject polygons to WGS 84;
2. run point-in-polygon;
3. replace GuyNode display names with the linked GECOM 2023 name;
4. retain the original boundary ID, name, source and confidence;
5. leave unresolved or multiply matched points unassigned.

The output must distinguish `matched`, `outside`, `overlap`, and
`unresolved-boundary` cases.

### Stage 3: supplemental areas

Test Annandale/Riverstown, Mahdia, and Lethem separately. Dissolve
constituency polygons when an outer Local Authority Area boundary is needed.
Compare their outlines visually with the corresponding GECOM 2023 PDF maps.

### Stage 4: unresolved areas

Digitize the nine missing Local Authority Areas from GECOM maps, preferably
using identifiable roads, rivers, canals and coordinates. Store these as a
separate derived layer with the map URL and digitization notes.

### Stage 5: constituencies

Only assign Gazetteer points to constituencies where a layer passes:

- name/Geo Order crosswalk review;
- 2023 constituency-count agreement;
- valid geometry checks;
- overlap/gap checks; and
- visual comparison with the GECOM source map.

Publish constituency results as provisional unless an official digital GECOM
boundary layer becomes available.

## Proposed merged-record fields

```json
{
  "name": "Example settlement",
  "latitude": 6.0,
  "longitude": -58.0,
  "region_number": 4,
  "region_name": "Demerara-Mahaica",
  "gecom_geo_order": "4.11",
  "local_authority_name": "BETTER HOPE/LA BONNE INTENTION",
  "boundary_name": "Better Hope/LBI",
  "boundary_source": "GuyNode",
  "boundary_match_method": "point_in_polygon",
  "boundary_confidence": "high",
  "constituency_number": null,
  "constituency_name": null
}
```

No record should receive a constituency or Local Authority Area solely through
fuzzy name matching when spatial geometry is unavailable.
