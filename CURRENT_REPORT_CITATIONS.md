# Citation placements for the current PDF

Source: Rylee Hunt Individual Technical Report.pdf (10 pages). The cited copy preserves all body wording and figures and appends a References page.

- Page 2: For the first pipeline, I initially developed a system to generate SAM2 [1] masks of rocks and

- Page 4: Once the team decided to pivot to direct terrain reconstruction from Chandrayaan-3 [2] stereo

- Page 4: examined. These models encode the camera centers and projection vectors [2].

- Page 5: Camera projection is derived from the CAHV parameters found in Chandrayaan-3 documentation. Rectification transforms the two images into a common viewing geometry so that corresponding points lie approximately on the same image row [3]. After rectification, disparity represents the horizontal separation between corresponding points. Depth is calculated using

- Page 5: where Z is depth, f is focal length, B is the stereo baseline, and d is disparity [4].

- Page 5: Dense matching uses OpenCV’s StereoSGBM implementation [5]. Experiments were completed to compare raw imagery, radiometrically calibrated imagery, and contrast enhancement. On one observation (Observation 003), the initial raw run retained 123,115 points, while the calibrated run retained 148,250. Contrast enhancement retained 129,904. These comparisons show differences in coverage, but increased point count alone does not establish improved accuracy. For example, radiometric processing can obscure the appearance of clipped raw pixels without restoring information lost during acquisition.

## References

[1] N. Ravi *et al.*, “SAM 2: Segment anything in images and videos,” arXiv:2408.00714, 2024, doi: 10.48550/arXiv.2408.00714.

[2] Space Applications Centre, Indian Space Research Organisation, *Chandrayaan-3 Navigational Camera (NavCam) PDS4 Data Products and Archive Software Interface Specification*, ver. 2.0. Ahmedabad, India, Jul. 3, 2024, sec. 6.4.2 and Appendix H.

[3] OpenCV, “Camera calibration and 3D reconstruction,” *OpenCV 4.13.0 Documentation*, “stereoRectify.” Accessed: Oct. 1, 2026. [Online]. Available: https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html

[4] OpenCV, “Depth map from stereo images,” *OpenCV 4.13.0 Documentation*. Accessed: Oct. 1, 2026. [Online]. Available: https://docs.opencv.org/4.13.0/dd/d53/tutorial_py_depthmap.html

[5] OpenCV, “cv::StereoSGBM class reference,” *OpenCV 4.13.0 Documentation*. Accessed: Oct. 1, 2026. [Online]. Available: https://docs.opencv.org/4.13.0/d2/d85/classcv_1_1StereoSGBM.html

## Separate factual correction

Page 8 retains the source wording “2.18 × 10^-11 mm” because this pass is limited to citations. The saved geometry_tests.json records calibration units, not verified millimeters. No external reference validates that unit conversion.

Reference [2] is the exact local version 2.0 mission document already inspected in the reconstruction repository. Its date comes from its own change history. No DOI or direct public PDF URL was verified; none is invented. Official retrieval instructions are at https://pradan.issdc.gov.in/ch3/faq.xhtml (NavCam section).
