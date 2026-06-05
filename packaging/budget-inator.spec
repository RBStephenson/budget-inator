# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Budget-inator standalone build.
#
# Run from the PROJECT ROOT (not this directory):
#   pyinstaller packaging/budget-inator.spec --distpath dist-standalone
#
# The frontend must be built first:
#   cd frontend && npm run build
#
# Output: dist-standalone/budget-inator  (or budget-inator.exe on Windows)

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(".").resolve()
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"

block_cipher = None

# ReportLab ships fonts/data files it loads at runtime — bundle them.
reportlab_datas = collect_data_files("reportlab")
reportlab_hidden = collect_submodules("reportlab")

a = Analysis(
    [str(ROOT / "packaging" / "standalone.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=[
        # Bundle the built React frontend
        (str(FRONTEND_DIST), "dist"),
        # Bundle the backend app package (needed for relative imports)
        (str(BACKEND / "app"), "app"),
        *reportlab_datas,
    ],
    hiddenimports=[
        # uvicorn internals that PyInstaller misses
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # FastAPI / Starlette
        "starlette.staticfiles",
        "starlette.routing",
        "aiofiles",
        "aiofiles.os",
        "aiofiles.threadpool",
        # SQLAlchemy dialects
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.pysqlite",
        # Pydantic
        "pydantic",
        "pydantic_settings",
        "pydantic.deprecated.class_validators",
        # PDF report rendering
        *reportlab_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="budget-inator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX can trigger AV false-positives; keep off by default
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # Console window so users can see errors on first run
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
