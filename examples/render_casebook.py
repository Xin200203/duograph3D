from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d.casebook import build_casebook, load_json, render_casebook_markdown
from duograph3d.io_utils import write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a G3 casebook from a mega summary and suite directories")
    parser.add_argument("mega_summary")
    parser.add_argument("suite_dirs", nargs="+")
    parser.add_argument("--output-dir", default="outputs_casebook")
    args = parser.parse_args()

    mega_summary = load_json(args.mega_summary)
    casebook = build_casebook(mega_summary, args.suite_dirs)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "casebook.json"
    md_path = output_dir / "casebook.md"
    write_json(casebook, json_path)
    md_path.write_text(render_casebook_markdown(casebook) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
