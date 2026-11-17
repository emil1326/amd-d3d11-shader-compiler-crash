"""Hand ONE compiled DXBC blob to the real D3D11 driver and call CreatePixelShader on it.

    python repro_create.py <file.cso> [vs|gs|ps|hs|ds|cs]     (default: ps)

Prints "OK hr=0x..." if the driver took it. If the driver's shader compiler crashes,
the whole process dies (exit code 0xC0000005), so use ONE blob per process.
Windows only. Python 3 + ctypes, nothing to install.
"""
import ctypes, sys, time

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

blob = open(sys.argv[1], "rb").read()
stage = sys.argv[2] if len(sys.argv) > 2 else "ps"
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
print("OK hr=0x%08x" % (hr & 0xFFFFFFFF))
