# Midterm evidence and revision notes

## Writing requirement and AI-use restriction

The supplied Fall 2026 ECEN 403 Section 927 syllabus states on page 5 that the midterm and final reports are individually written and assessed, with at least 2,000 words of finished, graded writing across the two assignments. It assigns at least 33% of the overall grade to individual writing quality. Page 6 lists October 1 as the midterm deadline.

Page 9 explicitly prohibits AI text generators for submitted work, including creating or revising drafts, editing the student's work, and reviewing a peer's work. It exempts pre-existing spelling/grammar software. The advisor's emails encourage coding assistance, but the supplied messages do not establish an exception for report writing. `INDIVIDUAL_MIDTERM_REPORT.md` is an AI-assisted draft and is marked accordingly; it should not be treated as submission-ready under the supplied rule. The restriction was discovered after the initial draft had been created.

Source: [syllabus](C:/Users/rhunt/Documents/Capstone/docs/ecen403hsyllabus.pdf), pp. 5–6, 9. No additional midterm word limit or prescribed citation style was found in the supplied syllabus or emails.

## Individual contribution and attribution

| Evidence | Supported statement | Limit |
|---|---|---|
| User's account | Rylee first generated SAM2 masks for the backup pipeline, then used Astra at the advisor's request to construct the reconstruction pipeline | Exact personal prompting, debugging, and review history was not supplied |
| Meeting slides, p. 18 | Rylee: feature identification/classification; Jonathan: initial stereo geometry; Alejandro: integration/interfaces; Arjun and Austin: navigation/simulation | Do not attribute every team implementation to Rylee |
| Meeting slides, pp. 27–29 | Jetson setup was in progress; the plan pivoted from YOLOv8 training to SAM2 masks; small rocks remained difficult | No completed Jetson deployment or measured embedded performance established |
| `lunar_detection/workspace/generate_masks.py` | Automatic SAM2.1 Hiera Tiny workflow with binary masks, previews, geometric CSV metadata, and a manual class field | Current source settings do not prove historical settings for every output |
| Current saved SAM2 outputs | 224 label files and previews, 843 masks; six images with no retained masks; all class entries blank | These are proposals, not 843 verified rocks/craters or distinct physical objects |
| Reconstruction records, September 29 | 50 supported local reconstructions, six registered components, documented numerical and consistency checks | No certified metric scale, gravity alignment, or absolute terrain accuracy |

The report retains the detailed navigation numbers as attributed statements from the supplied group draft. They were not independently verified against a navigation repository during this task.

## SAM2 inspection results

Read-only inspection of `C:/Users/rhunt/Documents/Capstone/lunar_detection/workspace` found:

| Product family / camera | Input images | CSV files | Mask records |
|---|---:|---:|---:|
| Calibrated left (NCL) | 56 | 56 | 234 |
| Calibrated right (NCR) | 56 | 56 | 211 |
| Raw left (NRL) | 56 | 56 | 205 |
| Raw right (NRR) | 56 | 56 | 193 |
| Total | 224 | 224 | 843 |

All 843 referenced masks exist. Every mask passed checks for binary values, recorded image dimensions, area, bounding box, and centroid. These checks were performed with AI assistance during this report-preparation task on September 30; they are not claimed as independent earlier student validation. No SAM2 inference was rerun, no source images or masks were changed, and no semantic ground-truth comparison was performed.

The current source selects CUDA when available and otherwise CPU; this does not prove which device generated the saved outputs. It specifies a 16-by-16 sampling grid, batch size 8, predicted-IoU threshold 0.8, stability threshold 0.95, no crop layers, disabled optional model postprocessing, and a later minimum area of 25 pixels. Saved CSVs do not supply runtime, model hashes, or device provenance.

Evidence records: [inventory](C:/Users/rhunt/Documents/Capstone/reconstruction/report_evidence/sam2_inventory.json) and [mask/CSV checks](C:/Users/rhunt/Documents/Capstone/reconstruction/report_evidence/sam2_output_checks.json).

## Arjun's seven action items

