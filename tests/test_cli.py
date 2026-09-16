import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from agentharness.cli import main
from agentharness.trace import read_events

class CLITests(unittest.TestCase):
    def test_resume_and_duplicate_output(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            args=['demo','--trusted-local','--limit','1','--output',d]
            self.assertEqual(main(args),0)
            trace=Path(d)/'trace.jsonl'
            before=read_events(trace)
            self.assertEqual(sum(e['event']=='trial' for e in before),3)
            self.assertEqual(main(args),2)
            self.assertEqual(main(args+['--resume']),0)
            self.assertEqual(read_events(trace),before)
            self.assertTrue((Path(d)/'dashboard.html').exists())

    def test_local_opt_in_required(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['run','--config','configs/local-demo.json','--output',d]),2)
            self.assertFalse((Path(d)/'trace.jsonl').exists())
