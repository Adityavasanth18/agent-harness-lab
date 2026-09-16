import json
import os
from pathlib import Path
import tempfile
import unittest
from agentharness.config import Config
from agentharness.context import Context, ContextOverflow, compress
from agentharness.sandbox import Sandbox
from agentharness.trace import Trace, read_events

class CoreTests(unittest.TestCase):
    def test_config_validation(self):
        for args in ({"architecture":"bad"}, {"max_steps":0}, {"parallel_agents":9}, {"context_chars":2}):
            with self.assertRaises(ValueError): Config(**args)

    def test_context_pins_and_bounds(self):
        for strategy in ("sliding", "summary"):
            c = Context("system", "original task", strategy, 2100)
            for i in range(10): c.add("user", str(i)*800)
            messages = c.messages()
            self.assertEqual(messages[:2], c.pinned)
            self.assertLessEqual(len(json.dumps(messages)),2100)
            self.assertGreater(c.compactions,0)

    def test_full_overflow(self):
        c = Context("system", "task", "full", 200)
        c.add("user", "x"*300)
        with self.assertRaises(ContextOverflow): c.messages()

    def test_compression(self):
        value = compress("a"*5000+"TAIL",200)
        self.assertLessEqual(len(value),200)
        self.assertTrue(value.endswith("TAIL"))

    def test_paths_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            b=Sandbox(d,"local")
            for path in ("../escape", "/tmp/escape", "."):
                with self.assertRaises(ValueError): b.write(path,"bad")
            b.write("nested/good.txt","hello")
            self.assertEqual(b.read("nested/good.txt"),"hello")
            if os.name != "nt":
                (Path(d)/"link").symlink_to(Path(d)/"nested",target_is_directory=True)
                with self.assertRaises(ValueError): b.read("link/good.txt")

    def test_command_timeout_and_output_cap(self):
        import sys
        with tempfile.TemporaryDirectory() as d:
            b=Sandbox(d,"local",timeout=.1,output_limit=100)
            r=b.run([sys.executable,"-c","import time; time.sleep(5)"])
            self.assertTrue(r.timed_out)
            r=b.run([sys.executable,"-c","print('a'*5000)"])
            self.assertEqual(len(r.output),100)

    def test_trace_corruption_reports_line(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"trace.jsonl"
            Trace(p,"x").emit("tool",status="ok")
            self.assertEqual(len(read_events(p)),1)
            with p.open("a") as f: f.write("broken\n")
            with self.assertRaisesRegex(ValueError,"line 2"): read_events(p)

if __name__ == '__main__': unittest.main()
