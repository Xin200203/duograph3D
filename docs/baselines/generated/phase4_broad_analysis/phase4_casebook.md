# Phase 4 Representative Casebook

## best_identity_stability
- Scene: `replica/office0`
- Metric: `identity_fragmentation_count` = `0.0`
- Observation mode: `real_deva_output_json`
- Event excerpt:
  - `current_hypothesis_emit` step=1 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278', 'ambiguity_flags': []}
  - `birth_commit` step=1 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278'}
  - `current_hypothesis_emit` step=2 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278', 'ambiguity_flags': []}
  - `association_commit` step=2 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278', 'score': 2.8100000000000005}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278', 'ambiguity_flags': []}
  - `association_commit` step=3 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278', 'score': 2.6372}
  - `current_hypothesis_emit` step=4 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278', 'ambiguity_flags': []}
  - `association_commit` step=4 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office0:deva-track:14802278', 'score': 2.8100000000000005}

## best_track_consistency
- Scene: `replica/office3`
- Metric: `track_consistency_rate` = `1.0`
- Observation mode: `real_deva_output_json`
- Event excerpt:
  - `current_hypothesis_emit` step=1 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644', 'ambiguity_flags': []}
  - `birth_commit` step=1 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644'}
  - `current_hypothesis_emit` step=2 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644', 'ambiguity_flags': []}
  - `association_commit` step=2 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644', 'score': 2.8100000000000005}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644', 'ambiguity_flags': []}
  - `association_commit` step=3 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644', 'score': 2.5146}
  - `current_hypothesis_emit` step=4 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644', 'ambiguity_flags': []}
  - `association_commit` step=4 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'office3:deva-track:6423644', 'score': 2.8100000000000005}

## worst_fragmentation
- Scene: `scannet/scene0222_00`
- Metric: `identity_fragmentation_count` = `115.0`
- Observation mode: `real_scannet_online_monitor_json`
- Event excerpt:
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'scene0222_00:track:32', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-2', 'track_hint': 'scene0222_00:track:34', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-3', 'track_hint': 'scene0222_00:track:35', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-4', 'track_hint': 'scene0222_00:track:36', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-5', 'track_hint': 'scene0222_00:track:38', 'ambiguity_flags': []}
  - `birth_commit` step=3 payload={'object_id': 'obj-1', 'hypothesis_id': 'hyp-1', 'track_hint': 'scene0222_00:track:32'}
  - `birth_commit` step=3 payload={'object_id': 'obj-2', 'hypothesis_id': 'hyp-2', 'track_hint': 'scene0222_00:track:34'}
  - `birth_commit` step=3 payload={'object_id': 'obj-3', 'hypothesis_id': 'hyp-3', 'track_hint': 'scene0222_00:track:35'}

## weakest_geometry_support
- Scene: `scannet/scene0050_00`
- Metric: `geometry_support_mean` = `0.2`
- Observation mode: `real_scannet_online_monitor_json`
- Event excerpt:
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-1', 'track_hint': 'scene0050_00:track:6', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-2', 'track_hint': 'scene0050_00:track:15', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-3', 'track_hint': 'scene0050_00:track:17', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-4', 'track_hint': 'scene0050_00:track:19', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-5', 'track_hint': 'scene0050_00:track:21', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-6', 'track_hint': 'scene0050_00:track:23', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-7', 'track_hint': 'scene0050_00:track:28', 'ambiguity_flags': []}
  - `current_hypothesis_emit` step=3 payload={'hypothesis_id': 'hyp-8', 'track_hint': 'scene0050_00:track:29', 'ambiguity_flags': []}

