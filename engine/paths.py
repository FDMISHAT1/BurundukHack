"""Centralized path resolution — works for dev, PyInstaller, and cx_Freeze."""
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Get the project root directory.

    Works in all contexts:
    - Development: returns project root (parent of engine/)
    - PyInstaller --onefile: returns temp extraction dir (sys._MEIPASS)
    - PyInstaller --onedir: returns the dist folder
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
LANG_DIR = DATA_DIR / "lang"
SAVE_DIR = BASE_DIR / "saves"
DOCKER_DIR = BASE_DIR / "docker"
