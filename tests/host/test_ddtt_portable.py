"""Portable evidence provenance and failure isolation (TC-173/174)."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools import ddtt_coverage as core, ddtt_provenance as provenance, ddtt_report as report, renode_probe
from tools.ddtt_guard import code_lines

class PortableTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        (self.root/'app.cpp').write_text('void step() {\n  ++count;\n}\n',encoding='utf-8')
        (self.root/'test.py').write_text('# Scenario\n',encoding='utf-8')
        def git(*args):
            return subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True).stdout
        git('init','-q');git('add','app.cpp','test.py')
        git('-c','user.name=Test','-c','user.email=test@example.invalid','-c','commit.gpgsign=false','commit','-qm','fixture')
        self.sha=git('rev-parse','HEAD').decode().strip()
        self.mapping=dict(schema=1,environment='emulator',elf_sha256='a'*64,points=[dict(source='app.cpp',source_sha256=core.digest(self.root/'app.cpp'),anchor='++count;',scenario='ONE',check='advanced')])
        self.runs=self.root/'build/runs';self.runs.mkdir(parents=True)
        self.campaign=self.root/'build/campaign.json'
        provenance.begin(self.root,self.sha,self.runs,self.campaign,['app.cpp','test.py'],self.mapping)
        self.result=dict(mode='emulator',purpose='automated',id='ONE',run_id='one',status='PASS',started_utc=datetime.now(timezone.utc).isoformat(),elf_sha256='a'*64,build_manifest={'inputs':[dict(file='app.cpp',sha256=self.mapping['points'][0]['source_sha256'])]},checks=[dict(name='advanced',passed=True)])
        self.path=self.runs/'one/result.json';self.path.parent.mkdir()
        self.save()
        self.path.with_name('run.json').write_text(json.dumps({'test':{'id':'ONE','path':str(self.root/'test.py')}}),encoding='utf-8')
        self.out=self.root/'build/public'

    def save(self):
        self.path.write_text(json.dumps(self.result),encoding='utf-8')

    def export(self):
        return report.export(self.root,self.mapping,self.runs,self.campaign,'owner/project',self.out)

    def test_portable_allowlist_and_links(self):
        provenance.seal(self.root,self.runs,self.campaign)
        data=self.export()
        self.assertEqual(data['summary'],{'CONFIRMED':1})
        self.assertEqual({p.name for p in self.out.iterdir()},report.FILES)
        self.assertIn(self.sha+'/test.py#L1',data['points'][0]['scenario_url'])
        for path in self.out.iterdir():
            self.assertNotIn(str(self.root),path.read_text(encoding='utf-8'))
        self.assertIn('DA:2,1',(self.out/'lcov.info').read_text())
        self.assertIn('number="2" hits="1"',(self.out/'coverage.xml').read_text())

    def test_tampered_result_clears_previous_green(self):
        provenance.seal(self.root,self.runs,self.campaign);self.export()
        self.result['checks'][0]['passed']=False;self.save()
        with self.assertRaises(ValueError):self.export()
        self.assertEqual((self.out/'lcov.info').read_text(),'')
        self.assertIn('ERROR',(self.out/'index.html').read_text())

    def test_changed_source_prevents_seal(self):
        (self.root/'app.cpp').write_text('changed')
        with self.assertRaises(ValueError):provenance.seal(self.root,self.runs,self.campaign)

    def test_changed_map_or_inventory_rejected(self):
        provenance.seal(self.root,self.runs,self.campaign)
        self.mapping['points'][0]['check']='different'
        with self.assertRaises(ValueError):self.export()
        self.mapping['points'][0]['check']='advanced'
        other=self.runs/'other';other.mkdir();(other/'result.json').write_bytes(self.path.read_bytes())
        with self.assertRaises(ValueError):self.export()

    def test_manual_and_wrong_environment_not_evidence(self):
        for change in ({'purpose':'manual'},{'mode':'hardware'},{'mode':'prepare'}):
            original=self.result.copy();self.result.update(change);self.save()
            self.assertEqual(core.project(self.root,self.mapping,[self.path])[0]['state'],'UNKNOWN')
            self.result=original

    def test_unknown_shared_line_is_not_green(self):
        rows=[dict(absolute_source='app.cpp',line=2,state=s) for s in ('CONFIRMED','UNKNOWN')]
        self.assertNotIn('DA:',core.render(rows))

    def test_comments_rejected_but_literals_preserved(self):
        self.assertEqual(code_lines('// comment\n/* block\n * text */\nconst char *s="//";\n'),[False,False,False,True])
        point=dict(self.mapping['points'][0],anchor='// comment')
        (self.root/'app.cpp').write_text('// comment\n')
        with self.assertRaises(ValueError):core.project(self.root,dict(self.mapping,points=[point]),[])

    def test_annotation_escapes_commands(self):
        text=report.annotation(dict(state='FAILED',source='a,b.cpp',line=2,check='x\n::error::fake'))
        self.assertIn('a%2Cb.cpp',text);self.assertNotIn('\n',text)

class ProbeTests(unittest.TestCase):
    def test_gdb_timeout_cleans_up_and_retains_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('elf','model','scenario.py','app.cpp'):(root/name).write_text('fixture')
            mapping=dict(schema=1,environment='emulator',elf_sha256=core.digest(root/'elf'),points=[dict(source='app.cpp',source_sha256=core.digest(root/'app.cpp'),anchor='fixture',scenario='ONE',check='one')])
            with patch.object(renode_probe.subprocess,'Popen') as popen, patch.object(renode_probe,'terminate') as terminate, patch.object(renode_probe.subprocess,'run',side_effect=subprocess.TimeoutExpired('gdb',.1)):
                def ready(*args,**kwargs):
                    kwargs['stdout'].write(b'GDB server with all CPUs started');kwargs['stdout'].flush()
                    return popen.return_value
                popen.side_effect=ready
                code=renode_probe.run(root,root/'elf',root/'model',root/'scenario.py',mapping,root/'runs','gdb','renode','ONE',.1)
                self.assertEqual(code,1);terminate.assert_called_once()
            result=json.loads(next((root/'runs').glob('*/result.json')).read_text())
            self.assertEqual(result['status'],'ERROR');self.assertIn('timed out',result['error'])
            self.assertEqual(result['cleanup'],'VERIFIED')

    def test_readiness_timeout_preserves_error_and_cleans_owned_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('elf','model','scenario.py','app.cpp'):(root/name).write_text('fixture')
            mapping=dict(schema=1,environment='emulator',elf_sha256=core.digest(root/'elf'),points=[dict(source='app.cpp',source_sha256=core.digest(root/'app.cpp'),anchor='fixture',scenario='ONE',check='one')])
            with patch.object(renode_probe.subprocess,'Popen') as popen, patch.object(renode_probe,'terminate') as terminate:
                popen.return_value.poll.return_value=1
                code=renode_probe.run(root,root/'elf',root/'model',root/'scenario.py',mapping,root/'runs','gdb','renode','ONE',.1)
                self.assertEqual(code,1);terminate.assert_called_once_with(popen.return_value)
            result=json.loads(next((root/'runs').glob('*/result.json')).read_text())
            self.assertEqual(result['status'],'ERROR');self.assertIn('readiness',result['error'])
            self.assertEqual(result['cleanup'],'VERIFIED')

if __name__=='__main__':unittest.main()
