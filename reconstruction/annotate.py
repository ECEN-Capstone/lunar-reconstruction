"""Local SAM2-assisted stereo annotation. Run with python -m reconstruction.annotate."""
import argparse
import csv
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_file
from .geometry import ROOT
from .annotation_geometry import triangulate

DATA = ROOT / 'chandrayaan-3-navcam-sorted'
OUTPUT = ROOT / 'artifacts/annotations'
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
lock = threading.Lock()
predictor = None
predictor_image = None
checkpoint = Path.home() / 'models/sam2/sam2.1_hiera_tiny.pt'
model_config = 'configs/sam2.1/sam2.1_hiera_t.yaml'
device = 'cpu'
with (DATA / 'stereo_pairs.csv').open(newline='') as f:
    PAIRS = {r['observation_id']: r for r in csv.DictReader(f)}


def image_path(obs, family, side):
    if obs not in PAIRS or family not in ('NR', 'NC') or side not in ('left', 'right'):
        raise ValueError('Unknown observation, image family or side')
    key = {('NR', 'left'): 'nrl_left_path', ('NR', 'right'): 'nrr_right_path',
           ('NC', 'left'): 'ncl_left_path', ('NC', 'right'): 'ncr_right_path'}[family, side]
    return DATA / PAIRS[obs][key]


def image(obs, family, side):
    im = cv2.imread(str(image_path(obs, family, side)), cv2.IMREAD_COLOR)
    if im is None:
        raise ValueError('Image unavailable; check Git LFS downloads')
    return im


def point(p, width, height):
    a = np.asarray(p, float)
    if a.shape != (2,) or not np.isfinite(a).all() or not (0 <= a[0] < width and 0 <= a[1] < height):
        raise ValueError('Point outside native image')
    return a.tolist()


@app.errorhandler(ValueError)
def bad_input(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(KeyError)
@app.errorhandler(TypeError)
def malformed_input(error):
    return jsonify(error='Malformed annotation request'), 400


@app.get('/')
def index():
    return send_file(Path(__file__).with_name('annotation_ui.html'))


@app.get('/api/pairs')
def pairs():
    return jsonify(observations=list(PAIRS), device=device, checkpoint=str(checkpoint))


@app.get('/api/image/<obs>/<family>/<side>')
def get_image(obs, family, side):
    return send_file(image_path(obs, family, side), mimetype='image/png')


@app.post('/api/segment')
def segment():
    global predictor, predictor_image
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    d = request.get_json(); obs, family, side = d['observation'], d['family'], d['side']
    im = image(obs, family, side); height, width = im.shape[:2]
    prompts = d['prompts']
    if not prompts or len(prompts) > 100:
        raise ValueError('Provide 1–100 foreground/background prompts')
    coords = [point(p['xy'], width, height) for p in prompts]
    labels = [p['label'] for p in prompts]
    if any(p not in (0, 1) for p in labels) or 1 not in labels:
        raise ValueError('At least one foreground prompt is required')
    with lock, torch.inference_mode():
        if predictor is None:
            torch.set_num_threads(min(8, os.cpu_count() or 1))
            predictor = SAM2ImagePredictor(build_sam2(model_config, str(checkpoint), device=device,
                                                       apply_postprocessing=False))
        key = (obs, family, side)
        if predictor_image != key:
            predictor.set_image(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)); predictor_image = key
        masks, scores, _ = predictor.predict(point_coords=np.asarray(coords),
                                             point_labels=np.asarray(labels), multimask_output=True)
    best = int(np.argmax(scores)); mask = masks[best].astype(np.uint8)
    # Row runs preserve the exact binary mask, unlike simplified contours.
    runs = []
    for y, row in enumerate(mask):
        edges = np.diff(np.pad(row.astype(np.int8), (1, 1)))
        runs.extend([[y, int(a), int(b)] for a, b in zip(np.where(edges == 1)[0], np.where(edges == -1)[0])])
    return jsonify(runs=runs, score=float(scores[best]), width=width, height=height)


