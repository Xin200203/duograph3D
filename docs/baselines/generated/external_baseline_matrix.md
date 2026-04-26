# External Baseline Matrix

| Baseline | Dataset | Scope | Comparison axis | Primary metric | Value | Faithfulness |
| --- | --- | --- | --- | --- | ---: | --- |
| DEVA official offline | replica | office0 | temporal_external_lane | `avg_segments_per_frame` | 1.0000 | official_repo_executed |
| DEVA official offline | replica | office2 | temporal_external_lane | `avg_segments_per_frame` | 0.6670 | official_repo_executed |
| DEVA official offline | replica | office3 | temporal_external_lane | `avg_segments_per_frame` | 0.6670 | official_repo_executed |
| EmbodiedSAM official ScanNet-MV | scannet | fullval | online_3d_external_lane | `all_ap` | 0.4135 | official_family_fork_executed |
