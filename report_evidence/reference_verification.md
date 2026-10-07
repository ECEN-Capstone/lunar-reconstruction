# Reference verification — October 1, 2026

Updated `INDIVIDUAL_MIDTERM_REPORT.md` and saved the same bibliography separately as `IEEE_REFERENCES.md`. No other current report file was identified in the visible project inventory. All body wording is unchanged after removing old and new citation markers. The former internal evidence list is preserved in `internal_sources_before_ieee.md`; experimental results now carry no reference numbers.

| Reference | Verification and scope |
|---|---|
| [1] SAM 2 paper | Original arXiv record verifies Nikhila Ravi as first author, 17 additional authors, the title, 2024 submission, arXiv identifier, and DOI 10.48550/arXiv.2408.00714. Cited explicitly as the 2024 preprint; no unverified conference pagination or conference DOI is added. |
| [2] Meta FAIR SAM 2 repository | Official repository confirms automatic mask generation and the SAM2.1 Hiera Tiny checkpoint. Its model section dates SAM 2.1 to September 29, 2024. The live repository has an access date rather than an invented single publication year. |
| [3] ISRO NavCam SIS | Exact local PDF used by reconstruction: `chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf`. Title page identifies Space Applications Centre, ISRO, Ahmedabad. Change history on p. 4 identifies version 2.0, July 3, 2024; Appendix H on p. 51 documents CAHV. All three pages visually inspected. The accompanying XML labels an older edition, so its January date and version 1.0 were not substituted for the PDF's own version/date. No DOI or public direct-PDF URL was verified, so neither is invented. This is cited as a technical document with a local link, not as a web page. |
| [4] OpenCV rectification documentation | Verified official versioned page and `stereoRectify` discussion of horizontal epipolar lines with matching y coordinates. Documentation version does not assert the installed project's OpenCV version. |
| [5] OpenCV stereo-depth tutorial | Verified explicit relationship disparity = Bf/Z, equivalent to Z = fB/d. The tutorial's code uses StereoBM; it is cited only for geometry, not as the StereoSGBM implementation reference. |
| [6] OpenCV StereoSGBM class documentation | Verified official class reference describing the modified Hirschmuller algorithm, supported modes, and parameters. No original-algorithm performance claims were added. |

Public mission-document retrieval instructions were verified at [ISRO PRADAN's NavCam FAQ](https://pradan.issdc.gov.in/ch3/faq.xhtml): Other Downloads → nav → nav.zip → document directory. That URL is a retrieval guide, not a direct link to the version 2.0 PDF, and is therefore not mislabeled as the document URL in the bibliography.

All web access dates are October 1, 2026. Web documentation pages do not receive invented publication years or DOIs. The SAM paper's DOI is verified on the original arXiv record.

Citation placement: [1] at the first main-body SAM2 tool mention; [2] at the checkpoint/automatic-generation description; [3] at source image specifications and the CAHV description; [4] at the rectification explanation; [5] at Z = fB/d; [6] at the StereoSGBM implementation mention. The abstract is left without citations. All six references occur in order of first citation; every listed entry is cited.
