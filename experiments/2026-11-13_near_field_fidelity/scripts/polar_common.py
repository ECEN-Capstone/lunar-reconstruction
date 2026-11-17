import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import cv2, numpy as np
D=POLAR_DIR
def rd(p):
    d={}
    for l in open(p):
        if ':' in l: k,v=l.split(':',1); d[k.strip()]=np.array(v.split(),float)
    return d
c=rd(D+'Terrain03_MeanDistr/stereo.calibration')
K1=c['CAMERA_MATRIX_LEFT'].reshape(3,3);K2=c['CAMERA_MATRIX_RIGHT'].reshape(3,3);D1=c['DISTORTION_COEFFICIENTS_LEFT'].reshape(1,4);D2=c['DISTORTION_COEFFICIENTS_RIGHT'].reshape(1,4)
R=c['ROTATION_MATRIX'].reshape(3,3);T=c['TRANSLATION_VECTOR'].reshape(3,1)
S=(1936,1216)
