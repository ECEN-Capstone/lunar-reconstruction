
Chandrayaan-3 Rover Navigational Camera (NavCam) PDS4 Data Archive

Contents:
1. Introduction
2. Archive Contents
3. Contacts for more information


1.  INTRODUCTION

This is readme file containing details about the PDS4 Data Archive of NavCam payload
of Chandrayaan-3 Rover


2.  ARCHIVE CONTENTS

Under nav instrument id wise data collection, data is organized under each directory
defined by PDS4. Data is organized based on the levels of data processing and data
products definitions. data products are organized into year, month and day wise as 
yyyymmdd. The year month and day wise directory contains PDS4 data products including 
PDS4 Label products.

Below is detailed NavCam data archive structure

nav
|--bundle.xml
|--readme.txt
|
|--data
|  |
|  |--raw
|  |  |--yyyymmdd
|  |     |-- data_product
|  |
|  |--calibrated
|  |  |--yyyymmdd
|  |     |-- data_product
|  |
|--calibration
|  |--collection_calibration_inventory.csv
|  |--collection_calibration_inventory.xml
|  |--look up table files
|  |--look up table xml files
|  |
|--document
|  |--collection_document_inventory.csv
|  |--collection_document_inventory.xml
|  |--ch3_nav_pds_dp_archive_sis.pdf
|  |--ch3_nav_pds_dp_archive_sis.xml

The details about the data_product file naming conventions and formats 
please refer section 6.5 and 7 in data products archive software interface 
specification document (ch3_nav_pds_dp_archive_sis.pdf) under document 
collection.


2.1.  The observational data collections

Under the data directory there are two separate subdirectory based on the 
defined PDS4 data products levels raw and calibrated. Under each 
sub directories, there are again sub directory based on year, month and day 
wise. The year, month and day wise subdirectory contains PDS4 data products 
mainly image for two sensors defined as left and right and associated 
label files in XML format.

2.2.  The Calibration Collection

The calibration directory contains calibration files used to process the data 
products, or calibration data needed to use the data products. This calibration 
files are the look up table files that got generated during ground calibration 
exercise. All these lookup table files naming convention is based on the 
parameters mission (ch3), instrument (nav), right, left

2.3.  The Document Collection

The document directory contains documentation to help the user understand and use 
the archive data. The document collection contains data products and archive software 
interface specification document data product contains end to end to description about 
the mission, payload, data products (content, format, file naming convention) and 
archive structure as per PDS4 standard. 

3.  CONTACTS FOR MORE INFORMATION
=============================================================================
1. Amitabh
   Deputy Project Director (DPD) Data Products
   Space Applications Centre
   Ahmedabad
   Phone: 07926914727
   Email id: amitabh@sac.isro.gov.in

3. Ajay Kumar Prashar
   PDS4 Technical Support
   Space Applications Centre
   Ahmedabad
   Phone: 07926914764
   Email id: ajay_prashar@sac.isro.gov.in

4. Sreenath
   Operations Support Team
   ISTRAC
   Bengaluru
   Phone: 08028094416, 08022029173
   Email id: sreenath@istrac.gov.in
================================================================================
