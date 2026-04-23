from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.g4_docs import (
    render_camera_ready_risk_list,
    render_extension_backlog,
    render_intro_claim_stack,
    render_paper_outline,
    render_submission_readiness,
)


def main() -> None:
    parser = argparse.ArgumentParser(description='Render G4 docs from mega and readiness summaries')
    parser.add_argument('mega_summary')
    parser.add_argument('readiness_json')
    parser.add_argument('--output-dir', default='outputs_g4')
    args = parser.parse_args()

    mega = json.loads(Path(args.mega_summary).read_text())
    readiness = json.loads(Path(args.readiness_json).read_text())
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    docs = {
        'paper-outline.md': render_paper_outline(mega, readiness),
        'intro-claim-stack.md': render_intro_claim_stack(mega, readiness),
        'camera-ready-risk-list.md': render_camera_ready_risk_list(readiness),
        'post-v1-extension-backlog.md': render_extension_backlog(mega),
        'submission-readiness-summary.md': render_submission_readiness(readiness, mega),
    }
    for name, content in docs.items():
        (output_dir / name).write_text(content + '\n')
        print(output_dir / name)


if __name__ == '__main__':
    main()
