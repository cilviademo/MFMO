# EOM-01 Expected Package — DEFERRED FOR THE MANUAL PILOT

The generator flow is not built by hand in this kit. Its output for 2026-08 and 2026-09 is generated OFFLINE by the same engine the test suite runs and shipped as `CSV-IMPORT/expected-items-2026-08-09.csv` (exactly 737 rows). Load that CSV instead of building the flow. When the solution deployment happens later, the imported EOM-01 takes over and its idempotency key means it will NOT duplicate these 737 rows.
