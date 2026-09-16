import tempfile
import unittest
from pathlib import Path
from agentharness.metrics import aggregate, percentile
from agentharness.dashboard import render_dashboard
from agentharness.optimize import select_configurations
from agentharness.replay import context_counterfactual


def req(start=0, end=1_000_000_000, **kw):
    return dict(event="request", run_id="run", task_id="task", start_ns=start, end_ns=end,
                input_tokens=kw.pop("input_tokens", 10), output_tokens=kw.pop("output_tokens", 20), **kw)


class MetricTests(unittest.TestCase):
    def test_empty_is_unknown(self):
        r = aggregate([])
        self.assertIsNone(r["requests"]["output_tokens_per_second"])
        self.assertIsNone(r["trials"]["success_rate"])

    def test_chunk_is_not_token(self):
        r = aggregate([req(chunk_timestamps_ns=[100_000_000, 300_000_000])])["requests"]
        self.assertEqual(r["ttft_ms"]["p50"], 100)
        self.assertEqual(r["chunk_interval_ms"]["p50"], 200)
        self.assertIsNone(r["token_itl_ms"]["p50"])

    def test_touching_intervals_not_concurrent(self):
        r = aggregate([req(), req(1_000_000_000, 2_000_000_000)])["requests"]
        self.assertEqual(r["peak_concurrent_requests"], 1)
        self.assertEqual(r["output_tokens_per_second"], 20)

    def test_overlap(self):
        self.assertEqual(aggregate([req(), req(1, 2)])["requests"]["peak_concurrent_requests"], 2)

    def test_missing_usage_no_partial_throughput(self):
        r = aggregate([req(), req(output_tokens=None)])["requests"]
        self.assertIsNone(r["output_tokens_per_second"])
        self.assertEqual(r["output_tokens"]["known_total"], 20)

    def test_percentile_interpolates(self):
        self.assertEqual(percentile([10, 20], 50), 15)

    def test_dashboard_script_escape(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "report.html"
            render_dashboard([req(model="</script><img src=x onerror=alert(1)>")], p)
            text = p.read_text()
            self.assertNotIn("</script><img", text)
            self.assertIn("\\u003c/script", text)

    def test_optimizer_measured_constraints(self):
        t = dict(event="trial", run_id="run", task_id="task", start_ns=0, end_ns=1_000_000_000,
                 success=True, architecture="single", config={})
        r = select_configurations([req(), t], min_success_rate=1, max_tokens=30)
        self.assertIsNotNone(r["recommendations"]["observed"])
        r = select_configurations([req(output_tokens=None), t], max_tokens=30)
        self.assertIsNone(r["recommendations"]["observed"])

    def test_derived_tpot_is_not_itl(self):
        r = aggregate([req(output_tokens=3, chunk_timestamps_ns=[100_000_000, 500_000_000])])["requests"]
        self.assertEqual(r["derived_chunk_tpot_ms"]["mean"], 200)
        self.assertIsNone(r["token_itl_ms"]["mean"])
        r = aggregate([req(output_tokens=3, estimated_tokens=True, chunk_timestamps_ns=[1, 9])])["requests"]
        self.assertIsNone(r["derived_chunk_tpot_ms"]["mean"])

    def test_trial_join_and_configured_cost(self):
        t = dict(event="trial", run_id="run", task_id="task", trial_id="trial1", start_ns=0, end_ns=1_000_000_000,
                 success=True, config={"input_cost_per_million":2, "output_cost_per_million":4})
        r = aggregate([req(), t])
        self.assertAlmostEqual(r["efficiency"]["configured_rate_total_cost"], .0001)
        self.assertEqual(select_configurations([req(), t], max_tokens=30)["configurations"][0]["mean_total_tokens"], 30)
        t["config"] = {}
        self.assertIsNone(aggregate([req(), t])["efficiency"]["configured_rate_total_cost"])

    def test_separate_clock_domains(self):
        a, b = req(), req()
        b["run_id"] = "other"
        r = aggregate([a, b])
        self.assertIsNone(r["requests"]["output_tokens_per_second"])
        self.assertEqual(r["requests"]["peak_concurrent_requests"], 1)
        self.assertEqual(len(r["by_run"]), 2)

    def test_metadata_replay_preserves_task(self):
        e = req(message_sizes=[{"role":"system", "characters":10}, {"role":"user", "characters":20},
                               {"role":"assistant", "characters":30}, {"role":"user", "characters":40}])
        r = context_counterfactual([e], 1)["requests"][0]
        self.assertTrue(r["metadata_only"])
        self.assertEqual(r["retained_characters"], 70)
        self.assertEqual(r["retained_messages"], 3)

    def test_replay_does_not_predict(self):
        r = context_counterfactual([req(messages=[{"role":"system", "content":"abc"}, {"role":"user", "content":"12345"}])], 0)
        self.assertFalse(r["executed"])
        self.assertEqual(r["requests"][0]["retained_characters"], 8)
        self.assertIsNone(r["requests"][0]["predicted_latency_ms"])


if __name__ == "__main__":
    unittest.main()
