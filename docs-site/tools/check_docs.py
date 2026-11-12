"""Static checks for the docs site. Does not run MPF.

1. Every ```yaml block in hand-written pages parses with MPF's own YAML loader.
2. Section and setting names in those blocks exist in mpf/config_spec.yaml (fragments that start below the top
   level are matched by their first key).
3. Every internal link in every page (hand-written and generated) points at a page that exists, and anchors on
   generated pages exist.

Usage:
  python check_docs.py <mpf repo root> <hugo content dir>
Exit code 1 if any check fails.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
CONTENT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(ROOT))

from mpf.file_interfaces.yaml_interface import YamlInterface  # noqa: E402  (MPF's YAML rules)
from ruamel.yaml import YAML  # noqa: E402

SPEC = YAML(typ="safe", pure=True).load((ROOT / "mpf" / "config_spec.yaml").read_text(encoding="utf-8"))
BALL_DEVICE_SUBSPECS = ["ball_device_counter_ball_switches", "ball_device_counter_entrance_switches",
                        "ball_device_ejector_pulse", "ball_device_ejector_enable", "ball_device_ejector_hold",
                        "ball_device_ejector_event"]
errors = []
warnings = []


def err(page, msg):
    errors.append("{}: {}".format(page.relative_to(CONTENT).as_posix(), msg))


def keys_for(section):
    spec = SPEC.get(section, {})
    keys = {k for k in spec if not k.startswith("__")}
    if spec.get("__type__") == "device":
        keys |= set(SPEC["device"])
    if spec.get("__type__") == "config_player":
        keys |= set(SPEC["config_player_common"])
    if spec.get("__parent__"):
        keys |= {k for k in SPEC[spec["__parent__"]] if not k.startswith("__")}
    if section == "ball_devices":
        for sub in BALL_DEVICE_SUBSPECS:
            keys |= {k for k in SPEC[sub] if k != "class"}
    return keys, "__allow_others__" in spec


def subconfig_of(section, key):
    v = SPEC.get(section, {}).get(key)
    if isinstance(v, str):
        m = re.search(r"subconfig\((\w+)\)", v)
        if m:
            return m.group(1), v.startswith("dict|")
    return None, False


def check_settings(page, section, settings, path):
    if not isinstance(settings, dict):
        return
    allowed, allow_others = keys_for(section)
    if allow_others:
        return
    for k, v in settings.items():
        if k not in allowed:
            err(page, "unknown setting {}:{} (not in config_spec {})".format(path, k, section))
            continue
        sub, is_dict = subconfig_of(section, k)
        if sub and isinstance(v, dict):
            if is_dict:
                for name, item in v.items():
                    check_settings(page, sub, item, "{}:{}:{}".format(path, k, name))
            else:
                check_settings(page, sub, v, "{}:{}".format(path, k))


def check_block(page, text):
    try:
        data = YamlInterface.process(text)
    except Exception as e:  # noqa: BLE001
        err(page, "YAML does not parse: {}".format(str(e).splitlines()[0]))
        return
    if not isinstance(data, dict):
        return
    for top, body in data.items():
        if top in SPEC:
            typ = SPEC[top].get("__type__")
            if typ == "device":
                if isinstance(body, dict):
                    for dev, settings in body.items():
                        check_settings(page, top, settings, "{}:{}".format(top, dev))
            elif typ in ("config", None):
                check_settings(page, top, body, top)
            continue
        # fragment: a bare setting (e.g. `ball_switches: ...` or `port: ...`) used for illustration
        if any(top in keys_for(s)[0] for s in SPEC):
            continue
        err(page, "unknown top-level section {}:".format(top))


FENCE = re.compile(r"^```yaml\s*\n(.*?)^```", re.M | re.S)


def check_snippets():
    n = 0
    for page in sorted(CONTENT.rglob("*.md")):
        if "reference" in page.relative_to(CONTENT).parts:
            continue
        for m in FENCE.finditer(page.read_text(encoding="utf-8")):
            check_block(page, m.group(1))
            n += 1
    return n


LINK = re.compile(r"\]\((/[^)\s]*)\)|href=\"(/[^\"]*)\"")


def page_for(url):
    path = url.split("#")[0].strip("/")
    if not path:
        return CONTENT / "_index.md"
    for cand in (CONTENT / (path + ".md"), CONTENT / path / "_index.md", CONTENT / path / "index.md"):
        if cand.exists():
            return cand
    return None


def anchors(page):
    text = page.read_text(encoding="utf-8")
    ids = set(re.findall(r'\{#([^}]+)\}', text)) | set(re.findall(r'id="([^"]+)"', text))
    for h in re.findall(r"^#{2,6} (.+?)\s*$", text, re.M):
        h = re.sub(r"\{#[^}]+\}", "", h).strip()
        # Hugo's default heading ids: lower case, punctuation dropped, spaces to dashes
        slug = re.sub(r"[^\w\- ]", "", h.lower()).strip().replace(" ", "-")
        ids.add(slug)
    return ids


def check_links():
    n = 0
    cache = {}
    for page in sorted(CONTENT.rglob("*.md")):
        for m in LINK.finditer(page.read_text(encoding="utf-8")):
            url = m.group(1) or m.group(2)
            n += 1
            target = page_for(url)
            if not target:
                err(page, "broken link {}".format(url))
                continue
            if "#" in url:
                anchor = url.split("#", 1)[1]
                if target not in cache:
                    cache[target] = anchors(target)
                if anchor not in cache[target]:
                    err(page, "missing anchor {}".format(url))
    return n


def main():
    snippets = check_snippets()
    links = check_links()
    pages = sum(1 for _ in CONTENT.rglob("*.md"))
    print("{} pages, {} yaml snippets checked, {} internal links checked".format(pages, snippets, links))
    for w in warnings:
        print("WARN", w)
    for e in errors:
        print("ERROR", e)
    if errors:
        print("{} error(s)".format(len(errors)))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