def validate(d):
    obs, family = d['observation'], d['family']
    ims = {s: image(obs, family, s) for s in ('left', 'right')}
    objects = d['objects']
    if not isinstance(objects, list) or len(objects) > 1000:
        raise ValueError('Invalid object list')
    ids = set()
    for obj in objects:
        if not isinstance(obj['id'], int) or obj['id'] < 1 or obj['id'] in ids:
            raise ValueError('Object IDs must be unique positive integers')
        ids.add(obj['id'])
        if obj['class'] not in ('rock', 'crater', 'unknown') or obj['landmark'] not in ('rock_contact', 'crater_rim', 'crater_floor', 'unknown'):
            raise ValueError('Unknown class or landmark')
        for side in ('left', 'right'):
            h, w = ims[side].shape[:2]; view = obj[side]
            if view.get('base') is not None:
                view['base'] = point(view['base'], w, h)
            for prompt in view.get('prompts', []):
                point(prompt['xy'], w, h)
            for y, a, b in view.get('runs', []):
                if not all(isinstance(v, int) for v in (y, a, b)) or not (0 <= y < h and 0 <= a < b <= w):
                    raise ValueError('Invalid mask run')
        obj['stereo'] = (triangulate(obj['left']['base'], obj['right']['base'])
                         if obj['left'].get('base') is not None and obj['right'].get('base') is not None
                         else dict(status='unpaired', reason='Mark the same visible physical point in both images'))
    return ims


@app.post('/api/preview')
def preview():
    d = request.get_json(); validate(d)
    return jsonify(objects=d['objects'])


@app.get('/api/session/<obs>/<family>')
def session(obs, family):
    image_path(obs, family, 'left')
    folders = sorted((OUTPUT / obs / family).glob('*/annotations.json'))
    return jsonify(json.loads(folders[-1].read_text()) if folders else dict(objects=[]))


@app.post('/api/save')
def save():
    d = request.get_json(); ims = validate(d)
    out = OUTPUT / d['observation'] / d['family'] / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True, exist_ok=False)
    d.update(schema_version=1, coordinate_system='native pixels, zero-based x right / y down; no resize or rectification',
             source_images={s: dict(path=str(image_path(d['observation'], d['family'], s).relative_to(ROOT)),
                                   sha256=hashlib.sha256(image_path(d['observation'], d['family'], s).read_bytes()).hexdigest()) for s in ims},
             model=dict(checkpoint=str(checkpoint), config=model_config, device=device),
             caveat='Human classifications and correspondences; per-point checks do not establish pair-wide rig validity or acquisition stationarity.')
    with (out / 'landmarks.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['object_id', 'class', 'landmark', 'left_x_px', 'left_y_px', 'right_x_px', 'right_y_px', 'stereo_status', 'x_m', 'y_m', 'z_m', 'epipolar_error_px'])
        for obj in d['objects']:
            st = obj['stereo']
            writer.writerow([obj['id'], obj['class'], obj['landmark'], *(obj['left'].get('base') or ['', '']),
                             *(obj['right'].get('base') or ['', '']), st['status'], *(st.get('xyz_rectified_left_m') or ['', '', '']), st.get('epipolar_error_px', '')])
            for side, im in ims.items():
                mask = np.zeros(im.shape[:2], np.uint8)
                for y, a, b in obj[side].get('runs', []):
                    mask[y, a:b] = 255
                cv2.imwrite(str(out / f"object_{obj['id']:04}_{side}.png"), mask)
                overlay = im.copy(); overlay[mask > 0] = (0, 190, 240)
                im[:] = cv2.addWeighted(im, .7, overlay, .3, 0)
                if obj[side].get('base') is not None:
                    xy = tuple(np.rint(obj[side]['base']).astype(int))
                    cv2.drawMarker(im, xy, (20, 255, 20), cv2.MARKER_CROSS, 18, 2)
                    cv2.putText(im, str(obj['id']), xy, cv2.FONT_HERSHEY_SIMPLEX, .6, (20, 255, 20), 2)
    for side, im in ims.items():
        cv2.imwrite(str(out / f'overlay_{side}.png'), im)
    (out / 'annotations.json').write_text(json.dumps(d, indent=2, allow_nan=False))
    return jsonify(path=str(out), objects=d['objects'])


def main():
    global checkpoint, device
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, default=checkpoint)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--port', type=int, default=7860)
    args = parser.parse_args(); checkpoint, device = args.checkpoint, args.device
    app.run(host='127.0.0.1', port=args.port, threaded=False)


if __name__ == '__main__':
    main()
