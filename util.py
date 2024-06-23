import platform
import subprocess
from contextlib import ExitStack

IS_WINDOWS = "windows" in platform.system().lower()


def pid_valid(pid, name):
    if IS_WINDOWS:
        cmdlet = (
            "(Get-CimInstance Win32_Process " "-Filter 'ProcessId = {}').CommandLine"
        ).format(pid)
        cmd = [
            "powershell",
            cmdlet,
        ]
    else:
        # for busybox these options are undocumented...
        cmd = ["ps", "-f", "-a"]

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
        bufsize=1,
        close_fds=not IS_WINDOWS,
    ) as p:

        for line in iter(p.stdout.readline, ""):
            if name in line and str(pid) in line:
                return True
    return False
