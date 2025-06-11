import PyInstaller.__main__
import os
import shutil

def build_executable():
    PyInstaller.__main__.run([
        'muse_obs_gui.py',
        '--onefile',
        '--windowed',
        '--name=MuseOBSTranslator',
        '--icon=icon.ico',
        '--add-data=config.json:.',
    ])

    # Copy additional files to dist
    shutil.copy('INSTALL.md', 'dist/INSTALL.md')
    shutil.copy('config.json', 'dist/config.json')

if __name__ == "__main__":
    build_executable()