# setup.py
from setuptools import setup

APP = ['msanalyzer_gui.py']
DATA_FILES = [
    'wang_lab_logo.png',
    # include any additional assets (e.g. icons)
]
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'wang_lab_logo.icns',   # optional: convert your PNG to ICNS first
    'plist': {
        'CFBundleName': 'MSAnalyzer',
        'CFBundleDisplayName': 'MSAnalyzer',
        'CFBundleIdentifier': 'org.yourorg.msanalyzer',
        'CFBundleVersion': '1.0.0',
    },
    'packages': ['pandas','matplotlib','seaborn','plotly','netCDF4','scipy','PIL'],
    'includes': ['parser','plot_utils','csv_viewer'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
