# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/plugins', 'plugins'), ('src/data', 'data')],
    hiddenimports=[],
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
