# -*- mode: python ; coding: utf-8 -*-


import os

def get_venv_site_packages():
    # Helper to find site-packages in the current venv
    # Assuming standard structure: .venv/Lib/site-packages on Windows
    # Adjust if cross-compiling, but for local build this is fine
    import site
    return site.getsitepackages()[1] # usually the user/venv site-packages

site_packages = get_venv_site_packages()
keystone_path = os.path.join(site_packages, 'keystone')
capstone_path = os.path.join(site_packages, 'capstone')

# Recursive helper to find DLLs
def find_dlls(base_path, target_folder_name):
    binaries = []
    if not os.path.exists(base_path): return binaries
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith('.dll'):
                full_path = os.path.join(root, file)
                # target path structure in dist, keep it relative-ish or flat?
                # Usually capstone expects dll in its package root or specific lib dir.
                # Simplest is to copy to package root in dist.
                binaries.append((full_path, target_folder_name))
    return binaries

extra_binaries = []
extra_binaries.extend(find_dlls(keystone_path, 'keystone'))
extra_binaries.extend(find_dlls(capstone_path, 'capstone'))

# Fallback: if recursive search failed (e.g. empty), try specifically pointing to where we think they are based on common installs
# But recursive should catch them if they exist.

from PyInstaller.utils.hooks import collect_all

# ... (existing dll finding code) ...

datas = [('src/plugins', 'plugins'), ('src/data', 'data')]
binaries = extra_binaries
hiddenimports = ['keystone', 'capstone', 'PIL']

# Collect comprehensive data/binaries/imports for complex packages
for pkg in ['rapidocr', 'rapidocr_onnxruntime', 'pix2text', "numpy", "doclayout_yolo", "cnocr", "spellchecker", "transformers.models.metaclip_2"]:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='pytoolbox',
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
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='pytoolbox',
)

# Compile AutoHotkey script after build
import os
import subprocess
from pathlib import Path

def compile_ahk():
    """Compile start_toolbox.ahk to exe and copy to dist folder"""
    ahk_script = Path('start_pyinstaller.ahk')
    dist_dir = Path('dist/pytoolbox')
    
    if not ahk_script.exists():
        print(f"Warning: {ahk_script} not found, skipping AHK compilation")
        return
    
    # Check if Ahk2Exe compiler exists
    ahk2exe_paths = [
        r'C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe',
        r'C:\Program Files (x86)\AutoHotkey\Compiler\Ahk2Exe.exe',
        os.path.expandvars(r'%localappdata%\Programs\AutoHotkey\Compiler\Ahk2Exe.exe'),
    ]
    
    ahk2exe = None
    for path in ahk2exe_paths:
        if os.path.exists(path):
            ahk2exe = path
            break
    
    if not ahk2exe:
        print("Warning: Ahk2Exe.exe not found, copying .ahk file instead")
        # Just copy the .ahk file
        import shutil
        shutil.copy(ahk_script, dist_dir / ahk_script.name)
        return
    
    import shutil
    # Compile AHK to exe
    output_exe = dist_dir / 'start_pyinstaller.exe'
    try:
        subprocess.run([
            ahk2exe,
            '/in', str(ahk_script),
            '/out', str(output_exe),
        ], check=True)
        print(f"Successfully compiled {ahk_script} to {output_exe}")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling AHK script: {e}")
        # Fallback: copy the .ahk file
        shutil.copy(ahk_script, dist_dir / ahk_script.name)
    shutil.copy("toolbox.bat", dist_dir / "toolbox.bat")

compile_ahk()
