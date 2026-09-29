"""Validate filename pairing and test the published radiometric recipe literally."""
import csv
import hashlib
import json
from datetime import datetime
import cv2
import numpy as np
from .geometry import ROOT,CAL
from .investigate import DATA


def main():
    rows=list(csv.DictReader((DATA/'stereo_pairs.csv').open()));intervals=[];radiometry=[]
    for row in rows:
        left=datetime.strptime(row['left_timestamp'],'%Y%m%dT%H%M%S%f')
        right=datetime.strptime(row['right_timestamp'],'%Y%m%dT%H%M%S%f')
        delta=(right-left).total_seconds();assert abs(delta-float(row['right_minus_left_seconds']))<1e-7;intervals.append(delta)
        for key in ['nrl_left_path','nrr_right_path','ncl_left_path','ncr_right_path']:
            path=DATA/row[key];parts=path.stem.split('_')
            assert parts[3]==row['left_timestamp' if 'left' in key else 'right_timestamp']
            assert parts[-2]==row['source_station_code'] and parts[-1]==row['sequence_id'] and path.exists()
    for side,rawkey,nckey in [('left','nrl_left_path','ncl_left_path'),('right','nrr_right_path','ncr_right_path')]:
        raw=cv2.imread(str(DATA/rows[2][rawkey]),0).astype(float);reference=cv2.imread(str(DATA/rows[2][nckey]),0)
        offset,gain,gain_offset=[np.loadtxt(CAL/f'ch3_nav_{side}_{name}.txt',delimiter=',') for name in ['offset','gain','gain_offset']]
        counts=raw-offset;rad=counts*gain+gain_offset;calculated=rad*np.ptp(counts)/np.ptp(rad)
        floor=np.clip(calculated,0,255).astype(np.uint8);rounded=np.clip(np.rint(calculated),0,255).astype(np.uint8)
        radiometry.append(dict(side=side,floor_MAE=float(np.mean(abs(floor.astype(float)-reference))),
            round_MAE=float(np.mean(abs(rounded.astype(float)-reference))),floor_exact_fraction=float((floor==reference).mean()),round_exact_fraction=float((rounded==reference).mean())))
    sample=DATA/rows[2]['nrl_left_path'];md5=hashlib.md5(sample.read_bytes()).hexdigest()
    assert sample.stat().st_size==538421 and md5=='981e24e50057fc4c1b5cc06196fe5550'
    result=dict(pair_count=len(rows),interval_seconds=[min(intervals),float(np.median(intervals)),max(intervals)],
        obs003_radiometry=radiometry,obs003_sample_label_md5_verified=md5)
    (ROOT/'artifacts/investigation/metadata_audit.json').write_text(json.dumps(result,indent=2));print(result)


if __name__=='__main__':main()
