"""Run repro_create.py on the three blobs, each in its own process, and print CRASH / OK."""
import os, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
for name, expect in [("repro.cso", "crashes"), ("repro_fixed_init.cso", "control"),
                     ("repro_fixed_break.cso", "control")]:
    p = subprocess.run([sys.executable, os.path.join(here, "repro_create.py"),
                        os.path.join(here, name), "ps"], capture_output=True, text=True)
    code = p.returncode & 0xFFFFFFFF
    if code == 0 and "OK hr=0x00000000" in p.stdout:
        state = "OK"
    elif code >= 0xC0000000:  # NTSTATUS error: the process was killed by an exception
        state = "CRASH"
    else:                     # no device, D3D error HRESULT, bad path...
        state = "ERROR"
    print("%-24s %-5s (exit 0x%08x, expected on affected driver: %s)"
          % (name, state, code, expect))
    if state == "ERROR":
        print("    " + (p.stdout + p.stderr).strip().replace("\n", "\n    "))
