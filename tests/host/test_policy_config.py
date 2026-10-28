"""Schema 3 configuration is portable and validated report policies are executable."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stm32_gdbtest.configuration import load_session, capture, thaw, ConfigError
from stm32_gdbtest.config_transport import dumps, loads, fingerprint
from stm32_gdbtest.package import pack, open_package
from stm32_gdbtest.runner import run
from test_session_config import TARGET
from test_prepare import SECTIONS


class PolicyConfigTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        (self.root/'target.toml').write_text(TARGET,encoding='utf-8')
        (self.root/'session.toml').write_text('[config]\ntarget="target.toml"\napi="api.toml"',encoding='utf-8')
        self.session=dict(root=str(self.root),out=str(self.root/'runs'),profile=str(self.root/'target.toml'),
                          session_config=str(self.root/'session.toml'),elf=str(self.root/'firmware.elf'),gdb='arm-none-eabi-gdb')
        self.test=dict(id='HW_ONE',timeout_s=10,contracts=[])

    def load(self,text='schema=3'):
        (self.root/'api.toml').write_text(text,encoding='utf-8')
        return load_session(self.root/'session.toml',environ={})

    def test_defaults_and_independent_policies(self):
        api=self.load().config['api']
        self.assertEqual(api['records']['max_records'],4096)
        self.assertEqual(api['report']['max_rows_per_collection'],65536)
        self.assertEqual(api['report']['on_limit'],'error')
        self.assertEqual(api['journal']['on_limit'],'error')
        for section in ('journal','report'):
            cfg=self.load(f'schema=3\n[{section}]\non_limit="truncate"')
            self.assertEqual(cfg.config['api'][section]['on_limit'],'truncate')
            other='report' if section=='journal' else 'journal'
            self.assertEqual(cfg.config['api'][other]['on_limit'],'error')
        with self.assertRaises(TypeError): api['report']['on_limit']='truncate'

    def test_numeric_boundaries(self):
        maxima={'max_records':65536,'max_nodes':2097152,'max_text_bytes':16777216,'max_depth':32,'max_integer_bits':1024}
        for section,key,maximum in [('records',k,v) for k,v in maxima.items()]+[('report','max_rows_per_collection',65536)]:
            for value in ('0','-1','true','1.5','"unlimited"',str(maximum+1)):
                with self.subTest(key=key,value=value),self.assertRaises(ConfigError):
                    self.load(f'schema=3\n[{section}]\n{key}={value}')
            for value in (1,maximum):
                self.assertEqual(self.load(f'schema=3\n[{section}]\n{key}={value}').config['api'][section][key],value)

    def test_unknown_keys_types_and_old_schemas(self):
        for text in ('[records]\nmax_record=10','[journal]\noverflow="truncate"',
                     '[report]\nmax_rows=10','[journal]\non_limit=true','[report]\non_limit="ignore"',
                     'report=1','journal=false','records=[]'):
            with self.subTest(text=text),self.assertRaises(ConfigError):self.load('schema=3\n'+text)
        for schema in (1,2):
            self.assertEqual(self.load(f'schema={schema}').config['api']['schema'],schema)
            for section in ('journal','report'):
                with self.assertRaises(ConfigError):self.load(f'schema={schema}\n[{section}]\non_limit="error"')
        # Application data namespaces remain available, not interpreted as quotas.
        self.assertEqual(self.load('schema=3\n[user]\ncount=2').config['api']['user']['count'],2)

    def test_capsule_after_sources_removed_and_hash_binding(self):
        original=self.load('schema=3\n[report]\nmax_rows_per_collection=7\nconsole="summary"\n[journal]\non_limit="truncate"')
        capsule=dumps(original)
        (self.root/'api.toml').unlink()
        restored=loads(capsule)
        self.assertEqual(thaw(original.config),thaw(restored.config))
        self.assertEqual(len({fingerprint(i) for i in (1,2,3)}),3)
        data=json.loads(capsule);data['defaults']=fingerprint(2)
        with self.assertRaises(ConfigError):loads(json.dumps(data))
        data=json.loads(capsule)
        raw=b'schema=3\n[report]\nmax_rows_per_collection=65537'
        data['files']['api']=dict(base64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ConfigError):loads(json.dumps(data))

    def test_real_package_roundtrip(self):
        cfg=self.load('schema=3\n[journal]\non_limit="truncate"\n[report]\nmax_rows_per_collection=17')
        board=self.root/'tests/board';board.mkdir(parents=True)
        (board/'test_one.py').write_text('from stm32_gdbtest import case\n@case("HW_ONE")\ndef one(t): pass\n',encoding='utf-8')
        Path(self.session['elf']).write_bytes(b'ELF fixture')
        session=dict(self.session,tests=str(board))
        bundle=self.root/'bundle.zip'
        pack(session,bundle)
        (self.root/'api.toml').unlink()
        with patch('stm32_gdbtest.package.find_gdb',return_value='gdb'):
            opened=open_package(bundle,self.root/'extracted','gdb')
        self.assertEqual(thaw(capture(opened).config),thaw(cfg.config))

    def test_all_validated_report_policies_are_executable(self):
        from stm32_gdbtest.configuration import require_execution_supported
        for policy in ('error','truncate'):
            for quota in (1,17,65536):
                cfg=self.load(f'schema=3\n[report]\non_limit="{policy}"\nmax_rows_per_collection={quota}')
                self.assertIsNone(require_execution_supported(cfg))

    def test_prepare_transports_schema_three_without_server(self):
        cfg=self.load('schema=3\n[report]\non_limit="truncate"\nmax_rows_per_collection=9')
        Path(self.session['elf']).write_bytes(b'ELF fixture')
        def run_tool(args,**kwargs):
            if '--gap-fill=0xFF' in args:Path(args[-1]).write_bytes(bytes(range(32)))
            return type('Process',(),dict(returncode=0))()
        with patch('stm32_gdbtest.runner.runtime_manifest',return_value={}), \
             patch('stm32_gdbtest.runner.subprocess.check_output',return_value=SECTIONS.encode()), \
             patch('stm32_gdbtest.runner.subprocess.run',side_effect=run_tool), \
             patch('stm32_gdbtest.runner.subprocess.Popen') as server, \
             patch('stm32_gdbtest.runner.probe_lock') as lock:
            self.assertEqual(run(self.session,self.test,prepare_only=True),0)
            server.assert_not_called();lock.assert_not_called()
        capsule=next((self.root/'runs').glob('*/config.json')).read_text(encoding='utf-8')
        self.assertEqual(thaw(loads(capsule).config),thaw(cfg.config))
