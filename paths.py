import os
from pathlib import Path
import shutil
import sys


def _config_directory():
	if sys.platform == "win32":
		base_directory = os.environ.get("LOCALAPPDATA")
		if not base_directory:
			base_directory = Path.home() / "AppData" / "Local"
		return Path(base_directory) / "MinModdingAndMapping"

	if sys.platform.startswith("linux"):
		return Path.home() / ".config" / "MinModdingAndMapping"

	return Path.home() / ".config" / "MinModdingAndMapping"


def _application_directories():
	if getattr(sys, "frozen", False):
		return (Path(sys.executable).resolve().parent, Path(__file__).resolve().parent)
	return (Path(__file__).resolve().parent,)


SETTINGS_PATH = _config_directory() / "settings.json"


def _migrate_app_settings():
	if SETTINGS_PATH.exists():
		return

	for directory in _application_directories():
		old_settings = directory / "settings.json"
		if not old_settings.is_file() or old_settings.resolve() == SETTINGS_PATH.resolve():
			continue
		try:
			SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy2(old_settings, SETTINGS_PATH)
		except OSError:
			pass
		return


_migrate_app_settings()
