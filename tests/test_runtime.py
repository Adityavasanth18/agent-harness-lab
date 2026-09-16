import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from agentharness.benchmarks import load_tasks
from agentharness.config import Config
from agentharness.providers import HTTPProvider, RetryableError, OracleProvider
from agentharness.runtime import Runtime
from agentharness.trace import Trace, read_events

TASKS=Path(__file__).resolve().parents[1]/'benchmarks'

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.task=load_tasks(TASKS)[0]

    def test_three_architectures_and_no_oracle_leakage(self):
        class Spy(OracleProvider):
            def complete(inner,messages,**kwargs):
                text=json.dumps(messages)
                for content in self.task.tests.values(): self.assertNotIn(content,text)
                return super(Spy,inner).complete(messages,**kwargs)
        for architecture in ('single','planner','parallel'):
            with self.subTest(architecture=architecture),tempfile.TemporaryDirectory() as d:
                trace=Trace(Path(d)/'trace.jsonl','run')
                result=Runtime(Config(sandbox='local',architecture=architecture),trace,Spy()).run_task(self.task,Path(d)/'trials')
                self.assertTrue(result['success'])
                self.assertEqual(len(result['candidates']),2 if architecture=='parallel' else 1)
                requests=[e for e in read_events(trace.path) if e['event']=='request']
                self.assertTrue(all(e['trial_id']==result['trial_id'] for e in requests))

    def test_transient_request_retry(self):
        class Flaky(OracleProvider):
            calls=0
            def complete(inner,*args,**kwargs):
                inner.calls+=1
                if inner.calls==1: raise RetryableError('test')
                return super(Flaky,inner).complete(*args,**kwargs)
        with tempfile.TemporaryDirectory() as d:
            trace=Trace(Path(d)/'trace.jsonl','run')
            result=Runtime(Config(sandbox='local'),trace,Flaky()).run_task(self.task,Path(d)/'trials')
            self.assertTrue(result['success'])
            self.assertTrue(any(e.get('retry')==1 for e in read_events(trace.path)))

    def test_bad_model_does_not_pass(self):
        class Bad(OracleProvider):
            def complete(inner,*args,**kwargs):
                result=super(Bad,inner).complete(*args,**kwargs)
                result['text']='{"done":true}'
                return result
        with tempfile.TemporaryDirectory() as d:
            result=Runtime(Config(sandbox='local',max_steps=2),Trace(Path(d)/'trace.jsonl','run'),Bad()).run_task(self.task,Path(d)/'trials')
            self.assertFalse(result['success'])

    def test_injected_unittest_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            runtime=Runtime(Config(sandbox='local'),Trace(Path(d)/'trace.jsonl','run'))
            root=Path(d)/'candidate'; box=runtime.sandbox(root)
            for p,c in self.task.files.items(): box.write(p,c)
            box.write('unittest.py','print("fake success")')
            self.assertNotEqual(runtime.verify(self.task,root,'test').returncode,0)

    def test_http_stream_contract(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.server.payload=payload
                self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
                items=[{'choices':[{'delta':{'role':'assistant','content':''}}]},
                       {'choices':[{'delta':{'content':'{"done":'}}]},
                       {'choices':[{'delta':{'content':'true}'}}]},
                       {'choices':[],'usage':{'prompt_tokens':12,'completion_tokens':5}}]
                for item in items: self.wfile.write(('data: '+json.dumps(item)+'\n\n').encode()); self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            config=Config(provider='http',endpoint=f'http://127.0.0.1:{server.server_port}/v1/chat/completions')
            result=HTTPProvider(config).complete([{'role':'user','content':'task'}])
            self.assertEqual(result['text'],'{"done":true}')
            self.assertEqual(result['input_tokens'],12)
            self.assertEqual(result['output_tokens'],5)
            self.assertEqual(len(result['chunk_timestamps_ns']),2)
            self.assertIsNone(result['first_token_ns'])
            self.assertEqual(result['token_timestamps_ns'],[])
            self.assertTrue(server.payload['stream'])
        finally: server.shutdown();server.server_close();thread.join()

    def test_bad_endpoint_and_config(self):
        for endpoint in ('http://example.org/v1','file:///etc/passwd','https://user:secret@example.org/v1'):
            with self.assertRaises(ValueError): HTTPProvider(Config(endpoint=endpoint))
        for field,value in [('max_steps',1.5),('retries',True),('timeout_seconds',float('nan'))]:
            with self.assertRaises(ValueError): Config(**{field:value})

if __name__=='__main__':unittest.main()
