# Gazetteer Boundary Merge

Run date: 2026-07-25

## Result

All 6,628 National Gazetteer records were tested against the audited GuyNode
boundary layers.

| Result | Records |
|---|---:|
| Region assigned | 6,411 |
| Outside the combined regional partition | 217 |
| Local Authority Area assigned | 1,225 |
| No supported Local Authority Area assignment | 5,403 |
| Local Authority Area overlaps | 0 |

Local-authority confidence among the 1,225 assignments:

| Confidence | Records |
|---|---:|
| High | 1,171 |
| Medium | 40 |
| Low | 14 |

The low-confidence records are from the supplemental Lethem constituency
union. Its six polygons do not agree with the five constituencies in the GECOM
2023 hierarchy, so those assignments must remain provisional.

## Why most locations are unassigned

The Gazetteer includes rivers, creeks, mountains, waterfalls, islands and
other natural features across the country. NDCs and municipalities do not
cover the whole territory. An unassigned Local Authority Area is therefore
often correct rather than a data failure.

For example, the largest unassigned classes include more than 1,400 rivers and
1,400 creeks. Among the 708 records explicitly classified as `Village`, 557
received a Local Authority Area and 151 did not.

## Quality corrections made during the merge

Two seemingly useful supplemental layers were rejected after spatial testing:

- **Annandale/Riverstown:** its nine-polygon union overlapped
  Charity/Urasara for all 18 affected Gazetteer records.
- **Mahdia:** its single polygon captured 207 features across a broad mining
  and drainage area, including 106 creeks and 30 rivers. It is not a
  defensible municipal boundary.

Rejecting these layers removed all Local Authority Area overlaps from the
final output.

## Fields

Each merged record preserves the Gazetteer fields and adds:

- `region_match_status`
- `region_number`
- `region_name`
- `gecom_geo_order`
- `local_authority_name`
- `local_authority_type`
- `local_authority_match_status`
- `boundary_name`
- `boundary_coverage_status`
- `boundary_confidence`
- `boundary_source_url`

No locality was assigned through name similarity alone. Names were used only
to build the audited boundary crosswalk; actual location assignment was
performed by point-in-polygon.

## Remaining boundary work

Eleven GECOM 2023 Local Authority Areas still require new or corrected
geometry:

1. Moruka/Providence
2. The Nile/Cozier
3. Annandale/Riverstown
4. Hauraruni/Yarowkabra
5. Lamaha/Yarowkabra
6. Plegt Anker/Kortberaad
7. Wyburg/Caracas
8. No.52/No.63
9. No.64/No.74
10. Municipality of Mahdia
11. Aranaputa/Upper Burro Burro

The next improvement should digitize and validate these eleven areas from the
GECOM 2023 maps, then rerun the same merge and compare the quality report.
