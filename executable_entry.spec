# -*- mode: python ; coding: utf-8 -*-
import os, pymunk, pygame_gui
pymunk_dir = os.path.dirname(pymunk.__file__)
# For linux and osx support, the .dylib and .so files for chipmunk need to be copied as well.
pygame_data_loc = os.path.join(os.path.dirname(pygame_gui.__file__), 'data')

block_cipher = None


a = Analysis(['executable_entry.py'],
             pathex=['.'],
             binaries=[],
             datas=[
                 ('ev3sim', 'ev3sim'),
                 (pygame_data_loc, 'pygame_gui/data'),
             ],
             hiddenimports=[
                 'opensimplex',
                 # Not sure why these are needed specifically. Might think that pyinstaller isn't windows and so doesn't include the packages.
                 'ev3dev2.button',
                 'ev3dev2.motor',
                 'ev3dev2.sensor.lego',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='ev3sim',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon="ev3sim/assets/Logo.ico",
          version="version_file.txt",
          uac_admin=False)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='ev3sim')
