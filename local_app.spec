# ─────────────────────────────────────────────────────────────────────────────
# local_app.spec  —  PyInstaller build spec for BatStateU Local Station
# ─────────────────────────────────────────────────────────────────────────────
#
# HOW TO BUILD (run this once on your development PC):
#
#   1. Install PyInstaller:
#        pip install pyinstaller
#
#   2. Place this file in the SAME folder as local_app.py
#
#   3. Run:
#        pyinstaller local_app.spec
#
#   4. Output will be in:  dist/AttendanceStation/
#
#   5. Copy these files/folders INTO dist/AttendanceStation/ manually:
#        local.html
#        login.html   (if used standalone)
#        .env
#        faces/       (folder — created automatically on first use if missing)
#        uploads/     (folder — created automatically on first use if missing)
#
#   6. Zip the entire dist/AttendanceStation/ folder and share it.
#      The instructor extracts it and double-clicks launch.bat
#
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# ── Collect data files from packages that need them ──────────────────────────

# InsightFace ships ONNX model configs and detection data
insightface_datas = collect_data_files('insightface')

# ReportLab needs its font/graphics data
reportlab_datas   = collect_data_files('reportlab')

# ── Hidden imports ─────────────────────────────────────────────────────────────
# PyInstaller cannot auto-detect these because they are loaded dynamically
hidden = [
    # Flask internals
    'flask',
    'flask_cors',
    'werkzeug',
    'werkzeug.utils',
    'werkzeug.serving',
    'werkzeug.routing',
    'jinja2',
    'itsdangerous',
    'click',

    # Database
    'psycopg2',
    'psycopg2.extras',
    'psycopg2._psycopg',

    # Environment
    'dotenv',
    'python_dotenv',

    # Cloudinary
    'cloudinary',
    'cloudinary.uploader',
    'cloudinary.api',

    # Face recognition
    'insightface',
    'insightface.app',
    'insightface.model_zoo',
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi._pybind_state',

    # Image / Camera
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',

    # PDF
    'reportlab',
    'reportlab.platypus',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.colors',
    'reportlab.lib.units',
    'reportlab.lib.styles',
    'reportlab.lib.enums',

    # Standard lib extras
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'urllib',
    'urllib.request',
    'urllib.parse',
    'json',
    'threading',
    'socket',
    'webbrowser',
]

a = Analysis(
    ['local_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # ── HTML served by Flask ──────────────────────────────────────────
        ('local.html',    '.'),
        ('login.html',    '.'),

        # ── Static assets (logo, favicon) — add if present ───────────────
        # ('face.png',  '.'),
        # ('red.png',   '.'),

        # ── Package data ──────────────────────────────────────────────────
        *insightface_datas,
        *reportlab_datas,
    ],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy packages not needed at runtime
        'matplotlib',
        'scipy',
        'pandas',
        'notebook',
        'IPython',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AttendanceStation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,          # Keep True — shows Flask logs so instructor can see errors
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='face.ico',     # Uncomment and provide a .ico file to set the EXE icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AttendanceStation',   # Output folder name inside dist/
)
