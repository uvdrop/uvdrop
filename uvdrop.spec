# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for uvdrop (onedir → Inno Setup)."""

block_cipher = None

a = Analysis(
    ["src/uvdrop/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[("policies", "policies")],
    hiddenimports=[
        "uvdrop",
        "uvdrop.ui",
        "uvdrop.ui.app",
        "uvdrop.relaunch",
        "uvdrop.launcher",
        "uvdrop.policy",
        "uvdrop.xlsx_policy",
        "uvdrop.requirements_convert",
        "uvdrop.appicon",
        "uvdrop.sample_icons",
        "uvdrop.package_spec",
        "uvdrop.ui.package_table",
        "uvdrop.usage",
        "uvdrop.resolve_deps",
        "uvdrop.i18n",
        "uvdrop.catalog",
        "uvdrop.clipboard_image",
        "uvdrop.python_support",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "_tkinter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="uvdrop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="uvdrop",
)
