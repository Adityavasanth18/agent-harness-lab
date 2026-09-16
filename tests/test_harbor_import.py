"""Schema-grounded synthetic fixtures, not captured live Harbor runs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from agentharness.harbor_import import import_harbor
from agentharness.metrics import aggregate
from agentharness.trace import read_events


def fixture():
    return {'id':'f845e666-1f98-4a1e-a938-1566da2f63c6','task_name':'01-stable-unique',
            'trial_name':'01-stable-unique__example','task_checksum':'test-checksum',
            'agent_info':{'name':'codex','version':'fixture','model_info':{'name':'fixture-model','provider':'openai'}},
            'started_at':'2026-09-16T12:00:00Z','finished_at':'2026-09-16T12:00:02.500000Z',
            'agent_result':{'n_input_tokens':100,'n_cache_tokens':25,'n_output_tokens':50,'cost_usd':0.01},
            'verifier_result':{'rewards':{'reward':1}},'exception_info':None}

class HarborImportTests(unittest.TestCase):
    def test_trial_roundtrip_and_honest_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'result.json'; out=Path(d)/'events.jsonl'
            src.write_text(json.dumps(fixture()))
            events=import_harbor(src,out)
            self.assertEqual(read_events(out),events)
            self.assertEqual(events[0]['end_ns']-events[0]['start_ns'],2_500_000_000)
            self.assertEqual(events[0]['harbor_usage']['n_input_tokens'],100)
            report=aggregate(events)
            self.assertEqual(report['trials']['success_rate'],1)
            self.assertEqual(report['requests']['count'],0)
            self.assertIsNone(report['requests']['ttft_ms']['mean'])
            self.assertIsNone(report['requests']['output_tokens']['total'])
            with self.assertRaises(FileExistsError): import_harbor(src,out)

    def test_job_embedded_and_child_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); trial=fixture()
            (root/'result.json').write_text(json.dumps({'id':'job','n_total_trials':1,'stats':{},'trial_results':[trial]}))
            child=root/'trial'; child.mkdir(); (child/'result.json').write_text(json.dumps(trial))
            events=import_harbor(root,root/'out.jsonl')
            self.assertEqual(len(events),1)
            self.assertEqual(events[0]['run_id'],'harbor-job-job')

    def test_error_unscored_missing_usage_null(self):
        with tempfile.TemporaryDirectory() as d:
            trial=fixture(); trial['verifier_result']=None; trial['agent_result']=None
            trial['exception_info']={'exception_type':'EnvironmentBuildError'}
            path=Path(d)/'result.json'; path.write_text(json.dumps(trial))
            event=import_harbor(path,Path(d)/'out')[0]
            self.assertIsNone(event['success']); self.assertIsNone(event['harbor_usage'])
            self.assertEqual(aggregate([event])['trials']['scored'],0)

    def test_invalid_rejected_before_output(self):
        mutations=[('finished_at',None),('started_at','bad'),('verifier_result',None),
                   ('verifier_result',{'rewards':{'reward':.5}}),('verifier_result',{'rewards':{'reward':True}}),
                   ('agent_result',{'n_input_tokens':-1}),('agent_result',{'cost_usd':float('nan')}),
                   ('finished_at','2026-09-16T12:00:02.500000'),
                   ('step_results',[{}]),('agent_info',{}),('finished_at','2026-09-15T12:00:00Z')]
        for key,value in mutations:
            with self.subTest(key=key,value=value), tempfile.TemporaryDirectory() as d:
                trial=fixture(); trial[key]=value
                path=Path(d)/'result.json'; path.write_text(json.dumps(trial)); out=Path(d)/'out'
                with self.assertRaises(ValueError): import_harbor(path,out)
                self.assertFalse(out.exists())

    def test_empty_and_conflicting_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError): import_harbor(root,root/'out')
            for name,reward in [('a',0),('b',1)]:
                child=root/name; child.mkdir(); t=fixture(); t['verifier_result']['rewards']['reward']=reward
                (child/'result.json').write_text(json.dumps(t))
            with self.assertRaises(ValueError): import_harbor(root,root/'out')

    def test_naive_and_offset_timestamps_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            trial=fixture()
            trial['started_at']='2026-09-16T12:00:00'
            trial['finished_at']='2026-09-16T12:00:02+00:00'
            path=Path(d)/'result.json'; path.write_text(json.dumps(trial))
            with self.assertRaises(ValueError): import_harbor(path,Path(d)/'out')
