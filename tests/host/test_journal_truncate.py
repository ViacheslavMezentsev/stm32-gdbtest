"""A3.2 journal prefixes, independent verdicts and atomic MMIO descriptors."""
import copy
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from stm32_gdbtest import evidence, report_data
from stm32_gdbtest.records import Journal, RecordError
from stm32_gdbtest.compact_records import CompactJournal
from stm32_gdbtest.mmio import MMIO, Register
from stm32_gdbtest.scenario import reject_failed_checks
from stm32_gdbtest.result_capture import save, read, finalize
from stm32_gdbtest.errors import CheckFailed

class TruncateTests(unittest.TestCase):
    def setup_journal(self, kind=Journal, **limits):
        report=dict(id='CASE', run_id='RUN', status='PASS')
        report_data.configure(report, {})
        journal=kind(**limits);journal.on_limit='truncate'
        return report,journal

    def test_prefix_and_atomic_limits(self):
        for kind in (Journal,CompactJournal):
            for limits in (dict(max_records=1),dict(max_nodes=12),dict(max_text_bytes=30)):
                with self.subTest(kind=kind,limits=limits):
                    r,j=self.setup_journal(kind,**limits)
                    evidence.journal(r,j.record,'x',1)
                    prefix=copy.deepcopy(j._entries)
                    for i in range(10):evidence.journal(r,j.record,'large',['X'*100]*20)
                    self.assertEqual(j._entries,prefix)
                    m=r['evidence']['stores']['records']
                    self.assertEqual((m['state'],m['saved'],m['lost'],m['first_lost'],m['last_lost']),('truncated',1,10,2,11))
                    self.assertEqual(r['evidence']['diagnostics_total'],1)
                    evidence.validate(r)
                    reject_failed_checks(SimpleNamespace(report=r))

    def test_invalid_values_after_exhaustion_still_refused(self):
        for kind in (Journal,CompactJournal):
            r,j=self.setup_journal(kind,max_records=1,max_depth=2,max_integer_bits=8)
            evidence.journal(r,j.record,'x',1)
            evidence.journal(r,j.record,'x',2)
            cycle=[];cycle.append(cycle)
            for value in (object(),b'bytes',cycle,{1:2},float('nan'),256,[[[1]]],'\ud800'):
                with self.assertRaises(RecordError):evidence.journal(r,j.record,'x',value)
            self.assertEqual(r['evidence']['stores']['records']['attempted'],2)

    def test_failed_checks_cannot_be_hidden_by_truncation(self):
        r,j=self.setup_journal(max_records=1)
        for i in range(2):evidence.journal(r,j.record,'x',i)
        report_data.append(r,'checks',dict(name='failed',passed=False))
        with self.assertRaises(CheckFailed):reject_failed_checks(SimpleNamespace(report=r))

    def test_full_compact_capture_and_result_roundtrip(self):
        for kind in (Journal,CompactJournal):
            for compact in (False,True):
                r,j=self.setup_journal(kind,max_records=1)
                for i in range(3):evidence.journal(r,j.record,'x',i)
                encoded=report_data.payload(r,compact)
                self.assertEqual(encoded['report_schema'],3)
                decoded=report_data.decode(encoded)
                with tempfile.TemporaryDirectory() as tmp:
                    save(tmp,r,SimpleNamespace(_journal=j),'normal')
                    self.assertEqual(read(tmp,r)['records'],[dict(sequence=1,name='x',data=0)])
                    finalize(tmp,r,True)
                    self.assertEqual((r['status'],r['command_code'],r['capture']['status']),('PASS',2,'saved'))
                    forged=copy.deepcopy(r);forged['evidence']['stores']['records']['lost']+=1
                    with self.assertRaises(ValueError):read(tmp,forged)
                self.assertEqual(decoded['evidence'],r['evidence'])

    def test_mmio_continues_without_extra_transfers_or_orphan_descriptors(self):
        for kind in (Journal,CompactJournal):
            for quota in (1,2):
                r,j=self.setup_journal(kind,max_records=quota)
                transport=Mock();transport.read.return_value=b'\x01\0\0\0'
                catalog=SimpleNamespace(registers={'P.R':Register('P.R',0x40000000,32,'read-write')},sha256='a'*64)
                mmio=MMIO(catalog,transport,lambda n,d:evidence.journal(r,j.mmio_record,n,d))
                for i in range(5):self.assertEqual(mmio.read('P.R'),1)
                self.assertEqual(transport.read.call_count,5)
                transport.write.assert_not_called()
                self.assertEqual(len(j._entries),quota)
                with tempfile.TemporaryDirectory() as tmp:
                    save(tmp,r,SimpleNamespace(_journal=j),'normal');read(tmp,r)
                if kind is CompactJournal:self.assertEqual(len(j.definitions),1)

    def test_failed_descriptor_admission_is_atomic(self):
        r,j=self.setup_journal(CompactJournal,max_nodes=2)
        transport=Mock();transport.read.return_value=b'\x01\0\0\0'
        catalog=SimpleNamespace(registers={'P.R':Register('P.R',0x40000000,32,'read-write')},sha256='a'*64)
        mmio=MMIO(catalog,transport,lambda n,d:evidence.journal(r,j.mmio_record,n,d))
        self.assertEqual(mmio.read('P.R'),1)
        self.assertEqual(j.definitions,{})
        self.assertEqual(j._entries,[])
        self.assertEqual((j._nodes,j._text_bytes),(0,0))

    def test_io_errors_not_converted_to_truncation(self):
        class Broken(Journal):
            def record(self,name,data):raise OSError('disk')
        r,j=self.setup_journal(Broken)
        with self.assertRaises(OSError):evidence.journal(r,j.record,'x',1)
        self.assertEqual(r['evidence']['stores']['records']['state'],'unavailable')

    def test_strict_mode_unchanged(self):
        r,j=self.setup_journal(max_records=1);j.on_limit='error'
        evidence.journal(r,j.record,'x',1)
        with self.assertRaises(RecordError):evidence.journal(r,j.record,'x',2)
        self.assertTrue(evidence.storage_failed(r))

    def test_capture_failure_escalates_and_preserves_first_loss(self):
        r,j=self.setup_journal(max_records=1)
        for i in range(2):evidence.journal(r,j.record,'x',i)
        first=copy.deepcopy(r['evidence']['diagnostics'][0])
        with tempfile.TemporaryDirectory() as tmp, patch('stm32_gdbtest.result_capture.os.replace',side_effect=OSError('disk')):
            save(tmp,r,SimpleNamespace(_journal=j),'normal')
        self.assertEqual(r['capture']['status'],'error')
        self.assertEqual(r['evidence']['stores']['records']['state'],'unavailable')
        self.assertEqual(r['evidence']['diagnostics'][0],first)
        evidence.validate(r)

    def test_new_metadata_cannot_be_downgraded(self):
        r,j=self.setup_journal(max_records=1)
        for i in range(2):evidence.journal(r,j.record,'x',i)
        for compact in (False,True):
            data=report_data.payload(r,compact)
            data['report_schema']=2 if compact else 1
            with self.assertRaises(ValueError):report_data.decode(data)
