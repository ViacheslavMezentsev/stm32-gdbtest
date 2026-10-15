"""Export sealed DDTT evidence as portable HTML/LCOV/Cobertura and CI annotations."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import subprocess
try:
    from . import ddtt_coverage as core
    from .ddtt_provenance import at_revision, digest, path_name, revision
    from .ddtt_view import formats, github, render
except ImportError:
    import ddtt_coverage as core
    from ddtt_provenance import at_revision, digest, path_name, revision
    from ddtt_view import formats, github, render

FILES = {'index.html', 'public-data.json', 'lcov.info', 'coverage.xml', '.nojekyll'}


def annotation(point):
    def esc(text, prop=False):
        text = str(text).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        return text.replace(':', '%3A').replace(',', '%2C') if prop else text
    level = {'CONFIRMED':'notice', 'FAILED':'error', 'UNKNOWN':'warning'}[point['state']]
    return (f'::{level} file={esc(point["source"], True)},line={point["line"]},title=DDTT::'
            + esc(point['state'] + ': ' + point['check']))


def prepare(root, mapping, runs, campaign, repository):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Expected GitHub owner/repository')
    if campaign.get('status') != 'SEALED':
        raise ValueError('Sealed campaign required')
    if campaign.get('mapping_sha256') != digest(json.dumps(mapping,sort_keys=True).encode()):
        raise ValueError('Campaign map changed')
    sha = revision(root, campaign['revision'])
    for name, checksum in campaign['inputs'].items():
        if digest(at_revision(root, sha, name)) != checksum:
            raise ValueError('Campaign input changed: ' + name)
    paths = []
    for name, item in campaign['results'].items():
        path = (runs / path_name(name)).resolve()
        if not path.is_relative_to(runs) or digest(path.read_bytes()) != item['sha256']:
            raise ValueError('Result changed')
        paths.append(path)
    if set(paths) != {p.resolve() for p in runs.glob('*/result.json')}:
        raise ValueError('Result inventory changed')
    rows = core.project(root, mapping, paths)
    points, sources = [], {}
    for row in rows:
        source = row['source']
        if campaign['inputs'].get(source) != row['source_sha256']:
            raise ValueError('Source not captured before run')
        sources[source] = at_revision(root, sha, source).decode('utf-8-sig').splitlines()
        point = {k:row[k] for k in ('source','line','scenario','check','state')}
        point.update(source_url=github(repository,sha,source,row['line']),scenario_url=None,
                     started_utc=None, checks_passed=sum(row.get('verdicts',[])),
                     checks_total=len(row.get('verdicts',[])))
        if row['evidence']:
            path = Path(row['evidence']['path'])
            meta = campaign['results'][path.relative_to(runs).as_posix()]
            scenario = meta['scenario']
            if meta['case'] != row['scenario'] or scenario not in campaign['inputs']:
                raise ValueError('Unknown scenario attribution')
            # Every source link points to a captured scenario. Entry line is explicit, not guessed.
            line = row.get('scenario_line',1)
            code = at_revision(root,sha,scenario).decode('utf-8-sig').splitlines()
            if type(line) is not int or not 1 <= line <= len(code):
                raise ValueError('Invalid scenario line')
            point['scenario_url'] = github(repository,sha,scenario,line)
            point['started_utc'] = core.load(path)['started_utc']
        points.append(point)
    return dict(schema=1, interpretation='DDTT selected assertions; not execution coverage',
                environment=mapping.get('environment','hardware'), repository=repository,revision=sha,
                elf_sha256=mapping['elf_sha256'],campaign_attempts=len(paths),points=points,
                summary=dict(Counter(p['state'] for p in points))), sources


def export(root, mapping, runs, campaign, repository, out):
    root, runs, out = Path(root).resolve(), Path(runs).resolve(), Path(out).resolve()
    if (not out.is_relative_to(root/'build') or out == root/'build'
            or out.is_relative_to(runs) or runs.is_relative_to(out)):
        raise ValueError('Use a separate project build output')
    out.mkdir(parents=True,exist_ok=True)
    if any(p.name not in FILES or not p.is_file() or p.is_symlink() for p in out.iterdir()):
        raise ValueError('Unrelated output files')
    for name in FILES:
        (out/name).write_text('',encoding='utf-8')
    (out/'index.html').write_text('<p>DDTT export ERROR / incomplete</p>',encoding='utf-8')
    # Load inside invalidation boundary.
    if isinstance(mapping,(str,Path)):
        mapping=core.load(mapping)
    if isinstance(campaign,(str,Path)):
        campaign=core.load(campaign)
    data,sources=prepare(root,mapping,runs,campaign,repository)
    lcov,xml=formats(data)
    for name,text in [('index.html',render(data,sources)),('public-data.json',json.dumps(data,ensure_ascii=False,indent=2)),
                      ('lcov.info',lcov),('coverage.xml',xml)]:
        (out/name).write_text(text,encoding='utf-8')
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('project','map','runs','campaign','repository','out'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--annotations',action='store_true')
    a=p.parse_args()
    try:
        data=export(a.project,a.map,a.runs,a.campaign,a.repository,a.out)
        if a.annotations:
            for point in data['points']:
                print(annotation(point))
        print(json.dumps(data['summary']))
        return 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.CalledProcessError) as error:
        print('DDTT export error: '+str(error),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
