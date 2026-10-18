#!/usr/bin/env python3
"""MTDI Studio startup.

Usage:
    python run.py                 start the studio (http on 8050, https on 8443)
    python run.py --self-test     run the software self test and exit

Every subsystem lives in the ``studio`` package; this file only assembles them:

    studio.app        the application sections (see studio/__init__.py)
    studio.runtime    lifecycle, streams, exports, local HTTPS
    studio.ui         instrument panels and the browser runtime
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio import APP_VERSION                        # noqa: E402
from studio import app as core                          # noqa: E402  loads every section
from studio._shared import SharedNamespace              # noqa: E402
from studio.runtime import install as install_runtime   # noqa: E402
from studio.ui import install as install_ui             # noqa: E402

NAMESPACE = SharedNamespace()
NAMESPACE["APP_VERSION"] = APP_VERSION
RUNTIME = install_runtime(NAMESPACE)
install_ui(NAMESPACE, RUNTIME)


def main(argv=None):
    return core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
