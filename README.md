# FrenchNamesAustralia
French Names Along the Australian Coastline

## MCP server

The project includes a read-only MCP server for structured, bilingual and geographic access to the toponym datasets. See [docs/MCP.md](docs/MCP.md) for tools, local testing and client configuration.

## Files outside the repository

Some scripts read source material kept outside the repo, in the parent `Toponymes/` folder (see `Toponymes/README.md`):

- `scripts/journal_navigation_flinders.py` → `../01_Sources/Journaux_de_bord/Flinders/`, `../01_Sources/Numerisations/flinders_navigation/`
- `rag/convertir_sources.py` → `../01_Sources/Journaux_de_bord/`, `../01_Sources/Bibliographie/`
- `scripts/convert_historique_baudin_tsv_to_json.py` → `../03_Parcours/Chronologies_et_tables/`