The exact source is Arjun's September 27 email on page 2 of [emals2.pdf](C:/Users/rhunt/Documents/Capstone/docs/emals2.pdf). Dr. Fan's September 29 reply on page 3 directs the midterm report to address these items and distinguish progress, validation, and next steps.

| Action item | Evidence / current status | Remaining work |
|---|---|---|
| 1. Show raw data, stereo coverage, sequence length, lighting variation | Slides pp. 4–8 show raw images, temporal gaps, overlap, and preliminary geometry; reconstruction has a raw contact sheet and diagnostics | Preserve observation identities and show representative failures alongside successful scenes |
| 2. Normalize lighting, attempt point cloud/mesh, cross-check with Claude Code | Raw/archived-calibrated/CLAHE comparisons and 50 partial meshes exist | Lighting robustness is not proven; no completed Claude Code cross-check was found; Astra development is distinct |
| 3. Verify intrinsics, extrinsics, baseline information in the XML/positioning archive | CAHV files and collection labels investigated; derived geometry documented | Center units/frame, per-image labels/poses, and exposure-interval motion remain unresolved |
| 4. Catalog lunar datasets, usable video sequences, metadata, dense overlap | Local NavCam archive characterized; slides report a separate 33-frame monocular Rover Imager set and no continuous video in this subset | Broader catalog not demonstrated; reconcile slides' 55 raw-right frames with local repositories' 56 |
| 5. Survey prior 3D lunar-terrain augmentation before rock/crater augmentation | Advisor gives conceptual guidance and examples; slides record proposed generator designs | No completed literature survey found; do not label this item complete |
| 6. Identify physical test platform through Dr. Majji or Dr. Ambrose | Request documented | No confirmed rover access or completed outreach outcome found in supplied records; the Jetson board is not a rover platform |
| 7. Continue simulation sensor development/integration | Group draft documents separate RGB-D validation and navigation baseline | Closed-loop sensor-driven obstacle response and terrain handoff remain integration work |

## Chronology and source conflicts

- September 3: Dr. Fan calls for geometry and statistics grounded in real observations, relightable terrain, and a generator constrained by those observations. This is a project direction, not evidence that augmentation is implemented.
- September 20: Dr. Fan recommends simplifying feature detection to SAM/SAM2 plus verification and avoiding a new diffusion/Transformer training effort at this stage.
- September 23 slide update: SAM2 pivot and small-rock difficulties.
- September 27: Arjun's seven action items.
- September 29: reconstruction technical record and advisor report guidance.
- September 30: saved-file audit during this chat.

The current-week slides are marked NOT READY FOR REVIEW. Earlier slides' 48/56 preliminary screening result and later reconstruction's 50/56 accepted runs use different criteria; do not present them as identical tests or a measured improvement. Earlier slides discuss a nominal 0.240 m baseline and assumed camera parameters, while the later reconstruction deliberately retains source calibration units. Use the later technical record for the evaluated implementation and preserve the earlier figures as historical context.

## Available visual evidence

- Slides p. 29: contemporaneous SAM2 preview and the stated small-rock limitation.
- SAM2 `workspace/outputs/`: 224 previews alongside input images and full-resolution masks; the inventory record lists example paths.
- Slides p. 5: raw stereo pair with a 43.20-second exposure separation.
- Slides p. 6: three overlapping viewpoints spanning 13 minutes 9 seconds, illustrating sparse temporal overlap rather than video.
- Reconstruction `artifacts/runs/r11_filtered_batch/obs_029/mesh_views.png`: partial observed local mesh.
- Reconstruction `artifacts/runs/r12_registration/component_obs_044/mesh_views.png`: registered triangle union with visible holes.

Any reported figure should identify its source observation, units, and whether it shows a mask proposal, observed geometry, or proposed augmentation. Neither model-confidence scores nor attractive mesh renders establish ground-truth accuracy.

## Remaining personal detail

Only Rylee can supply an accurate account of the specific prompts, implementation decisions, manual checks, corrections, and interpretation personally performed during Astra-assisted development. The draft intentionally does not invent those experiences. The provided emails establish AI coding guidance generally and a Claude Code cross-check request specifically; the statement that the advisor requested Astra comes from Rylee's direct account.
