// control: repro.hlsl with every array element written before the loops. Does NOT crash.
cbuffer C : register(b0) { int4 g[9]; }
float4 main(float4 pos : SV_Position) : SV_Target
{
    int rg[16];
    [unroll] for (int z = 0; z < 16; z++) rg[z] = 0;
    int nr = 0;
    [loop] for (int i = 0; i < 9; i++)
    {
        bool dup = false;
        [loop] for (int j = 0; j < 16; j++) { if (j < nr && rg[j] == g[i].x) dup = true; }
        if (!dup) { rg[nr] = g[i].x; nr++; }
    }
    return float4((float)nr, 0, 0, 1);
}
