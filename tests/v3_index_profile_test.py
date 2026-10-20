"""The diagnostic must keep constructor work outside the frozen cold timer."""
import unittest
from unittest.mock import patch

import profile_search_index as profiler


class IndexProfileTest(unittest.TestCase):
    def test_constructor_and_ingest_connection_scopes_are_separate(self):
        report = profiler.run_once(0)
        phases = report['phases']
        self.assertEqual(phases['initialize']['calls'], 1)
        self.assertEqual(phases['initialize_connect']['calls'], 1)
        self.assertEqual(phases['connect']['calls'], report['records'])
        self.assertEqual(phases['ingest']['calls'], report['records'])
        self.assertEqual(phases['validate']['calls'], report['records'])
        self.assertEqual(phases['seed_total']['ms'], report['cold_index_ms'])
        self.assertIn('inclusive', report['phase_semantics'])

    def test_failed_seed_restores_every_instrumented_method(self):
        names = ('__init__', '_connect', '_validate', 'ingest')
        original = {name: getattr(profiler.runtime.MemoryStore, name) for name in names}
        with patch.object(profiler.evaluator, 'seed_store', side_effect=ValueError('synthetic')):
            with self.assertRaisesRegex(ValueError, 'synthetic'):
                profiler.run_once(0)
        for name, method in original.items():
            self.assertIs(getattr(profiler.runtime.MemoryStore, name), method)


if __name__ == '__main__':
    unittest.main()
