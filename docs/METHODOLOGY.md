# Methodology

## Sources

The primary sources are the 80 GECOM `Register of Voters for Local Government Elections 2023` PDFs linked from the GECOM LGE 2023 Resource Hub.

The Local Authority Area map collection was used as a secondary visual reference. Earlier OCR-only map results were not used as the final authority when searchable register headings were available.

## Extraction

Each voter-register PDF repeatedly prints:

1. Local Authority Area;
2. constituency heading;
3. constituency number.

Those repeated blocks were parsed from every page. Records were grouped by GECOM Geo Order and constituency number. A completeness check required numbering to be contiguous from 1 through the highest constituency number for every Local Authority Area.

Final validation:

- 80 of 80 Local Authority Areas complete;
- 610 constituency records;
- no missing constituency numbers.

## Normalization

Official wording and capitalization were preserved. A small set of obvious PDF text-layer defects was normalized for display:

- split words such as `A VENUE`, `V ALLEY`, and `CANV AS`;
- inconsistent whitespace around punctuation;
- clear character-spacing artefacts such as `HEA VEN`.

The original extracted heading is retained as `official_source_name` whenever it differs from the normalized display name.

## Known limitations

- This is a 2023 electoral/administrative reference, not a guarantee of current boundaries.
- Constituency names are not exact-locality boundaries.
- Some official headings contain repeated or very similar place names; those are preserved rather than silently merged.
- Boundary geometries are not included.

## Reproducibility

Source URLs are included in the CSV. The scripts directory contains the extraction and finalization programs used to build the published files.
