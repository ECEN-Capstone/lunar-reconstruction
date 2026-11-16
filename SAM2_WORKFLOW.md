# Lunar SAM2 annotation in WSL

## Installed on this computer

Ubuntu 22.04 / WSL2, Python 3.10, isolated environment `/home/alejo/.venvs/lunar-sam2`, CPU PyTorch 2.5.1 and TorchVision 0.20.1, Meta SAM2 source `/home/alejo/src/sam2`, and SAM2.1 Hiera Tiny checkpoint `/home/alejo/models/sam2/sam2.1_hiera_tiny.pt`. Flask and headless OpenCV support the local annotation app. The computer has Intel Iris Xe graphics; this setup uses CPU inference. The optional CUDA extension is disabled. Existing Windows reconstruction requirements are separate.

## Start

From PowerShell in this repository:

```powershell
.\scripts\start-lunar-labeler.ps1
```

Open <http://localhost:7860>. Keep the terminal open; Ctrl+C stops it. The server listens on loopback only. Alternatively, in Ubuntu, change to this repository's `/mnt/c/...` directory and run:

```bash
~/.venvs/lunar-sam2/bin/python -m reconstruction.annotate
```

## Annotate

1. Choose an observation and NR (raw) or NC (calibrated) image family; load the pair. Start with obs_034. Switching pairs offers to discard unsaved work; loading resumes the latest saved revision.
2. Create an object and choose its human class: rock, crater, or unknown. SAM2 is a promptable segmenter, not a lunar rock/crater classifier.
3. Set **Click mode → Foreground prompt (+)** and click inside the object: a green dot should appear, and the foreground prompt count under that view should increase. Class and landmark selections alone do not prompt SAM2. Add background points to exclude shadows, adjacent rocks, or unwanted terrain. Segment left; expect an elapsed-time message followed by a translucent yellow mask and a nonzero mask-pixel count. Feedback stays visible in a sticky banner; missing prompts are explained before inference. Repeat independently on the right for the same object: left prompts are not copied to the right. New prompts invalidate the old mask; run segmentation again after editing. Only the best-scored mask is shown. The score is not class confidence.
4. Choose a landmark meaning. `rock_contact` is a visible point where the rock touches ground; `crater_rim` and `crater_floor` explicitly distinguish different crater features. For multiple contact/rim samples, create separate object records. There is one paired landmark per record in this first version.
5. Switch click mode to Landmark point and click the same identifiable physical point in both views. Enlarge the displayed images using the width slider and scroll for precision. Click again to correct a point; use Clear landmark to remove it. Coordinates remain floating-point, zero-based original image pixels, x right and y down. A mask's bottommost pixel is not automatically assumed to be a physical base. Leave hidden or ambiguous points unpaired.
6. Check stereo to compute sparse 3D points and rotate/zoom the point view. A pair needs positive depth in both cameras and at most 2 px reprojection and rectified vertical residual. Failed matches remain in the annotation with a rejection reason and no 3D coordinate. These checks do not replace the dense pipeline's pair-wide geometry gate.
7. Save a revision. Saved revisions are immutable; reload resumes the newest one. Unsaved edits remain in browser memory only. Save before closing. Source images are never edited.

## Outputs and geometry

`artifacts/annotations/<observation>/<family>/<UTC revision>/` contains:

- `annotations.json`: human class, landmark meaning, both image points, exact binary mask row runs, prompts, SAM2 scores, source image SHA256 hashes, model path/config, and stereo diagnostics.
- `landmarks.csv`: object IDs, native left/right x/y coordinates, status, x/y/z in metres and epipolar residual. Unpaired/rejected points have empty XYZ.
- `object_<id>_<side>.png`: lossless per-object binary masks at native size, including empty masks for manually annotated points without segmentation.
- `overlay_left.png` / `overlay_right.png`: mask and numbered contact-point previews.

The adapter in `reconstruction/annotation_geometry.py` uses the same literal CAHV calibration as `reconstruction/geometry.py`, triangulates native image correspondences, and transforms into the rectified left-camera frame (x right, y down, z forward). Mission-paper millimetres are divided by 1000 for metres. It does not sample a resized screenshot or use dense depth from another pixel. There is no global lunar frame, gravity alignment, cross-observation registration, or claim of physical ground truth. Acquisition motion and uncertain calibration still affect results. Match landmarks in real mission stereo pairs; generated image pairs do not establish metric geometry.

For integrating with existing dense reconstruction, export native left x/y through the existing left rectification homography before indexing rectified depth/XYZ arrays, and respect their validity masks. The initial labeler uses explicit paired clicks instead, which makes correspondence review possible even where dense depth has holes.

## Verify / reproduce

```bash
~/.venvs/lunar-sam2/bin/python -m reconstruction.check_annotations
~/.venvs/lunar-sam2/bin/pip check
```

Installation recipe for another WSL CPU machine (Python >=3.10 with venv and git available):

```bash
python3 -m venv ~/.venvs/lunar-sam2
source ~/.venvs/lunar-sam2/bin/activate
pip install --upgrade pip setuptools wheel
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
mkdir -p ~/src ~/models/sam2
git clone https://github.com/facebookresearch/sam2.git ~/src/sam2
SAM2_BUILD_CUDA=0 pip install --no-build-isolation -e ~/src/sam2
pip install flask opencv-python-headless
curl -fL --retry 3 https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt -o ~/models/sam2/sam2.1_hiera_tiny.pt
```

The PowerShell launcher currently targets Ubuntu and this computer's `/home/alejo` environment. Adjust it on another computer. The exact installed package versions, SAM2 commit and checkpoint hash are recorded in `report_evidence/sam2_wsl_environment.txt` after verification. Keep masks and labels for later supervised training; a future automatic proposal/classification stage will need validation on lunar images. Automatic grid mask generation and automatic semantic labeling are outside this initial prompted workflow.

Primary references: [Meta SAM2 installation and API](https://github.com/facebookresearch/sam2), [optional CUDA extension setting](https://github.com/facebookresearch/sam2/blob/main/setup.py).
