# 184 remote verification (fullval family, 2026-04-23)

- Generated: 2026-04-23T18:35:00
- Full-match across lanes (1e-4 tolerance): True
- Note: Numeric match uses absolute tolerance 1e-4; time values are rounded to 4dp in local files and should match within tolerance.

| lane | AP | AP50 | AP25 | match_rate | birth_rate | rescued | scenes | frames | mem_kept | mem_full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fullval_strict_baseline | 0.4135 | 0.6300 | 0.7886 | 0.8202 | 0.1791 | 0.0 | 312 | 13430 | 56.9311 | 62.9335 |
| fullval_rescue_only | 0.4133 | 0.6286 | 0.7897 | 0.7999 | 0.1636 | 2.158376693725586 | 312 | 13430 | 53.3058 | 57.4743 |
| fullval_dedup_only | 0.4133 | 0.6244 | 0.7797 | 0.8104 | 0.1888 | 0.0 | 312 | 13430 | 53.3261 | 57.1333 |
| fullval_rescue_plus_dedup | 0.4051 | 0.6139 | 0.7708 | 0.7861 | 0.1723 | 2.394638776779175 | 312 | 13430 | 49.3498 | 51.7797 |
| fullval_dedup_strict | 0.3985 | 0.6024 | 0.7624 | 0.3959 | 0.0980 | NA | 312 | 13430 | 51.6560 | 53.7141 |

## mismatch detail

