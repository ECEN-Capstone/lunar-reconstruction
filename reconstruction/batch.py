"""Run all geometrically supported pairs and retain explicit rejected observations."""
import argparse
import csv
import json
from .geometry import ROOT
from .investigate import DATA
from .stereo import run, ReconstructionRejected


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);args=p.parse_args()
    out=ROOT/'artifacts/runs'/args.run;out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads((ROOT/'configs/terrain.json').read_text())
    geometry={r['observation']:r for r in json.loads((ROOT/'artifacts/investigation/stereo_geometry.json').read_text())}
    results=[]
    for row in csv.DictReader((DATA/'stereo_pairs.csv').open()):
        obs=row['observation_id'];g=geometry[obs]
        accepted=g['matches']>=40 and g['literal']['median_abs_y']<=1 and g['literal']['p90_abs_y']<=2
        if not accepted:
            record=dict(observation=obs,status='rejected',reason='Insufficient matches or fixed-rig epipolar residual exceeds gate',geometry=g)
            print(json.dumps(record),flush=True)
        else:
            try:
                record=dict(status='reconstructed',**run(row,cfg,out/obs))
            except ReconstructionRejected as exc:
                record=dict(observation=obs,status='rejected',reason=str(exc))
        results.append(record);(out/'batch_metrics.json').write_text(json.dumps(results,indent=2))
    (out/'config.json').write_text(json.dumps(cfg,indent=2))


if __name__=='__main__':main()
