Chandrayaan-3 Navigation Camera — sorted archive

Archive contents
================

The 224 PNG files form 56 observations, each represented by four products:

  NC_family/left_NCL/   56 left-view NCL images
  NC_family/right_NCR/  56 right-view NCR images
  NR_family/left_NRL/   56 left-view NRL images
  NR_family/right_NRR/  56 right-view NRR images

The final letter of each three-letter product code is the camera side:

  L = left
  R = right

The middle letter separates two image-product families:

  C = NC family (NCL/NCR)
  R = NR family (NRL/NRR)

NCL and NRL use identical acquisition timestamps for each left scene. NCR and
NRR likewise use identical timestamps for each right scene. Visual inspection
shows that the NC and NR versions contain the same scene geometry but different
intensity/contrast processing. Because the filenames alone do not establish the
official expansion of C versus R, the directory names retain the source codes
instead of assigning an unsupported camera-type label.

Stereo pairing
==============

stereo_pairs.csv maps each observation to all four product files. Every left
observation has exactly one right counterpart with the same source code and
sequence number. The right image was acquired 29.9602 to 43.2644 seconds after
the corresponding left image (median 40.6892 seconds).

Filename structure
==================

Example:

  ch3_nav_ncl_20230823T1801171121_d_img_d32_001.png

  ch3_nav        mission/instrument prefix
  ncl            product family and side (NC, left)
  timestamp      acquisition timestamp
  d_img          image-product marker
  d32            source/station code
  001            sequence identifier

Source/station codes present: bl1, d32, gnh, kru, nno.

Original filenames are preserved. Files are copied, not altered or recompressed.
