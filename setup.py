from setuptools import setup

APP = ['main.py']
DATA_FILES = ['ffmpeg/ffmpeg']  # Include FFmpeg binary for macOS
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter', 'whisper', 'srt'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
