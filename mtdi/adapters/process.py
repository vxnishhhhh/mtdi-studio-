"""Any program, in any language, as an MTDI source.

    {"id": "probe", "adapter": "process", "command": ["python3", "probe.py"],
     "data_source": "SOFTWARE", "restart_after": 2}

MTDI starts the program in the project folder and reads its standard output as
protocol lines (KEY=value,...). This is how networks, logs, databases, build
systems, security tools or anything else become channels: write a small probe
that prints numbers. If the program exits it is restarted.

A manifest can start programs, so only run manifests you trust.
"""
import os
import pathlib
import subprocess

from . import Adapter


class ProcessAdapter(Adapter):
    def run(self):
        command = self.spec.get("command")
        if not command:
            raise RuntimeError("process source needs a command list")
        self.data_source = self.spec.get("data_source", "SOFTWARE")
        cwd = pathlib.Path(self.engine.project.get("_dir", "."))
        env = dict(os.environ, PYTHONUNBUFFERED="1", **{k: str(v) for k, v in self.spec.get("env", {}).items()})
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, bufsize=1)
        self.engine.set_source_state(self.id, "connected", "running " + " ".join(map(str, command)))
        try:
            for line in proc.stdout:
                if self.stop_event.is_set():
                    break
                if line.strip():
                    self.line(line)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if not self.stop_event.is_set():
            err = (proc.stderr.read() or "").strip().splitlines()[-1:] if proc.stderr else []
            self.engine.set_source_state(self.id, "offline", f"exited {proc.returncode}" + (f": {err[0]}" if err else ""))
            self.stop_event.wait(float(self.spec.get("restart_after", 2)))
