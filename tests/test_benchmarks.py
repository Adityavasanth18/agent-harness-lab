import json
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import unittest
import tomllib
from agentharness.benchmarks import load_tasks, materialize, write_files
from agentharness.harbor import export_harbor

ROOT = Path(__file__).resolve().parents[1]

class BenchmarkTests(unittest.TestCase):
    def test_starters_fail_oracles_pass(self):
        tasks = load_tasks(ROOT / 'benchmarks/micro')
        self.assertEqual(len(tasks), 30)
        for task in tasks:
            with self.subTest(task=task.id), tempfile.TemporaryDirectory() as d:
                materialize(task,d)
                self.assertFalse((Path(d)/'test_solution.py').exists())
                write_files(task.tests,d)
                argv=[sys.executable,*task.verify[1:]]
                broken=subprocess.run(argv,cwd=d,capture_output=True,text=True,timeout=5)
                self.assertNotEqual(broken.returncode,0,task.id)
                write_files(task.solution,d)
                # Ensure import caches cannot reuse starter bytecode after quick writes.
                import shutil
                shutil.rmtree(Path(d)/'__pycache__',ignore_errors=True)
                fixed=subprocess.run(argv,cwd=d,capture_output=True,text=True,timeout=5)
                self.assertEqual(fixed.returncode,0,f'{task.id}\n{fixed.stderr}')

    def test_export(self):
        tasks=load_tasks(ROOT/'benchmarks/micro')
        with tempfile.TemporaryDirectory() as d:
            paths=export_harbor(tasks,d)
            self.assertEqual(len(paths),30)
            for path in paths:
                config=tomllib.loads((path/'task.toml').read_text())
                self.assertEqual(config['schema_version'],'1.3')
                self.assertEqual(config['environment']['network_mode'],'no-network')
                self.assertTrue((path/'tests/test_solution.py').is_file())
                self.assertFalse((path/'environment/workspace/test_solution.py').exists())
                if shutil.which('sh'):
                    subprocess.run(['sh','-n',str(path/'tests/test.sh')],check=True)
                    subprocess.run(['sh','-n',str(path/'solution/solve.sh')],check=True)
                self.assertIn('printf "0\\n"', (path/'tests/test.sh').read_text())
            with self.assertRaises(FileExistsError): export_harbor(tasks,d)

    def test_reject_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            for path in ('../outside','/tmp/outside','x/../../outside','a\\b'):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    write_files({path:'bad'},d)
            try:
                (Path(d)/'link').symlink_to(Path(d).parent,target_is_directory=True)
            except (OSError, NotImplementedError):
                return  # Windows may require elevated symlink privileges.
            with self.assertRaises(ValueError): write_files({'link/outside':'bad'},d)

    def test_reject_duplicate_id_and_test_collision(self):
        task=json.loads(next((ROOT/'benchmarks/micro').rglob('task.json')).read_text())
        with tempfile.TemporaryDirectory() as d:
            for name in ('a','b'):
                folder=Path(d)/name; folder.mkdir(); (folder/'task.json').write_text(json.dumps(task))
            with self.assertRaises(ValueError): load_tasks(d)
            task['tests']={'solution.py':'oops'}
            (Path(d)/'a/task.json').write_text(json.dumps(task))
            with self.assertRaises(ValueError): load_tasks(Path(d)/'a')
