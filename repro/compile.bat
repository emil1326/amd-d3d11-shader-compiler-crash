@echo off
rem fxc from the Windows SDK 10.0.26100.0, default optimisation (/O1), no extra flags.
set FXC="C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\fxc.exe"
%FXC% /nologo /T ps_5_0 /E main /Fo repro.cso /Fc repro.asm repro.hlsl
%FXC% /nologo /T ps_5_0 /E main /Fo repro_fixed_init.cso /Fc repro_fixed_init.asm repro_fixed_init.hlsl
%FXC% /nologo /T ps_5_0 /E main /Fo repro_fixed_break.cso /Fc repro_fixed_break.asm repro_fixed_break.hlsl
