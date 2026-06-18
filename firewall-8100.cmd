@echo off
rem Allow inbound TCP 8100 (Live Telemetry sharing) through Windows Firewall.
rem Run on the DRIVER/HOST PC. Requests UAC elevation.
powershell -NoProfile -Command "Start-Process netsh -Verb RunAs -ArgumentList 'advfirewall firewall add rule name=\"MoTeC-Live 8100\" dir=in action=allow protocol=TCP localport=8100'"
echo Firewall rule for TCP 8100 requested (confirm the UAC prompt).
