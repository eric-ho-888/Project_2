# EV Charging Analysis — HDB Carparks and Residential Planning

## Purpose

This folder contains the code and supporting outputs contributed to the team's Singapore EV Charging Data Platform project. The analysis extends islandwide EV charging data to examine charging points associated with HDB carparks, historical charging availability, geographic differences in observed occupancy, and residential development as a planning consideration.

The files are intended for consolidation into the team GitHub repository. They do **not** include copies of the underlying BigQuery tables or large source GeoJSON datasets.

## Contents

| Folder | Contents |
| --- | --- |
| `dbt_models/` | The copied dbt `models/` directory and `dbt_project.yml`, including transformations used by the analysis. |
| `queries/` | Saved BigQuery SQL queries for matching summaries, availability comparisons, AC/DC distribution and occupancy rankings. |
| `notebooks/` | Jupyter notebooks for spatial analysis, maps and future residential development. |
| `visualisations/` | Interactive Plotly HTML maps for HDB-linked occupancy and strong-match candidate coverage. |
| `results/` | Optional exported results, if provided. |

Filenames within these folders are preserved from the original project. The two HTML maps may be named `Singapore_EV_Occupancy_Map.html` and `Singapore_EV_Coverage_Map.html`.

## Data sources and access

1. **LTA DataMall — EV charging point data:** The team's BigQuery environment holds the historical 15-minute charging-point observations and derived dbt tables. Teammates already have access to the BigQuery data.
2. **HDB carpark information:** Downloaded from [data.gov.sg](https://data.gov.sg/). Used for HDB carpark reference locations and address matching. Search for the HDB carpark information dataset and check the notebook for the expected fields and file path.
3. **HDB public housing buildings under construction:** Available through [data.gov.sg](https://data.gov.sg/). Used as contextual development records, **not** a verified schedule of future household occupation.
4. **URA planning-area boundaries and Master Plan 2025 land use:** Government geospatial datasets used for geographic assignment and development context. Consult the relevant notebooks for the actual GeoJSON filenames and relative paths.

Government source files are not bundled. Download the relevant versions and place them in the paths expected by the notebooks, or adjust the notebook paths. Source datasets can change; reproducing historical outputs may require the same source version and observation window.

## Methodology

### HDB carpark matching

Charging points were associated with HDB carparks using (a) geographic proximity, with a **50-metre threshold for a strong candidate match**, and (b) sufficient standardised address or location-name evidence, including HDB block-range matching. Proximity alone does not establish that a charging point belongs to a particular carpark. A missing strong match does not establish that a carpark has no chargers.

### Availability analysis

Individual charging points were provisionally grouped into charging **locations** using standardised location attributes. At a complete location observation, a location was counted as having availability if **at least one connector was reported Available**. These location-level percentages differ from the percentage of individual charging-point observations reported Available. The grouping is provisional, not an independently verified station inventory.

### Occupancy analysis

The HDB-linked planning-area occupancy metric describes the share of qualifying **individual charging-point observations** classified as Occupied among Available-or-Occupied observations. The Occupied category can include charging, reserved and blocked. The figures do not directly measure active charging sessions, driver demand or unmet demand.

## Verified results used in the presentation

The following figures come from the team's reported BigQuery queries and should be interpreted for their corresponding extracts and model versions.

| Measure | Result |
| --- | ---: |
| HDB carparks analysed | 2,273 across 32 URA planning areas |
| HDB carparks with a strong candidate match | 628 |
| Individual charging points with a strong HDB match | 2,895 |
| Provisional charging locations islandwide | 2,799 |
| Provisional charging locations with a strong HDB association | 655 |
| HDB-matched location availability | 91.90% of complete location observations |
| Unmatched location availability | 90.38% |
| Islandwide location availability | 90.73% |
| AC share of all individual charging points | 10,086 / 11,698 = 86.22% |
| AC share of strongly HDB-matched charging points | 2,839 / 2,895 = 98.07% |

Selected planning-area occupancy results for the strongly matched subset:

| URA planning area | Occupancy | Matched HDB carparks | Matched charging points |
| --- | ---: | ---: | ---: |
| Punggol | 47.53% | 8 of 102 | 24 |
| Pasir Ris | 37.04% | 25 of 65 | 86 |
| Tengah | 22.10% | 1 of 20 | 7 |

The occupancy ranking covered **30 qualifying planning areas** with strong matches, compared with **32 planning areas** represented in the HDB carpark analysis. The approximately **25% estimated overall HDB-matched occupancy** was derived from a charging-point-count-weighted average of planning-area percentages; it is not an exact observation-weighted aggregate.

## Key interpretation and limitations

- The historical status analysis covered approximately **one week** of 15-minute observations. It does not establish long-term demand or persistent shortages.
- Location-level availability over 90% means at least one connector was available at most complete observed intervals; it does **not** mean every connector was available, nor that all drivers had convenient access.
- Strong HDB matches are algorithmic candidate associations, not verified installations. Low strong-match coverage must **not** be interpreted as low actual HDB charger coverage.
- Selected area occupancy rates apply only to the matched charging-point subset and may not represent all HDB charging infrastructure in those areas.
- AC/DC classification is based on the `current` field in the dbt charger dimension. AC is commonly suitable for longer parking durations; an AC-heavy network alone does not prove inadequate charging service.
- HDB building footprints and URA zoning provide development context but do not quantify future households, move-in dates or EV charging demand.
- The HTML heatmaps are supporting exploratory visualisations, not part of the final presented findings; they may reflect an earlier extract and should not be assumed to match the latest BigQuery percentages.

## Reproducing the analysis

1. Use the team's existing Google Cloud / BigQuery access and identify the corresponding EV charging datasets and historical observation period.
2. Place the dbt project files in the appropriate project directory; review `dbt_project.yml`, referenced models and any required macros/packages before running dbt. Local dbt credentials and profiles are **not** included.
3. Download the government source datasets as required by the notebooks, check their schemas, and set the expected local paths.
4. Run the relevant dbt models and saved SQL queries, then run notebooks as needed. Reproduction may require Python geospatial and Plotly dependencies already used by the notebooks.
5. Check that the source versions and observation window match those used for the reported results before comparing numerical outputs.

## Security

Do not commit API keys, `.env` files, `profiles.yml` with credentials, Google Cloud service-account JSON keys, or other secrets to GitHub. BigQuery project and dataset identifiers may appear in SQL; verify repository visibility and team sharing policy before publishing.
