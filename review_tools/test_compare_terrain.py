"""Adversarial review checks with analytic terrain, independent of the pipeline."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from review_tools.compare_terrain import compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ref = self.root / 'reference'
        self.ref.mkdir()
        self.axis = np.arange(3)*.05
        self.stereo = np.full((3, 3), np.nan)
        self.stereo[np.ix_([0, 2], [0, 2])] = 0
        self.truth = np.full((3, 3), .2)
        self.meta = dict(endpoints=['obs_A', 'obs_B'], pose={'source': 'analytic fixed pose'}, grid_m=.05,
                         validation={'holdout': 'obs_H'}, generator='analytic fixture', seed=1)
        self.arrays = dict(x=self.axis, y=self.axis, stereo_m=self.stereo, baseline_idw_m=np.zeros((3, 3)))
        (self.ref/'metrics.json').write_text(json.dumps(self.meta))
        np.savez(self.ref/'surfaces.npz', **self.arrays)
        np.savez(self.ref/'validation.npz', heldout_m=self.truth)

    def candidate(self, name='candidate', cell=(1, 1), height=.1):
        path = self.root/name
        path.mkdir()
        merged = self.stereo.copy()
        labels = np.where(np.isfinite(self.stereo), 1, 0)
        if cell is not None:
            merged[cell], labels[cell] = height, 3
        np.savez(path/'surfaces.npz', **self.arrays, merged_m=merged, labels=labels)
        np.savez(path/'validation.npz', heldout_m=self.truth)
        (path/'metrics.json').write_text(json.dumps(self.meta))
        return path

    def mutate(self, path, **values):
        with np.load(path/'surfaces.npz') as f:
            data = {k:f[k] for k in f.files}
        data.update(values)
        np.savez(path/'surfaces.npz', **data)

    def test_analytic_errors_and_completion_coverage(self):
        result, masks = compare(self.ref, [self.candidate()])
        run = result['runs'][0]
        self.assertEqual(result['eligible_reference_cells'], 5)
        self.assertEqual(result['common_video_cells'], 1)
        self.assertEqual(int(masks['common_video'].sum()), 1)
        self.assertAlmostEqual(run['native_video']['rmse_m'], .1)
        self.assertAlmostEqual(run['native_reference_coverage'], .2)
        self.assertAlmostEqual(run['fixed_region_video_plus_linear']['rmse_m'], np.sqrt((4*.2**2+.1**2)/5))
        self.assertEqual(run['improved_cells_vs_linear'], 1)
        self.assertEqual(run['unchanged_cells_vs_linear'], 4)

    def test_disjoint_support_is_not_claimed_as_paired_accuracy(self):
        result, _ = compare(self.ref, [self.candidate('a'), self.candidate('b', (1, 0), .4)])
        self.assertEqual(result['common_video_cells'], 0)
        self.assertIsNone(result['runs'][0]['common_video']['rmse_m'])
        self.assertEqual(result['runs'][1]['worsened_cells_vs_linear'], 0)  # equal absolute error at .4 vs 0

    def test_zero_coverage_has_no_video_error_and_exact_baseline_fallback(self):
        result, _ = compare(self.ref, [self.candidate(cell=None)])
        run = result['runs'][0]
        self.assertEqual(run['native_reference_coverage'], 0)
        self.assertIsNone(run['native_video']['rmse_m'])
        self.assertAlmostEqual(run['fixed_region_video_plus_linear']['rmse_m'], .2)

    def test_duplicate_candidate_is_rejected(self):
        p = self.candidate()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            compare(self.ref, [p, p])

    def test_changed_strict_geometry_is_rejected(self):
        p = self.candidate()
        merged = self.stereo.copy()
        merged[0, 0], merged[1, 1] = .001, .1
        self.mutate(p, merged_m=merged)
        with self.assertRaisesRegex(ValueError, 'preserved strict'):
            compare(self.ref, [p])

    def test_shifted_grid_is_rejected(self):
        p = self.candidate()
        self.mutate(p, x=self.axis+.001)
        with self.assertRaisesRegex(ValueError, 'grid coordinates'):
            compare(self.ref, [p])

    def test_different_reference_array_is_rejected(self):
        p = self.candidate()
        np.savez(p/'validation.npz', heldout_m=self.truth+.01)
        with self.assertRaisesRegex(ValueError, 'withheld reference'):
            compare(self.ref, [p])

    def test_invented_measured_label_is_rejected(self):
        p = self.candidate()
        labels = np.where(np.isfinite(self.stereo), 1, 0)
        labels[1, 1] = 1
        self.mutate(p, labels=labels)
        with self.assertRaisesRegex(ValueError, 'strict source labels'):
            compare(self.ref, [p])

    def test_different_pose_scenario_is_rejected(self):
        p = self.candidate()
        m = dict(self.meta, pose={'source': 'other'})
        (p/'metrics.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, 'pose scenario'):
            compare(self.ref, [p])


if __name__ == '__main__':
    unittest.main()
