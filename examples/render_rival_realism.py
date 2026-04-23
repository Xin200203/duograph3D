from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.rival_realism import render_rival_realism_markdown, summarize_rival_realism


def main() -> None:
    parser = argparse.ArgumentParser(description='Render rival realism summary from suite directories')
    parser.add_argument('suite_dirs', nargs='+')
    parser.add_argument('--output-dir', default='outputs_rival_realism')
    args = parser.parse_args()

    summary = summarize_rival_realism(args.suite_dirs)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'rival_realism.json'
    md_path = output_dir / 'rival_realism.md'
    write_json(summary, json_path)
    md_path.write_text(render_rival_realism_markdown(summary) + '\n')
    print(json_path)
    print(md_path)


if __name__ == '__main__':
    main()
