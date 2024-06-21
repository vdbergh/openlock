import os
import platform
import subprocess
import tempfile
from contextlib import ExitStack

IS_WINDOWS = "windows" in platform.system().lower()


def pid_valid(pid, name):
    with ExitStack() as stack:
        if IS_WINDOWS:
            cmdlet = (
                "(Get-CimInstance Win32_Process "
                "-Filter 'ProcessId = {}').CommandLine"
            ).format(pid)
            p = stack.enter_context(
                subprocess.Popen(
                    [
                        "powershell",
                        cmdlet,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True,
                    bufsize=1,
                    close_fds=not IS_WINDOWS,
                )
            )
        else:
            p = stack.enter_context(
                subprocess.Popen(
                    # for busybox these options are undocumented...
                    ["ps", "-f", "-a"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True,
                    bufsize=1,
                    close_fds=not IS_WINDOWS,
                )
            )
        for line in iter(p.stdout.readline, ""):
            if name in line and str(pid) in line:
                return True
    return False


def atomic_write(name, data):

    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(data)
    temp_file.flush()
    temp_file.close()

    # try linking, which is atomic, and will fail if the file exists
    try:
        os.link(temp_file.name, name)
    finally:
        # Remove the temporary file
        os.remove(temp_file.name)
