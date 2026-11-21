# Local CPU environment

### env: qah-oommf@3197af42
how: project .venv + NIST OOMMF Windows binaries + Git Tcl 8.6.18
tier: cpus=8, ram=22.88GiB, gpus=0
validated: 2026-11-13 tier 1/2 passed; agent-follows-doc PASS (fresh agent, exact documented invocation, exit 0)
doc: simulations/shape_comparison/ENVIRONMENT.md
invocation: ./.venv/Scripts/python.exe simulations/shape_comparison/validate_environment.py
gotcha: OOMMF refuses elevated tokens; runtime.py removes admin SID and privileges. Child object default DACL must grant current user or process initialization fails.
