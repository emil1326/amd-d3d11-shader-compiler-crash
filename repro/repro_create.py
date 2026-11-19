"""Hand ONE compiled DXBC blob to the real D3D11 driver and call Create<Stage>Shader on it.

    python repro_create.py <file.cso> [vs|gs|ps|hs|ds|cs] [--wer]     (default: ps)

Prints "OK hr=0x..." if the driver took it. If the driver's shader compiler crashes,
the whole process dies with exit code 0xC0000005, so use ONE blob per process.

The crash happens on a driver worker thread. By default Windows Error Reporting then
holds the process for a few seconds to write a dump, and the main thread can finish
and exit 0 in the meantime, which hides the crash. So this script turns the WER dialog
off for itself (SetErrorMode), and the fault ends the process at once with 0xC0000005.
Pass --wer to keep Windows Error Reporting: you get the Application event log entry and
the minidump, but the exit code is then not reliable (it is often 0).
Windows only. Python 3 + ctypes, nothing to install.
"""
import ctypes, sys, time

args = [a for a in sys.argv[1:] if a != "--wer"]
if not args:
    sys.exit(__doc__)
if "--wer" not in sys.argv:
    # SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX: an unhandled fault kills the process
    # immediately instead of handing it to WerFault.exe first
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)

d3d11 = ctypes.WinDLL("d3d11")
dev = ctypes.c_void_p()
ctx = ctypes.c_void_p()
fl = ctypes.c_uint(0)
levels = (ctypes.c_uint * 1)(0xB000)  # D3D_FEATURE_LEVEL_11_0
# D3D_DRIVER_TYPE_HARDWARE = 1, SDK version 7, default adapter
hr = d3d11.D3D11CreateDevice(None, 1, None, 0, levels, 1, 7,
                             ctypes.byref(dev), ctypes.byref(fl), ctypes.byref(ctx))
if hr != 0:
    print("CreateDevice hr=0x%08x" % (hr & 0xFFFFFFFF))
    sys.exit(2)

blob = open(args[0], "rb").read()
stage = args[1] if len(args) > 1 else "ps"
# ID3D11Device vtable slots of the Create*Shader methods
slot = {"vs": 12, "gs": 13, "ps": 15, "hs": 16, "ds": 17, "cs": 18}[stage]
vtable = ctypes.cast(ctypes.cast(dev, ctypes.POINTER(ctypes.c_void_p))[0],
                     ctypes.POINTER(ctypes.c_void_p))
create = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_char_p,
                            ctypes.c_size_t, ctypes.c_void_p,
                            ctypes.POINTER(ctypes.c_void_p))(vtable[slot])
out = ctypes.c_void_p()
hr = create(dev, blob, len(blob), None, ctypes.byref(out))
time.sleep(2.0)  # the driver may keep compiling on a worker thread after Create returns
if hr < 0:
    print("FAILED hr=0x%08x" % (hr & 0xFFFFFFFF))
    sys.exit(3)
print("OK hr=0x%08x" % (hr & 0xFFFFFFFF))
