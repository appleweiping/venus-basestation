# mapping-new Branch Snapshot

This directory is a copy of one branch of the Team 28 repository on TU/e GitLab. I did not write this code.

- Branch represented: mapping-new
- Source HEAD at copy time: bef05588cfd5efbabd049f2b5b6e1f586bfa974a (bef0558)
- Refreshed: 2026-05-29

What the copy leaves out or keeps:

- .git/ metadata was not copied.
- Personal sftp.json files are excluded; examples may remain.
- Module snapshots include top-level setup files plus libpynq application sources.
- Generated Doxygen HTML, library build outputs, Python bytecode caches, object files, and local executables are excluded.
- Vendored third-party Python packages are excluded from the public snapshot; install them with pip when running the scripts.
- MQTT course example scripts must read VENUS_MQTT_PASSWORD from the environment; do not commit course passwords.
