"""Fold a GMC page's scene files into {{< scenefile >}} blocks.

    python fold_scenes.py gmc/slides.md slides/base.tscn slides/ramp_lit.tscn ...

Each named file's labelled block (a line holding only `path`: then the code block) is wrapped in a scenefile shortcode,
so the page shows it collapsed under the editor steps. The label line stays, so the GMC tests still read the file.
"""
import re
import sys
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[2] / "content"


def fold(page, names):
    path = CONTENT / page
    text = path.read_text(encoding="utf-8")
    for name in names:
        label = "`%s`:" % name
        pattern = re.compile(r"^%s[ \t]*\n\s*\n```\w*\s*\n.*?^```[ \t]*\n" % re.escape(label), re.M | re.S)
        match = pattern.search(text)
        if not match:
            raise SystemExit("no block for %s in %s" % (name, page))
        before = text[:match.start()]
        if before.rstrip().endswith("{{< scenefile \"%s\" >}}" % name):
            continue
        text = before + '{{< scenefile "%s" >}}\n%s{{< /scenefile >}}\n' % (name, match.group(0)) + text[match.end():]
    path.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    fold(sys.argv[1], sys.argv[2:])
