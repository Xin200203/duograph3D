from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.metadata_grounding import render_metadata_grounding_markdown, summarize_metadata_grounding


def main() -> None:
    parser = argparse.ArgumentParser(description='Render metadata grounding summary from suite directories')
    parser.add_argument('suite_dirs', nargs='+')
    parser.add_argument('--output-dir', default='outputs_metadata_grounding')
    args = parser.parse_args()

    summary = summarize_metadata_grounding(args.suite_dirs)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'metadata_grounding.json'
    md_path = output_dir / 'metadata_grounding.md'
    write_json(summary, json_path)
    md_path.write_text(render_metadata_grounding_markdown(summary) + '\n')
    print(json_path)
    print(md_path)


if __name__ == '__main__':
    main()
