"""Generate the Hugo reference section from the MPF source tree.

Reads only source files (no MPF import needed except ruamel.yaml for parsing YAML):
  mpf/config_spec.yaml, mpf/mpfconfig.yaml, mpf/**/*.py, mpf/modes/*/config/*.yaml,
  mpf/commands/*.py, mpf/tests/machine_files/**.

Usage:
  python gen_reference.py <mpf repo root> <hugo content dir>

Writes <content>/reference/** (the folder is wiped first).
"""
import ast
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve() / "reference"
PKG = ROOT / "mpf"
TESTS = PKG / "tests" / "machine_files"

yaml = YAML(typ="safe", pure=True)


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def esc(text):
    """Escape for a markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def code(text):
    text = str(text)
    if "`" in text:
        return "`` " + text + " ``"
    return "`" + text + "`"


def front(title, weight=None, extra=None):
    lines = ["---", "title: " + yaml_str(title)]
    if weight is not None:
        lines.append("weight: {}".format(weight))
    for k, v in (extra or {}).items():
        lines.append("{}: {}".format(k, yaml_str(v)))
    lines.append("generated: true")
    lines.append("---\n")
    return "\n".join(lines) + "\n"


def yaml_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write(path, text):
    path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------------
# Source index: classes across the mpf package (AST, no import)
# --------------------------------------------------------------------------------------------

class ClassInfo:
    def __init__(self, module, name, node, path):
        self.module = module
        self.name = name
        self.path = path
        self.line = node.lineno
        self.doc = ast.get_docstring(node) or ""
        self.bases = [ast.unparse(b) for b in node.bases]
        self.methods = {n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.attrs = {}
        for n in node.body:
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in targets:
                    if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant):
                        self.attrs[t.id] = n.value.value
        self.imports = {}


CLASSES = {}          # "mpf.devices.switch.Switch" -> ClassInfo
BY_NAME = defaultdict(list)


def index_classes():
    for path in PKG.rglob("*.py"):
        if "tests" in path.parts:
            continue
        module = ".".join(path.relative_to(ROOT).with_suffix("").parts)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        imports = {}
        for n in tree.body:
            if isinstance(n, ast.ImportFrom) and n.module:
                for a in n.names:
                    imports[a.asname or a.name] = n.module + "." + a.name
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                info = ClassInfo(module, n.name, n, path)
                info.imports = imports
                CLASSES[module + "." + n.name] = info
                BY_NAME[n.name].append(info)


def resolve_base(info, base):
    base = base.split("[")[0]
    if base in info.imports and info.imports[base] in CLASSES:
        return CLASSES[info.imports[base]]
    local = info.module + "." + base
    if local in CLASSES:
        return CLASSES[local]
    if "." in base:
        if base in CLASSES:
            return CLASSES[base]
    cands = BY_NAME.get(base.split(".")[-1], [])
    return cands[0] if len(cands) == 1 else None


def mro(info, seen=None):
    seen = seen or set()
    out = []
    if info is None or info.module + "." + info.name in seen:
        return out
    seen.add(info.module + "." + info.name)
    out.append(info)
    for b in info.bases:
        out.extend(mro(resolve_base(info, b), seen))
    return out


def has_method(info, name):
    return any(name in c.methods for c in mro(info))


def class_attr(info, name):
    for c in mro(info):
        if name in c.attrs:
            return c.attrs[name]
    return None


def first_para(doc):
    return doc.strip().split("\n\n")[0].replace("\n", " ").strip() if doc else ""


# --------------------------------------------------------------------------------------------
# config_spec.yaml
# --------------------------------------------------------------------------------------------

SPEC_PATH = PKG / "config_spec.yaml"
SPEC = yaml.load(SPEC_PATH.read_text(encoding="utf-8"))
SPEC_LINES = {}       # (section, key) -> line number
SPEC_COMMENTS = {}    # (section, key) -> comment text


def scan_spec_raw():
    section = None
    for no, line in enumerate(SPEC_PATH.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^([a-z0-9_]+):", line)
        if m:
            section = m.group(1)
            SPEC_LINES[(section, None)] = no
            continue
        m = re.match(r"^    ([A-Za-z0-9_]+):(.*)$", line)
        if m and section:
            SPEC_LINES[(section, m.group(1))] = no
            if "#" in m.group(2):
                SPEC_COMMENTS[(section, m.group(1))] = m.group(2).split("#", 1)[1].strip()


CATEGORY = {"device": "devices", "config_player": "players", "config": "sections", "config_dict": "sections",
            "list": "sections", "named_lists": "sections", None: "shared"}
CATEGORY_TITLE = {"devices": "Devices", "players": "Config players", "sections": "Config sections",
                  "shared": "Shared and sub-settings"}


def section_url(name):
    if name not in SPEC:
        return None
    return "/reference/config/{}/{}/".format(CATEGORY[SPEC[name].get("__type__")], name.replace("_", "-"))


def link_section(name, text=None):
    url = section_url(name)
    text = text or code(name)
    return "[{}]({})".format(text, url) if url else text


def describe_validator(v):
    m = re.match(r"^(\w+)\((.*)\)$", v)
    if m:
        kind, arg = m.groups()
        if kind == "enum":
            return "one of " + ", ".join(code(x.strip()) for x in arg.split(","))
        if kind == "machine":
            return "name of a " + link_section(arg, code(arg)) + " entry"
        if kind == "subconfig":
            return link_section(arg, code(arg)) + " settings"
        if kind == "mode_settings":
            return "mode settings"
        return code(v)
    simple = {"str": "string", "int": "integer", "float": "number", "num": "number", "bool": "boolean",
              "boolean": "boolean", "ms": "time (ms)", "secs": "time (seconds)", "color": "color",
              "event_posted": "event name (posted)", "event_handler": "event name (handled)",
              "template_int": "integer or template", "template_float": "number or template",
              "template_bool": "boolean or template", "template_str": "string or template",
              "template_secs": "seconds or template", "template_ms": "ms or template",
              "pow2": "power of two", "gain": "gain", "kivycolor": "color", "color_or_token": "color or show token",
              "list": "list", "dict": "mapping"}
    return simple.get(v, code(v))


def describe_type(spec):
    container, validator, _default = spec
    if container == "single":
        return describe_validator(validator)
    if container == "list":
        return "list of " + describe_validator(validator)
    if container == "set":
        return "set of " + describe_validator(validator)
    if container == "event_handler":
        return "events, each with an optional delay"
    if container == "dict":
        k, _, v = validator.partition(":")
        return "mapping: {} → {}".format(describe_validator(k), describe_validator(v))
    return code("|".join(spec))


def describe_default(spec):
    d = spec[2]
    if d == "":
        return "**required**"
    if d.lower() == "none":
        return "*(none)*"
    return code(d)


def spec_entries(name):
    """Yield (key, spec-list or 'ignore' or dict) for a section, skipping dunders."""
    for k, v in SPEC[name].items():
        if k.startswith("__"):
            continue
        if isinstance(v, str) and v != "ignore":
            v = v.split("|")
        yield k, v


# ball_devices: settings marked ignore are validated in these sub-specs by the counter/ejector classes
BALL_DEVICE_SUBSPECS = ["ball_device_counter_ball_switches", "ball_device_counter_entrance_switches",
                        "ball_device_ejector_pulse", "ball_device_ejector_enable", "ball_device_ejector_hold",
                        "ball_device_ejector_event"]


def settings_table(name, keys=None, note_ignore=True):
    rows = ["| Setting | Type | Default |", "|---|---|---|"]
    nested = []
    for k, v in spec_entries(name):
        if keys is not None and k not in keys:
            continue
        anchor = '<span id="{}"></span>'.format(k)
        if v == "ignore":
            if not note_ignore:
                continue
            comment = SPEC_COMMENTS.get((name, k), "")
            rows.append("| {}{} | not validated here{} | |".format(anchor, code(k + ":"),
                                                                   esc(" (" + comment + ")") if comment else ""))
        elif isinstance(v, dict):
            nested.append(k)
            rows.append("| {}{} | nested settings (see below) | |".format(anchor, code(k + ":")))
        else:
            desc = describe_type(v)
            comment = SPEC_COMMENTS.get((name, k))
            if comment:
                desc += " <br><small>" + esc(comment) + "</small>"
            rows.append("| {}{} | {} | {} |".format(anchor, code(k + ":"), esc(desc), esc(describe_default(v))))
    out = "\n".join(rows) + "\n"
    for k in nested:
        out += "\n### `{}:` (nested)\n\n".format(k)
        sub = SPEC[name][k]
        r = ["| Setting | Type | Default |", "|---|---|---|"]
        for kk, vv in sub.items():
            if kk.startswith("__"):
                continue
            if isinstance(vv, str) and vv != "ignore":
                vv = vv.split("|")
                r.append("| {} | {} | {} |".format(code(kk + ":"), esc(describe_type(vv)), esc(describe_default(vv))))
            elif isinstance(vv, dict):
                r.append("| {} | nested | |".format(code(kk + ":")))
        out += "\n".join(r) + "\n"
    return out


def required_settings(name):
    return [k for k, v in spec_entries(name) if isinstance(v, list) and v[2] == ""]


# --------------------------------------------------------------------------------------------
# mpfconfig.yaml, events, test configs
# --------------------------------------------------------------------------------------------

MPFCONFIG = yaml.load((PKG / "mpfconfig.yaml").read_text(encoding="utf-8"))["mpf"]


def class_for(dotted):
    return CLASSES.get(dotted)


EVENT_RE = re.compile(r"'''event:\s*(.+?)\n(.*?)'''", re.S)


def parse_events():
    events = []
    for path in sorted(PKG.rglob("*.py")):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for m in EVENT_RE.finditer(text):
            name = m.group(1).strip()
            body = m.group(2)
            line = text.count("\n", 0, m.start()) + 1
            desc, args, cfg = [], [], []
            mode = "desc"
            for raw in body.splitlines():
                s = raw.strip()
                if s.startswith("desc:"):
                    mode = "desc"
                    s = s[5:].strip()
                elif s.startswith("args:"):
                    mode = "args"
                    s = s[5:].strip()
                elif s.startswith("config_section:") or s.startswith("config_attribute:"):
                    cfg.append(s)
                    continue
                if not s:
                    if mode == "desc" and desc and desc[-1] != "":
                        desc.append("")
                    continue
                if mode == "desc":
                    desc.append(s)
                else:
                    am = re.match(r"^([A-Za-z_0-9()]+):\s*(.*)$", s)
                    if am:
                        args.append([am.group(1), am.group(2)])
                    elif args:
                        args[-1][1] += " " + s
            text_desc = "\n".join(desc).strip()
            text_desc = re.sub(r"(?<!\n)\n(?!\n)", " ", text_desc)
            events.append({"name": name, "desc": text_desc, "args": args, "path": path, "line": line})
    return events


def test_config_files():
    files = []
    for path in sorted(TESTS.rglob("*.yaml")):
        if "config" in path.parts:
            files.append(path)
    return files


TEST_FILES = test_config_files()
TEST_TEXT = {p: p.read_text(encoding="utf-8", errors="replace") for p in TEST_FILES}


def section_blocks(section):
    """Return list of (path, block_text) for top-level `section:` blocks in tested configs."""
    out = []
    pat = re.compile(r"^{}:\s*$".format(re.escape(section)), re.M)
    for path, text in TEST_TEXT.items():
        m = pat.search(text)
        if not m:
            continue
        lines = text[m.start():].splitlines()
        block = [lines[0]]
        for ln in lines[1:]:
            if ln and not ln[0].isspace() and not ln.startswith("#"):
                break
            block.append(ln)
        while block and not block[-1].strip():
            block.pop()
        out.append((path, block))
    return out


def example_for(section):
    blocks = section_blocks(section)
    if not blocks:
        return None, []
    good = [b for b in blocks if 3 <= len(b[1]) <= 30]
    path, block = (good or blocks)[0]
    if len(block) > 30:
        block = block[:30] + ["  # ... (trimmed)"]
    return (path, "\n".join(block)), [b[0] for b in blocks]


# --------------------------------------------------------------------------------------------
# Page builders
# --------------------------------------------------------------------------------------------

def source_link(path, line=None):
    r = rel(path)
    return code(r + (":{}".format(line) if line else ""))


def build_config_pages(events):
    device_cls = {}
    for section, dotted in MPFCONFIG["device_modules"].items():
        device_cls[section] = class_for(dotted)
    player_cls = {}
    for name, dotted in MPFCONFIG["config_players"].items():
        info = class_for(dotted)
        if info:
            sec = class_attr(info, "config_file_section")
            player_cls[sec or name] = (name, info)

    events_by_file = defaultdict(list)
    for e in events:
        events_by_file[e["path"].resolve()].append(e)

    groups = defaultdict(list)
    for name in sorted(SPEC):
        if name.startswith("_"):
            continue
        entry = SPEC[name]
        typ = entry.get("__type__")
        cat = CATEGORY.get(typ, "sections")
        valid = entry.get("__valid_in__", "")
        summary = ""
        meta = []
        body = []

        info = None
        if typ == "device":
            info = device_cls.get(name)
        elif typ == "config_player":
            info = player_cls.get(name, (None, None))[1]
            if info is None:
                for pname, pdotted in MPFCONFIG["config_players"].items():
                    if pname + "_player" == name:
                        info = class_for(pdotted)
        if info:
            summary = first_para(info.doc)

        meta.append("**Kind:** {}".format({"devices": "device", "players": "config player",
                                           "sections": "config section", "shared": "sub-settings"}[cat]))
        if valid:
            places = [x.strip() for x in str(valid).split(",")]
            where = {"machine": "machine config", "mode": "mode config"}
            meta.append("**Valid in:** " + ", ".join(where.get(p, p) for p in places))
        if info:
            meta.append("**Class:** {} ({})".format(code(info.module + "." + info.name), source_link(info.path, info.line)))
        meta.append("**Spec:** " + source_link(SPEC_PATH, SPEC_LINES.get((name, None))))

        title = name + ":"
        body.append(front(title, extra={"summary": summary[:300]} if summary else None))
        if summary:
            body.append(summary + "\n")
        body.append("  \n".join(meta) + "\n")

        if cat in ("devices",):
            body.append("Each entry under `{}:` is one device, named by its key. Every device also accepts the "
                        "[common device settings](/reference/config/shared/device/).\n".format(name))
        if cat == "players":
            body.append("Entries are keyed by the event that triggers them. Every player also accepts the "
                        "[common player settings](/reference/config/shared/config-player-common/).\n")

        req = required_settings(name)
        req_text = "\n".join("- " + code(r) for r in req)
        if name == "ball_devices":
            req_text = ("- One of `eject_coil`, `hold_coil`, `mechanical_eject: true` or `ejector`. Without one, "
                        "MPF stops with *Device needs an eject_coil, a hold_coil, or \"mechanical_eject: True\"* "
                        "(`BallDevice._validate_config`, error 4).\n"
                        "- Every `eject_timeouts` value must be smaller than every `ball_missing_timeouts` value "
                        "(error 8).")
        if req_text:
            body.append("## Required settings\n\n" + req_text + "\n")

        example, used_in = example_for(name)
        if example:
            body.append("## Example\n\nFrom {} in MPF's test suite (tested by MPF's own tests):\n\n```yaml\n{}\n```\n"
                        .format(code(rel(example[0])), example[1]))

        body.append("## Settings\n\n" + settings_table(name, note_ignore=(name != "ball_devices")))

        if name == "ball_devices":
            body.append(
                "### Counter and ejector settings\n\n"
                "These settings appear in `config_spec.yaml` under `ball_devices` as `ignore` with a "
                "\"deprecated: see ...\" comment, but they are **not deprecated in practice**: the ball device copies "
                "them into its counter and ejector, which validate them against the sub-specs below "
                "(`mpf/devices/ball_device/switch_counter.py`, `pulse_coil_ejector.py` and the other ejectors). "
                "Which ones apply depends on the counter and ejector the device uses.\n")
            for sub in BALL_DEVICE_SUBSPECS:
                body.append("#### From {}\n\n".format(link_section(sub)) + settings_table(sub))

        if info and typ == "device":
            ctl = []
            for k, v in spec_entries(name):
                if k.endswith("_events") and k != "control_events" and isinstance(v, list) and v[0] == "event_handler":
                    method = "event_" + k[:-7]
                    ok = has_method(info, method)
                    ctl.append("| {} | {} | {} |".format(code(k + ":"), code(method), "yes" if ok else "**not found**"))
            if ctl:
                body.append("## Control events\n\nEach `*_events` setting lists events that make the device act. "
                            "MPF calls the device method shown (`DeviceManager.get_device_control_events`).\n\n"
                            "| Setting | Method | Method found |\n|---|---|---|\n" + "\n".join(ctl) + "\n")

        if info:
            evs = []
            for c in mro(info):
                evs.extend(events_by_file.get(Path(c.path).resolve(), []))
            seen = set()
            evs = [e for e in evs if not (e["name"] in seen or seen.add(e["name"]))]
            if evs:
                body.append("## Events posted\n\n`(name)` is the device name.\n\n" + "\n".join(
                    "- [{}](/reference/events/#{}): {}{}".format(
                        code(e["name"]), event_anchor(e["name"]), esc(e["desc"].split("\n")[0]),
                        " **Wrong name in the source; see the note on the events page.**"
                        if e["name"] in EVENT_CORRECTIONS else "") for e in evs) + "\n")

        if used_in:
            body.append("## Used in tested configs\n\n" + "\n".join("- " + code(rel(p)) for p in used_in[:15]) +
                        ("\n- ... and {} more".format(len(used_in) - 15) if len(used_in) > 15 else "") + "\n")

        write("config/{}/{}.md".format(cat, name.replace("_", "-")), "\n".join(body))
        groups[cat].append((name, summary, valid))

    # index pages
    order = ["devices", "players", "sections", "shared"]
    idx = [front("Config reference", 1),
           "Every top-level entry in `mpf/config_spec.yaml`, one page each. Devices and config players are "
           "linked to the class that implements them.\n"]
    for w, cat in enumerate(order, 1):
        idx.append("- [{}](/reference/config/{}/) ({})".format(CATEGORY_TITLE[cat], cat, len(groups[cat])))
        sub = [front(CATEGORY_TITLE[cat], w), "| Section | Valid in | Summary |", "|---|---|---|"]
        for name, summary, valid in groups[cat]:
            sub.append("| [{}](/reference/config/{}/{}/) | {} | {} |".format(
                code(name + ":"), cat, name.replace("_", "-"), esc(valid), esc(summary[:160])))
        write("config/{}/_index.md".format(cat), "\n".join(sub))
    write("config/_index.md", "\n".join(idx))


def event_anchor(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# Annotations that do not match what the code posts. Each was confirmed by running MPF; the note is shown under the
# event. Keyed by annotated name. Remove an entry when MPF is fixed (verify/test_guides.py checks they still hold).
EVENT_CORRECTIONS = {
    "multiball_(name)_lost_ball": "MPF 0.82.0.dev0 actually posts this event as `multiball_(name)_ball_lost` "
                                  "(`Multiball._ball_drain_count_balls`). Use that name in your config.",
}


def build_events(events):
    out = [front("Events", 3),
           "Every event documented in the MPF source with an `'''event: ...'''` annotation ({} events). "
           "In names, `(name)` stands for a device name and other words in parentheses for values filled in at "
           "runtime. Handle any of them in a `*_events` setting or a config player.\n".format(len(events))]
    by_group = defaultdict(list)
    for e in events:
        parts = e["path"].relative_to(PKG).parts
        group = "/".join(parts[:2]) if parts[0] in ("devices", "modes", "platforms", "plugins") else parts[0]
        by_group[group.replace(".py", "")].append(e)
    for group in sorted(by_group):
        out.append("## {}\n".format(group))
        for e in sorted(by_group[group], key=lambda x: x["name"]):
            out.append('### {} {{#{}}}\n'.format(code(e["name"]), event_anchor(e["name"])))
            if e["desc"]:
                out.append(e["desc"] + "\n")
            if e["name"] in EVENT_CORRECTIONS:
                out.append("{{< warn >}}\n**Wrong name in the source.** " + EVENT_CORRECTIONS[e["name"]] +
                           "\n{{< /warn >}}\n")
            if e["args"]:
                out.append("| Argument | Meaning |\n|---|---|\n" + "\n".join(
                    "| {} | {} |".format(code(a), esc(d)) for a, d in e["args"]) + "\n")
            out.append("<small>Source: {}</small>\n".format(source_link(e["path"], e["line"])))
    write("events.md", "\n".join(out))


def parse_cli():
    cmds = []
    for path in sorted((PKG / "commands").glob("*.py")):
        if path.stem in ("__init__", "logging_formatters"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        has_command = any(isinstance(n, ast.ClassDef) and n.name == "Command" for n in tree.body)
        if not has_command:
            continue
        doc = ast.get_docstring(tree) or ""
        args = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument":
                flags = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                kw = {k.arg: k.value for k in node.keywords}
                help_text = ""
                if "help" in kw:
                    try:
                        help_text = ast.literal_eval(kw["help"])
                    except ValueError:
                        help_text = ast.unparse(kw["help"])
                default = ""
                if "default" in kw:
                    default = ast.unparse(kw["default"])
                args.append((flags, help_text, default, node.lineno))
        cmds.append((path.stem, doc, args, path))
    return cmds


def build_cli():
    cmds = parse_cli()
    out = [front("Command line", 4),
           "`mpf <command> [machine_path] [options]`. With no command, `game` runs. A command is any module in "
           "`mpf/commands/` (`mpf/commands/__init__.py`, `CommandLineUtility.execute`); installed packages such as "
           "the media controller can add more through the `mpf.command` entry point.\n",
           "Options accepted before any command (`MpfCommandLineParser.parse_args`):\n",
           "| Option | Meaning |\n|---|---|\n| `machine_path` | Path of the machine folder (default: current folder). |\n"
           "| `-P` | Production mode. |\n| `--version` | Print MPF, config and BCP versions and exit. |\n"]
    for name, doc, args, path in cmds:
        out.append("## `mpf {}`\n".format(name))
        if doc:
            out.append(first_para(doc) + "\n")
        out.append("<small>Source: {}</small>\n".format(source_link(path)))
        if args:
            out.append("| Option | Meaning | Default |\n|---|---|---|")
            for flags, help_text, default, _ in args:
                out.append("| {} | {} | {} |".format(", ".join(code(f) for f in flags), esc(help_text),
                                                     esc(code(default)) if default else ""))
            out.append("")
    write("cli.md", "\n".join(out))


def build_modes():
    out = [front("Built-in modes", 5),
           "Modes that ship with MPF in `mpf/modes/`. `mpf/mpfconfig.yaml` already lists {} in its `modes:` list, "
           "so those run without being named in your config; the others start only when you add them to your "
           "`modes:` list. If your machine has a mode folder with the same name, your config is merged on top of "
           "the built-in one.\n".format(", ".join(code(m) for m in yaml.load((PKG / "mpfconfig.yaml").read_text())["modes"])),
           "| Mode | Priority | Start events | Stop events | Game mode | Code |", "|---|---|---|---|---|---|"]
    details = []
    for path in sorted((PKG / "modes").glob("*/config/*.yaml")):
        cfg = yaml.load(path.read_text(encoding="utf-8")) or {}
        mode = cfg.get("mode", {})
        name = path.stem
        start = mode.get("start_events", "")
        stop = mode.get("stop_events", "")
        out.append("| [{}](#{}) | {} | {} | {} | {} | {} |".format(
            code(name), name.replace("_", "-"), mode.get("priority", ""), esc(code(start)) if start else "",
            esc(code(stop)) if stop else "", "no" if mode.get("game_mode") is False else "yes",
            code(mode["code"].split(".")[-1]) if "code" in mode else ""))
        sections = [k for k in cfg if k != "mode"]
        info = class_for(mode.get("code", ""))
        d = ["## `{}` {{#{}}}\n".format(name, name.replace("_", "-"))]
        if info and info.doc:
            d.append(first_para(info.doc) + "\n")
        d.append("Config: {}".format(source_link(path)) + ("  \nCode: {}".format(source_link(info.path, info.line))
                                                             if info else "") + "\n")
        if sections:
            d.append("Also configures: " + ", ".join(link_section(s) for s in sections) + "\n")
        if "use_wait_queue" in mode:
            d.append("Uses the wait queue: the event that starts it waits until the mode stops.\n")
        details.append("\n".join(d))
    out.append("")
    out.extend(details)
    write("builtin-modes.md", "\n".join(out))


CAPS = {"SwitchPlatform": "switches", "DriverPlatform": "coils (drivers)", "LightsPlatform": "lights",
        "ServoPlatform": "servos", "StepperPlatform": "steppers", "AccelerometerPlatform": "accelerometers",
        "I2cPlatform": "I2C", "DmdPlatform": "DMD", "RgbDmdPlatform": "RGB DMD",
        "SegmentDisplayPlatform": "segment displays", "HardwareSoundPlatform": "hardware sound",
        "ShakerPlatform": "shakers", "MotorPlatform": "motors"}


def build_platforms():
    rows = []
    for name, dotted in sorted(MPFCONFIG["platforms"].items()):
        info = class_for(dotted)
        if not info:
            continue
        chain = [c.name for c in mro(info)]
        caps = [v for k, v in CAPS.items() if k in chain]
        if "SegmentDisplaySoftwareFlashPlatform" in chain and "segment displays" not in caps:
            caps.append("segment displays")
        pkg_dir = Path(info.path).parent if Path(info.path).parent.name != "platforms" else Path(info.path)
        files = list(pkg_dir.rglob("*.py")) if pkg_dir.is_dir() else [pkg_dir]
        sections = set()
        for f in files:
            t = f.read_text(encoding="utf-8")
            sections.update(re.findall(r"validate_config\(\s*[\"']([a-z0-9_]+)[\"']", t))
            sections.update(re.findall(r"get_platform_sections?\(\s*[\"']([a-z0-9_]+)[\"']", t))
            sections.update(re.findall(r"config_section\s*=\s*[\"']([a-z0-9_]+)[\"']", t))
            sections.update(re.findall(r"machine\.config\[[\"']([a-z0-9_]+)[\"']\]", t))
            # any quoted spec name that is not a device/player section (platform settings specs)
            sections.update(x for x in re.findall(r"[\"']([a-z0-9_]+)[\"']", t)
                            if x in SPEC and SPEC[x].get("__type__") in (None, "config", "config_dict")
                            and x not in ("device", "config_player_common"))
        sections = sorted(s for s in sections if s in SPEC)
        rows.append((name, info, caps, sections))
        page = [front(name, extra={"summary": first_para(info.doc)[:200]}),
                (first_para(info.doc) + "\n") if info.doc else "",
                "**Name in `hardware:`:** {}  \n**Class:** {} ({})\n".format(
                    code(name), code(dotted), source_link(info.path, info.line)),
                "## Capabilities\n\nFrom the platform interfaces the class implements (`mpf/core/platform.py`):\n\n" +
                ("\n".join("- " + c for c in caps) if caps else "- none detected (overlay or helper platform)") + "\n",
                "## Config sections it reads\n\n" + ("\n".join("- " + link_section(s) for s in sections)
                                                    if sections else "None found by the scan.") + "\n",
                "## Using it\n\n```yaml\nhardware:\n  platform: {}\n```\n\nOr per device type, for example "
                "`hardware: switches: {}`. See [`hardware:`](/reference/config/sections/hardware/).\n".format(name, name)]
        example, used_in = None, []
        for s in sections:
            example, used_in = example_for(s)
            if example:
                break
        if example:
            page.append("## Example from the test suite\n\nFrom {}:\n\n```yaml\n{}\n```\n".format(
                code(rel(example[0])), example[1]))
        write("platforms/{}.md".format(name.replace("_", "-")), "\n".join(page))
    idx = [front("Hardware platforms", 6),
           "Platforms registered in `mpf/mpfconfig.yaml` (`mpf: platforms:`). Name one in `hardware: platform:`.\n",
           "| Platform | Capabilities | Config sections |", "|---|---|---|"]
    for name, info, caps, sections in rows:
        idx.append("| [{}](/reference/platforms/{}/) | {} | {} |".format(
            code(name), name.replace("_", "-"), esc(", ".join(caps)), ", ".join(code(s) for s in sections)))
    write("platforms/_index.md", "\n".join(idx))


def build_errors():
    path = PKG / "core" / "config_validator.py"
    text = path.read_text(encoding="utf-8")
    rows = []
    for m in re.finditer(r"validation_error\((.*?)\)\s*$", text, re.M | re.S):
        pass
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "validation_error":
            if len(node.args) >= 3:
                msg = ast.unparse(node.args[2])
                code_no = ast.unparse(node.args[3]) if len(node.args) > 3 else ""
                for k in node.keywords:
                    if k.arg == "code":
                        code_no = ast.unparse(k.value)
                rows.append((code_no, msg, node.lineno))
    out = [front("Config errors", 7),
           "Config problems stop MPF with a **Config File Error**. The message has this shape "
           "(`mpf/exceptions/base_error.py`):\n",
           "```text\nConfig File Error in <logger>: <message> Error Code: CFE-<logger>-<number> (<url>)\n```\n",
           "Validation errors from `mpf/core/config_validator.py` start with "
           "`Config validation error: Entry <path> = \"<value>\" is not valid.` followed by the reason below. "
           "`<path>` names the section, device and setting, so it tells you exactly where to look.\n",
           "## Validation errors\n", "| Code | Reason (source expression) | Line |", "|---|---|---|"]
    for c, msg, line in sorted(rows, key=lambda r: (r[0] == "", r[0].zfill(3), r[2])):
        out.append("| {} | {} | {} |".format(c or "(none)", esc(code(msg)), line))
    out.append("\nCodes shown as (none) use no number in the slug. The full source is {}.\n".format(source_link(path)))
    out.append("## Common causes\n\n"
               "| Message | Usual cause |\n|---|---|\n"
               "| `Required setting \"x:\" is missing from section \"y:\"` | A setting with no default (marked **required** in the config reference) is absent. |\n"
               "| `Cannot convert value to boolean.` | A `bool` setting got something other than true/false/yes/no/on/off. |\n"
               "| `Cannot convert value to ms.` | A time setting has a typo, e.g. `2 s` or `fast`. |\n"
               "| `List contains an empty element.` | A trailing or doubled comma in a list like `a, , b`. |\n"
               "| `Item is not a dict.` | A mapping setting was given a single value or a list. |\n")
    write("errors.md", "\n".join(out))


def build_index(n_events):
    out = [front("Reference", 4),
           "Generated from the MPF source (version `{}`). Do not edit these pages by hand: run "
           "`docs-site/tools/gen_reference.py`.\n".format(
               re.search(r"__version__ = '([^']+)'", (PKG / "_version.py").read_text()).group(1)),
           "- [Config reference](/reference/config/): every config section and setting.",
           "- [Events](/reference/events/): {} annotated events.".format(n_events),
           "- [Command line](/reference/cli/)",
           "- [Built-in modes](/reference/builtin-modes/)",
           "- [Hardware platforms](/reference/platforms/)",
           "- [Config errors](/reference/errors/)\n",
           "## Reading a settings table\n",
           "| Column | Meaning |\n|---|---|\n"
           "| Setting | The key you write in YAML. |\n"
           "| Type | What the validator accepts. *list of* accepts a YAML list or a comma-separated string. "
           "*events, each with an optional delay* is an event handler setting (see "
           "[Writing config files](/get-started/config-files/#event-handlers)). *name of a `x` entry* must be a "
           "device you defined under `x:`. |\n"
           "| Default | **required** means there is no default and MPF stops with an error if it is missing. "
           "*(none)* means the setting is optional and empty. |\n",
           "Rows marked *not validated here* are accepted by the section but checked elsewhere (or ignored).\n"]
    write("_index.md", "\n".join(out))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    index_classes()
    scan_spec_raw()
    events = parse_events()
    build_config_pages(events)
    build_events(events)
    build_cli()
    build_modes()
    build_platforms()
    build_errors()
    build_index(len(events))
    n = sum(1 for _ in OUT.rglob("*.md"))
    print("wrote {} pages to {} ({} events, {} classes indexed)".format(n, OUT, len(events), len(CLASSES)))


if __name__ == "__main__":
    main()
