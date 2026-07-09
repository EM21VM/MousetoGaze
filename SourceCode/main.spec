# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# Sammelt automatisch alle versteckten Daten- und Modelldateien ein
mediapipe_datas = collect_data_files('mediapipe')
eyetrax_datas = collect_data_files('eyetrax', include_py_files=True)
l2cs_datas = collect_data_files('l2cs', include_py_files=True) # Vorsichtshalber auch für L2CS

all_datas = mediapipe_datas + eyetrax_datas + l2cs_datas

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=all_datas,
    hiddenimports=[
        # --- Eyetrax & Scikit-Learn ---
        'eyetrax', 
        'eyetrax.gaze',
        'eyetrax.calibration',
        'eyetrax.calibration.five_point',
        'eyetrax.utils',
        'eyetrax.utils.screen',
        'screeninfo',
        'sklearn',               
        'sklearn.neural_network',
        
        # --- GazeTracking ---
        'GazeTracking',
        'GazeTracking.gaze_tracking',
        'GazeTracking.pupil',
        'GazeTracking.calibration',
        'GazeTracking.eye',
        'dlib',
        
        # --- L2CS-Net & PyTorch ---
        'l2cs', 
        'l2cs.pipeline',
        'torch',
        'torchvision',
        
        # --- MediaPipe Explicit Imports ---
        'mediapipe',
        'mediapipe.python.solutions.face_mesh',
        'mediapipe.python.solutions.drawing_utils',
        
        # --- Hardware / OS Backends ---
        'pynput.keyboard._win32', 
        'pynput.mouse._win32',
        'pyscreeze',             
        'cv2'                    
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EyetrackerController',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Icon.ico'],
)