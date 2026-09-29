# Acceptance audit — 2026-09-29

This audit distinguishes completed implementation from the unresolved physical success criterion. It does not redefine source-unit reconstruction as certified metric terrain.

| Requested item | Current evidence | Outcome |
|---|---|---|
| Inspect repository, code history, datasets and documentation | Two initial Git commits contain data/documentation only; inventory covers all 255 original dataset/documentation files, 224 images and every XML/LUT | Complete |
| Determine pairs, filenames, dimensions, timestamps, poses | 56 manifest rows independently validated; all images 1024 x 1024 8-bit; timestamps re-parsed; missing image XML and per-image pose stream documented | Complete investigation; poses unavailable except image-derived estimates |
| Interpret calibration without fabricated parameters | CAHV matrices parsed directly; exact projective RQ/rectification; numeric baseline retained in unspecified source units; axis-normalization sensitivity experiment | Complete, with explicit unit/frame limitation |
| Run raw stereo → rectification → disparity → depth → 3D → PLY | r01 and r07; r14 reproduces r01 arrays exactly; PLY exports and diagnostics present | Complete in source calibration units |
| One physically defensible metric stereo pair | No source states the unit of camera centers; 30–43 s acquisition gap leaves possible motion along baseline unobservable from epipolar consistency alone | **Not established; blocker** |
| Inspect, iterate and preserve experiments | Raw/NC/CLAHE comparison, widened disparity search, raw clipping mask, support filtering, rejected pair test; r01–r14 outputs retained | Complete |
| Per-frame depth | r08 processes 50 pairs and rejects six; r11 retains 50 filtered XYZ/depth arrays | Complete for supported candidates |
| Pose estimation and registration | r12 tests 129 links with held-out PnP and separate target-depth checks; 17 links accepted | Complete exploratory local registration |
| Multi-frame fusion and global cloud | Six component-local fused clouds and trajectories; 31 singletons | Local fusion complete; a single global cloud is unsupported |
| Mesh | 50 partial PLY/OBJ frame meshes and six observed-triangle component unions; exported geometry rendered and checked | Complete partial observed surfaces; no hole-filled surface claim |
| Simulator-ready terrain | Unknown metre scale/gravity, holes, overlapping faces and incomplete trajectory | **Not established; dependent blocker** |
| Report and calibration table | RECONSTRUCTION_REPORT.md, including generated measured-results appendix | Complete |
| README, environment, source documentation, configuration and commands | README.md, requirements.txt, reconstruction modules and configs; environment frozen; pip check and compilation passed | Complete |
| Intermediates, masks, clouds, meshes, trajectory, metrics and logs | artifacts/investigation and artifacts/runs; per-run provenance and parent-run links | Complete for executed stages |
| Preserve original imagery and metadata | All 255 source hashes rechecked, zero changes | Verified |
| Output validation | 118 PLYs read back; exact counts, finite coordinates, valid indices/file lengths; representative positive-area triangles and rendered previews | Verified within stated scope; does not establish physical accuracy |

The precise external inputs needed are the camera team's unit/reference-frame declaration for `C`, acquisition stationarity or motion telemetry for the stereo exposure interval, and per-product labels/selected-frame identities. Gravity/attitude and independent metric validation are additionally required before rover-navigation use. Those records cannot be recovered from the current pixels or commanded-path summaries without introducing unverified assumptions.

All useful local processing has been delivered; the requested certified metric milestone remains unfulfilled. No scale, pose, distortion or missing terrain was invented to make that milestone appear complete.
