"""Host-side acceptance of expected R10 errors, never rewriting their status."""
import json


def validate(case_id, report, directory):
    if report.get('status') != 'ERROR':
        raise RuntimeError('Expected retained ERROR')
    error = report.get('error', '')
    if case_id == 'HW_R10_FAULT':
        evidence = report.get('research', {}).get('fault', {})
        if (report.get('teardown') != 'reset_run' or not report.get('image_verified')
                or 'sum_bytes' not in error or not evidence.get('guard_hit')
                or evidence.get('exception') != 3 or evidence.get('dummy_count') != 1
                or evidence.get('bfar') != 0x20020000
                or evidence.get('cfsr', 0) & 0x8200 != 0x8200
                or evidence.get('hfsr', 0) & 0x40000000 == 0
                or not report.get('checks') or not all(c['passed'] for c in report['checks'])):
            raise RuntimeError('Fault cause or reset evidence missing')
    elif case_id == 'HW_R10_TIMEOUT':
        marker = directory / 'entered-call.json'
        if ('TimeoutExpired' not in error or report.get('teardown') != 'reset_run (host recovery)'
                or not marker.is_file()):
            raise RuntimeError('Timeout entry or host recovery missing')
        evidence = json.loads(marker.read_text(encoding='utf-8'))
        if (evidence.get('function') != 'Default_Handler' or evidence.get('dummy_count') != 1
                or evidence.get('instruction_hex') != 'fee7' or evidence.get('exception') != 0):
            raise RuntimeError('Timeout did not enter the expected thread-mode dummy loop')
    else:
        raise ValueError('Not an R10 negative scenario')
