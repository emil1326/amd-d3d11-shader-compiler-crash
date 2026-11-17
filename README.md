# AMD D3D11 driver: shader compiler crash on a valid ps_5_0 blob

A 13-line pixel shader, compiled by the stock Windows SDK `fxc`, makes the AMD user-mode D3D11 driver (`amdxx64.dll`) die with an access violation (0xC0000005) when you hand it to `ID3D11Device::CreatePixelShader`. The trigger is a dynamically indexed local array that a loop reads at elements nothing has stored to yet. The reads are masked in the HLSL, so the shader is well defined, but `fxc` compiles the mask into a plain `and`, so the bytecode reads the array unconditionally. Writing zeros to the array first, or adding a `break` before the read, makes the crash go away. Reproduced every run on a Radeon RX 9070 XT.

## The shader

```hlsl
cbuffer C : register(b0) { int4 g[9]; }
float4 main(float4 pos : SV_Position) : SV_Target
{
    int rg[16];
    int nr = 0;
    [loop] for (int i = 0; i < 9; i++)
    {
        bool dup = false;
        [loop] for (int j = 0; j < 16; j++) { if (j < nr && rg[j] == g[i].x) dup = true; }
        if (!dup) { rg[nr] = g[i].x; nr++; }
    }
    return float4((float)nr, 0, 0, 1);
}
```

It collects the distinct values of `g[i].x` into `rg`. `nr` is how many are stored so far, and the inner loop only compares against the first `nr`.

## Symptom

`CreatePixelShader` on the compiled blob (`repro/repro.cso`) kills the process with 0xC0000005, a read at address 0x58, at `amdxx64.dll+0x6cbebb`. The minidump shows a very deep recursion inside the driver's shader compiler, so it looks like unbounded recursion running out of stack. It happens during the Create call or on the driver's compile worker thread right after it returns. The same blob is created fine by the WARP reference rasterizer.

We found it because Unity (2022.3, D3D11) creates every shader it loads, so the editor crashed on every start.

## Environment

| | |
|---|---|
| GPU | AMD Radeon RX 9070 XT |
| Driver | 32.0.32015.7029 (dated 2026-10-17) |
| OS | Windows 11 Home, build 26300 |
| Shader compiler | fxc 10.0.26100.8249 (Windows SDK 10.0.26100.0), default /O1, no flags |
| API | D3D11, feature level 11_0, default hardware adapter |

Other GPUs and driver versions are untested. If you can try one, please say so in an issue.

## Steps to reproduce

You need Windows, Python 3 (nothing to install) and a machine whose default D3D11 adapter is the AMD GPU. The compiled blobs are in the repo, so compiling is optional.

1. Optional: `repro\compile.bat` rebuilds the blobs with fxc. The blobs we tested have these SHA-1s (also in `repro/SHA1SUMS.txt`): `repro.cso` e13972fb795ae9e5d3060a1f5073a233be9ec379, `repro_fixed_init.cso` 6fc610ba434854b52373eaa48da9f582430c2f36, `repro_fixed_break.cso` 8aba02a64a4e38474c94cacb173a4f786e23ee34.
2. `python repro\run_all.py` runs the three blobs, each in its own process, and prints CRASH or OK.
3. Or by hand, one blob per process (a crash kills the process): `python repro\repro_create.py repro\repro.cso ps`

## Expected vs actual

Expected: all three blobs print `OK hr=0x00000000`. They are valid ps_5_0 bytecode, so the driver should compile them or at worst return an error HRESULT.

Actual: `repro.cso` kills the process (exit code 0xC0000005, same offset every time). The two controls print `OK`.

## Why this is valid input

The inner loop reads `rg[j]` for every `j` below 16, but the `j < nr` test masks the comparison, so a value is only used when it was already stored. The result never depends on an element that was not written. HLSL does not short-circuit into a branch here: `fxc` turns `j < nr && rg[j] == g[i].x` into an `and` of two compares, so the bytecode (`repro/repro.asm`, 20 instructions) contains an unconditional `mov r1.y, x0[r0.w + 0].x` inside the inner loop, and the only store into `x0` (`mov x0[r0.x + 0].x, ...`) comes after it. On the first trip of the outer loop no store reaches any element, on any path. Reading uninitialised temps is legal in DXBC, and the value is simply masked afterwards. A compiler can treat those elements as undefined, but it should not crash.

## Workarounds

Both are in this repo as controls, and neither changes the result:

- `repro/repro_fixed_init.hlsl`: write every element (here zero) before the loops, so each read has a store reaching it.
- `repro/repro_fixed_break.hlsl`: `if (j >= nr) break;` before the read, so the read is control-dependent on the fill count.

Unrolling the inner loop does not help (the reads are still unconditional), and neither does removing other parts of the surrounding code, which is how we know the read of unwritten elements is the whole trigger.

## How it was found

Emil was building a big VRChat world and merged a villages update. Unity then crashed on every launch, and it was not managed code throwing: the minidump pointed into `amdxx64.dll`. To find which shader, we compiled every program of the changed shaders offline with fxc and handed each blob straight to the driver with a tiny `CreatePixelShader` caller (`repro_create.py`, one process per blob). One big fragment shader (about 13,900 instruction slots) crashed it. Then it was bisecting: cut the shader down to the one function that mattered (538 slots), then to one loop, then found that filling the array with zeros first fixed it, and that a `break` before the read fixed it too. After that the 13 lines above were easy.

```mermaid
flowchart LR
    A[Unity crashes on start] --> B[minidump: amdxx64.dll 0xC0000005]
    B --> C[compile shaders offline with fxc]
    C --> D[CreatePixelShader per blob, one process each]
    D --> E[one fragment crashes]
    E --> F[bisect: array read before any store]
    F --> G[13-line repro]
```

## Files

| file | what it is |
|---|---|
| `repro/repro.hlsl` / `.cso` / `.asm` | the shader, the blob that crashes, its disassembly |
| `repro/repro_fixed_init.*` | control: array zeroed first, OK |
| `repro/repro_fixed_break.*` | control: `break` before the read, OK |
| `repro/repro_create.py` | creates a D3D11 device and calls `CreatePixelShader` on one blob (Python + ctypes) |
| `repro/run_all.py` | runs the three blobs in separate processes, prints CRASH / OK |
| `repro/compile.bat` | the exact fxc command lines |

## License

It's MIT with Commons Clause and a little "don't be awful" condition on top, so it's "source-available" rather than official open source. In plain words: use it for anything, paid work included, change it and share it, but don't sell the thing itself, and don't use it to steal other people's art, harass people, or do anything illegal. Full text in `LICENSE`. (Honestly, it's 13 lines of HLSL and a ctypes script, so I mostly just want AMD to fix their driver xD)
