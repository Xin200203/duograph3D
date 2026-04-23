# DuoGraph3D

Research-oriented implementation skeleton for the v1 DuoGraph3D plan.

## Repository
- GitHub (SSH): `git@github.com:Xin200203/duograph3D.git`

## Current scope
- shared event schema and branch ids
- object graph memory as the only long-term decision state
- layer-1 current evidence repair
- layer-2 current-to-memory association and lifecycle updates
- temporal variants: none / naive frame-wise / deva-style
- fair-rival skeletons: single-layer, dense-authority-export, full fair counterfactual
- unittest coverage for state authority, temporal behavior, and rival branch execution

## Run tests
```bash
cd /Users/xin/Research/Code/research/DuoGraph3D
python3 -m unittest discover -s tests -v
```

## Example
```bash
cd /Users/xin/Research/Code/research/DuoGraph3D
PYTHONPATH=src python3 examples/minimal_sequence.py
```
