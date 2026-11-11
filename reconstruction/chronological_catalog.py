"""Inventory chronological stereo endpoints without inventing missing rover poses."""
import json
from pathlib import Path

import numpy as np

from .video_bridge import ROOT, RUNS, relative


def main():
    frames = []
    for path in (RUNS / 'r11_filtered_batch').glob('obs_*/provenance.json'):
        if not (path.parent / 'xyz_rectified_calibration_units.npy').exists():
            continue
        meta = json.loads(path.read_text())
        frames.append((meta['observation']['left_timestamp'], path.parent.name))
    frames.sort()
    priors = json.loads((ROOT / 'configs/video_mobility_priors.json').read_text())
    rows = []
    for (ta, a), (tb, b) in zip(frames, frames[1:]):
        row = dict(start=a, end=b, utc=[ta, tb])
        if ta == tb:
            row.update(status='same timestamp; not a chronological motion interval')
        else:
            T, path = relative(a, b)
            prior = priors.get(a+':'+b)
            if T is not None:
                shift = float(np.linalg.norm(T[:3, 3]))
                row.update(status='registered stereo pose' if shift >= .05 else 'registered; insufficient translation',
                           displacement_m=shift, registration_path=path)
            elif prior and ta < prior['event_utc'] < tb:
                row.update(status='conditional mobility prior', prior=prior)
            else:
                row.update(status='relative pose unavailable')
        rows.append(row)
    counts = {status: sum(r['status'] == status for r in rows) for status in sorted({r['status'] for r in rows})}
    output = dict(stereo_observations=len(frames), adjacent_intervals=len(rows), counts=counts,
                  scope='Adjacent supported stereo observations by timestamp, not every archive image.',
                  caveats=['Registration paths may include other observations; a heldout test must exclude its validation observation.',
                           'Mobility commands are conditional priors, not achieved pose measurements.',
                           'No connection is created for an unavailable relative pose.'], intervals=rows)
    out = ROOT / 'output/chronological_video/chronological_catalog.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2))
    print(json.dumps({k: output[k] for k in ['stereo_observations', 'adjacent_intervals', 'counts']}, indent=2))


if __name__ == '__main__':
    main()
