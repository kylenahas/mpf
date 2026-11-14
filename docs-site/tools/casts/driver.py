"""Type commands into a real interactive bash while asciinema records it (see record.sh).

The commands and their output are real; only the typing is scripted, at a steady pace.
"""
import fcntl, json, os, pty, select, struct, sys, termios, time

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = 80
ENV = {"HOME": "/home/you", "USER": "you", "LOGNAME": "you", "TERM": "xterm-256color", "LANG": "C.UTF-8",
       "SHELL": "/bin/bash", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
       "PIP_DISABLE_PIP_VERSION_CHECK": "1"}


def record(cast, steps, rows):
    pid, fd = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", rows, COLS, 0, 0))
        os.chdir("/home/you")
        os.execvpe("asciinema", ["asciinema", "rec", "--overwrite", "-q", "-i", "1.5",
                                 "-c", "bash --noprofile --rcfile %s -i" % os.path.join(HERE, "rc.sh"), cast], ENV)
    buf = b""

    def read(timeout):
        nonlocal buf
        r, _, _ = select.select([fd], [], [], timeout)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                return False
            buf += data
            return True
        return False

    def wait_prompt(limit=600):
        end = time.time() + limit
        while time.time() < end:
            if not read(0.4) and buf.rstrip().endswith(b"$"):
                return
        raise SystemExit("no prompt in %s: %r" % (cast, buf[-300:]))

    wait_prompt()
    time.sleep(.6)
    for step in steps:
        if isinstance(step, tuple):          # ("interrupt_after", seconds, command)
            _, secs, cmd = step
        else:
            secs, cmd = None, step
        for ch in cmd:
            os.write(fd, ch.encode())
            read(0.055)
        time.sleep(.3)
        buf = b""
        os.write(fd, b"\r")
        if secs is not None:
            end = time.time() + secs
            while time.time() < end:
                read(0.2)
            os.write(fd, b"\x03")
        wait_prompt()
        time.sleep(.8)
    os.write(fd, b"exit\r")
    while read(1):
        pass
    os.waitpid(pid, 0)
    with open(cast) as f:
        header = json.loads(f.readline())
    print(cast, header.get("width"), header.get("height"), sum(1 for _ in open(cast)) - 1, "events")


def trim(cast):
    """Drop the typed `exit` at the end (keep events up to the last prompt), then hold the final screen for a second
    with an empty frame, so a page's poster time (just under the duration) shows the finished session."""
    with open(cast) as f:
        header, *events = f.read().splitlines()
    events = [json.loads(e) for e in events]
    last = max(i for i, e in enumerate(events) if e[2].endswith("$ "))
    events = events[:last + 1]
    events.append([round(events[-1][0] + 1.0, 6), "o", ""])
    with open(cast, "w", newline="\n") as f:
        f.write(header + "\n")
        for e in events:
            f.write(json.dumps(e) + "\n")


if __name__ == "__main__" and sys.argv[1] == "--trim":
    for path in sys.argv[2:]:
        trim(path)
elif __name__ == "__main__":
    out = sys.argv[1]
    # The whole install, from a home with no venv yet (needs network for pip).
    record(os.path.join(out, "install.cast"), [
        "python3 --version",
        "python3 -m venv ~/mpfenv",
        "source ~/mpfenv/bin/activate",
        "pip install mpf",
        "mpf --version",
        "mpf init my_machine",
        "ls -R my_machine",
    ], rows=24)
    # Activating and leaving the venv made above.
    record(os.path.join(out, "venv-activate.cast"), [
        "source ~/mpfenv/bin/activate",
        "which python",
        "deactivate",
        "which python3",
    ], rows=9)
