"""Run repro_create.py on the three blobs, each in its own process, and print CRASH / OK."""
import os, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
for name, expect in [("repro.cso", "crashes"), ("repro_fixed_init.cso", "control"),
                     ("repro_fixed_break.cso", "control")]:
    p = subprocess.run([sys.executable, os.path.join(here, "repro_create.py"),
                        os.path.join(here, name), "ps"], capture_output=True, text=True)
    ok = p.returncode == 0 and "OK hr=0x00000000" in p.stdout
    code = p.returncode & 0xFFFFFFFF
    print("%-24s %-5s (exit 0x%08x, expected on affected driver: %s)"
          % (name, "OK" if ok else "CRASH", code, expect))
