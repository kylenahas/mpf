"""Take Godot editor screenshots for a GMC docs page.

Builds the page's project like the GMC tests do (verify/test_gmc.py), adds the test-only editor plugin in this
folder, opens the Godot editor on it and saves the screenshots listed in a JSON spec.

    python take_shots.py <spec.json>

The spec: {"page": "gmc/install-and-connect.md", "extra_pages": [...], "size": "1600x900",
           "shots": [{"scene": "res://slides/attract.tscn", "select": "Title", "out": "install-title.png"}, ...]}
"out" names are written to docs-site/static/images/gmc/editor/. Needs MPF_DOCS_GODOT and MPF_DOCS_GMC.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent.parent
sys.path.insert(0, str(DOCS / "verify"))
import test_gmc as tg  # noqa: E402

OUT = DOCS / "static" / "images" / "gmc" / "editor"


def main(spec_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    files = {}
    for page in spec.get("extra_pages", []) + [spec["page"]]:
        files.update(tg.page_files(page))
    for rel, body in spec.get("files", {}).items():
        files[rel] = body
    files["gmc.cfg"] = tg.with_godot_path(files.get("gmc.cfg", "[cli]\ngodot_exec_path=\"\"\n"))
    files["project.godot"] = files["project.godot"].replace(
        'enabled=PackedStringArray("res://addons/mpf-gmc/plugin.cfg")',
        'enabled=PackedStringArray("res://addons/mpf-gmc/plugin.cfg", "res://addons/doc_shots/plugin.cfg")')
    path = tg.build_project(files)
    shutil.copytree(HERE, path / "addons" / "doc_shots", ignore=shutil.ignore_patterns("*.py", "*.json", "__pycache__"))
    OUT.mkdir(parents=True, exist_ok=True)
    shots = [dict(s, out=str(OUT / s["out"]).replace("\\", "/")) for s in spec["shots"]]
    shot_list = Path(tempfile.mkdtemp(prefix="mpf_docs_shots_")) / "doc_shots.json"
    shot_list.write_text(json.dumps(shots), encoding="utf-8")
    try:
        env = dict(os.environ, MPF_DOCS_EDITOR_SHOTS=str(shot_list).replace("\\", "/"))
        result = subprocess.run([tg.GODOT, "--editor", "--path", str(path), "--resolution", spec.get("size", "1600x900")],
                                capture_output=True, text=True, timeout=spec.get("timeout", 300), env=env)
        for line in ((result.stdout or "") + (result.stderr or "")).splitlines():
            if "DOC_EDITOR" in line or "ERROR" in line:
                print(line)
    finally:
        shutil.rmtree(shot_list.parent, ignore_errors=True)
        shutil.rmtree(tg.godot_user_dir(path.name), ignore_errors=True)
        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1])
