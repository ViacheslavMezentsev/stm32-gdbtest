"""Run the simulation and compare complete snapshots against a reviewed oracle."""
import argparse
import json
from pathlib import Path

if __package__:
    from .engine import Engine, load_tree, read_json
else:
    from engine import Engine, load_tree, read_json


def first_difference(expected, actual, path='$'):
    if type(expected) is not type(actual):
        return f'{path}: expected {expected!r}, got {actual!r}'
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return f'{path}: keys differ'
        for key in expected:
            diff = first_difference(expected[key], actual[key], f'{path}.{key}')
            if diff:
                return diff
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return f'{path}: expected length {len(expected)}, got {len(actual)}'
        for index, (left, right) in enumerate(zip(expected, actual)):
            diff = first_difference(left, right, f'{path}[{index}]')
            if diff:
                return diff
    elif expected != actual:
        return f'{path}: expected {expected!r}, got {actual!r}'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=Path(__file__).parent / 'fixtures/bringup')
    parser.add_argument('--out', type=Path, default=Path('build/adaptive-tree'))
    args = parser.parse_args()
    frames = Engine(load_tree(args.fixture / 'tree'), read_json(args.fixture / 'facts.json')).run()
    diff = first_difference(read_json(args.fixture / 'expected.json'), frames)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'snapshots.json').write_text(json.dumps(frames, indent=2) + '\n', encoding='utf-8')
    (args.out / 'verification.json').write_text(json.dumps({
        'simulation_only': True, 'snapshots': len(frames), 'executed': len(frames[-1]['results']),
        'oracle_match': diff is None, 'difference': diff,
        'executed_order': list(frames[-1]['results']),
    }, indent=2) + '\n', encoding='utf-8')
    print(diff or f'PASS: {len(frames)} complete snapshots match the independent oracle')
    return 1 if diff else 0


if __name__ == '__main__':
    raise SystemExit(main())
