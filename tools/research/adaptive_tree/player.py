"""Render an offline HTML player from recorded snapshots, never re-run scenarios."""
import argparse
import json
from pathlib import Path


def render(snapshots):
    template = Path(__file__).with_name('player.html').read_text(encoding='utf-8')
    # Do not let fixture text terminate the script element.
    data = json.dumps(snapshots, ensure_ascii=False).replace('<', '\\u003c')
    return template.replace('__SNAPSHOTS__', data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshots', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    frames = json.loads(args.snapshots.read_text(encoding='utf-8'))
    if not frames:
        parser.error('At least one snapshot is required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(frames), encoding='utf-8')
    print('Rendered', args.output)


if __name__ == '__main__':
    main()
