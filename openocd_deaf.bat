@echo off
echo --- Deaf Wrapper: Ignoring VS Code flags and running manual command ---
"C:\Users\shaher\Downloads\Programs\OpenOCD-20251211-0.12.0\bin\openocd.exe" -f interface/stlink.cfg -f target/stm32f1x.cfg -c "gdb port 50000" -c "tcl port 50001" -c "telnet port 50002"
