# Guyana Location Taxonomy

Open data files for Guyana's Local Authority Areas and constituencies, derived from official Guyana Elections Commission (GECOM) Local Government Elections 2023 documents.

## Dataset

The verified constituency dataset contains:

- 10 administrative regions
- 80 Local Authority Areas
- 610 numbered constituencies
- 609 distinct constituency names within regions

Every constituency was extracted from the numbered headings in GECOM's official `Register of Voters for LGE 2023` PDFs. Numbering was checked for completeness within every Local Authority Area.

## Files

| File | Description |
|---|---|
| `data/constituencies.json` | Complete Region -> Local Authority Area -> Constituency hierarchy |
| `data/constituencies.csv` | Flat import-friendly representation with source URLs |
| `data/distinct-constituencies-by-region.json` | Minimal Region -> distinct constituency names representation |
| `data/local-authorities.json` | GECOM Local Authority Areas, Geo Orders, types, and map URLs |
| `data/gazetteer-locations.json` | 6,628 Gazetteer locations with WGS 84 latitude and longitude |
| `data/gazetteer-locations.csv` | Flat GPS-enabled Gazetteer export for application imports |
| `data/local-authority-boundary-crosswalk.json` | GECOM-to-GuyNode polygon crosswalk with coverage and confidence |
| `data/guynode-layer-inventory.csv` | Audited schemas, counts, dates and 2023 constituency-count comparisons |
| `docs/METHODOLOGY.md` | Source, extraction, normalization, and limitations |
| `docs/GUYNODE_BOUNDARY_AUDIT.md` | Spatial-source audit and recommended merge strategy |

## Example

```json
{
  "region_number": 1,
  "region_name": "Barima-Waini",
  "local_authorities": [
    {
      "geo_order": "1.01",
      "name": "PORT KAITUMA MATTHEWS RIDGE/ARAKAKA",
      "type": "NDC",
      "constituencies": [
        {
          "number": 1,
          "name": "CANAL BANK - CITRUS GROVE"
        }
      ]
    }
  ]
}
```

## Authority and scope

This repository is authoritative only with respect to the names and structure printed in GECOM's 2023 Local Government Elections documents. It does not assert that boundaries or names remained unchanged after 2023.

Source: [GECOM LGE 2023 Resource Hub](https://gecom.org.gy/public/home/resource_hub/lge2023)

The Gazetteer files come from the Government of Guyana's ArcGIS National
Gazetteer layer. Their coordinates are returned in WGS 84 (`EPSG:4326`).
Gazetteer points have not been assigned to GECOM constituencies because that
requires authoritative constituency boundary polygons.

## Name normalization

Obvious PDF text-layer spacing defects were corrected for display, such as `A VENUE` to `AVENUE`. When a correction was made, `official_source_name` is retained beside the normalized name in the complete JSON.

## License

Repository code and original documentation are released under the MIT License. The underlying government records remain attributable to GECOM.
