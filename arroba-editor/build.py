# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reproducible local preview packaging; run from the isolated .venv."""
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from engine import model_path

root = Path(__file__).resolve().parent
subprocess.run([
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
    "--name", "ArrobaEditor", "--collect-all", "imageio_ffmpeg", "--collect-all", "faster_whisper",
    "--collect-all", "ctranslate2", "--collect-all", "tokenizers", "--collect-all", "onnxruntime",
    "--collect-all", "av", "--copy-metadata", "huggingface-hub", "--copy-metadata", "tqdm",
    str(root / "app.py"),
], cwd=root, check=True)
dist = root / "dist/ArrobaEditor"
if (model_path() / "model.bin").is_file():
    shutil.copytree(model_path(), dist / "models/tiny", dirs_exist_ok=True, ignore=shutil.ignore_patterns(".cache"))
for name in ("README.md", "THIRD_PARTY.md", "requirements.lock.txt"):
    shutil.copy2(root / name, dist / name)
shutil.copy2(root.parent / "LICENSE", dist / "LICENSE")
with zipfile.ZipFile(dist / "SOURCE.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.iterdir()):
        if path.suffix in {".py", ".md", ".txt"} and path.is_file():
            archive.write(path, "arroba-editor/" + path.name)
    archive.write(root.parent / "LICENSE", "LICENSE")
    archive.writestr("UPSTREAM.txt", "Concat 0.2.11, installed separately and unmodified:\nhttps://github.com/jub0t/Concat/tree/v0.2.11\nhttps://github.com/jub0t/Concat/releases/tag/v0.2.11\n")
with (dist / "DEPENDENCY-LICENSES.txt").open("w", encoding="utf-8") as output:
    for package in sorted(importlib.metadata.distributions(), key=lambda p: p.metadata.get("Name", "")):
        output.write(f"\n{'=' * 60}\n{package.metadata.get('Name')} {package.version}\n")
        output.write(str(package.metadata.get("License-Expression") or package.metadata.get("License") or "See upstream notices") + "\n")
        for file in package.files or []:
            if file.name.lower().startswith(("license", "copying", "notice")) and ".dist-info" in str(file):
                output.write(package.locate_file(file).read_text(encoding="utf-8", errors="replace") + "\n")
(dist / "BUILD.json").write_text(json.dumps({"version": "0.1.0", "python": sys.version, "concat_tested": "0.2.11"}, indent=2), encoding="utf-8")
print(dist / "ArrobaEditor.exe")
