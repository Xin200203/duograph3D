# 184 remote recheck5 verification (fullval family)
- Generated: 2026-04-23T18:59:12+0800
- Full-match across lanes (1e-4 tolerance): True
- Reused ESAM fullval namespace; compared latest timestamp metric and online-monitor summaries.

| lane | AP | AP50 | AP25 | match_rate | birth_rate | rescued | scenes | frames | topk_drop | mem_kept | mem_full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fullval_baseline_dino | 0.4135 | 0.6300 | 0.7886 | 0.8202 | 0.1791 | 0.0000 | 312 | 13430 | 6.0024 | 56.9311 | 62.9335 |
| fullval_neg05_v2_rescue_only_strict_retry2 | 0.4133 | 0.6286 | 0.7897 | 0.7999 | 0.1636 | 2.1584 | 312 | 13430 | 4.1685 | 53.3058 | 57.4743 |
| fullval_neg05_v2_dedup_only_strict | 0.4133 | 0.6244 | 0.7797 | 0.8104 | 0.1888 | 0.0000 | 312 | 13430 | 3.8071 | 53.3261 | 57.1333 |
| fullval_neg05_v2_rescue_all_dedup_strict | 0.4051 | 0.6139 | 0.7708 | 0.7861 | 0.1723 | 2.3946 | 312 | 13430 | 2.4299 | 49.3498 | 51.7797 |
| 2601_dedup_strict_fullval | 0.3985 | 0.6024 | 0.7624 | 0.3959 | 0.0980 | NA | 312 | 13430 | 2.0582 | 51.6560 | 53.7141 |

## mismatch detail
