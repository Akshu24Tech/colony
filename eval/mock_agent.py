#!/usr/bin/env python3
"""A scripted stand-in for a real agent. It follows whatever notes it is given, including wrong ones,
and otherwise finds the right file itself. It exists to test the harness plumbing ONLY.
Its pass/fail pattern is built in, so it is not evidence about real agents or about Colony.
"""
import os
import subprocess
import sys
from pathlib import Path

prompt = sys.argv[1] if len(sys.argv) > 1 else ""
task = os.environ.get("EVAL_TASK", "")
guidance = ""
if "AGENTS.md" in prompt and Path("AGENTS.md").exists():
    guidance = Path("AGENTS.md").read_text()
if "colony brief" in prompt:
    out = subprocess.run(["colony", "brief"], capture_output=True, text=True).stdout
    guidance = "\n".join(l for l in out.splitlines() if "DO NOT TRUST" not in l)

if task == "timeout-unit":
    key = "TIMEOUT_MS = 5000" if "TIMEOUT_MS" in guidance else "TIMEOUT = 5"
    Path("config.py").write_text(key + "\nRETRIES = 3\n")
elif task == "schema-migration":
    if "migrations" in guidance:
        Path("migrations/003_add_email.sql").write_text("ALTER TABLE users ADD COLUMN email TEXT;\n")
    else:
        Path("schema.sql").write_text(Path("schema.sql").read_text().replace("name TEXT)", "name TEXT, email TEXT)"))
elif task == "base-url":
    if "config.yml" in guidance:
        Path("config.yml").write_text("base_url: https://api.example.org\n")
    else:
        Path("settings.toml").write_text('base_url = "https://api.example.org"\n')
elif task == "checkout-flag":
    if "flags.json" in guidance:
        Path("flags.json").write_text('{"new_checkout": true}\n')
    else:
        Path("flags.yaml").write_text("new_checkout: true\nbeta_search: false\n")
print("mock agent done")
