"""One-off scrub of employer/internal identifiers from AI-Evaluation legacy suite."""
import os, sys

REPLACEMENTS = [
    ("REDACTED-CREDENTIAL", "ENV_DB_PASSWORD"),
    ("baseline11x_HealthOS", "APP_SERVER_11X"),
    ("MUII_HEALTHOS", "MUII_DB"),
    ("FHIR_HealthOS", "FHIR_DB"),
    ("Release01", "APP_SERVER_10G"),
    ("HealthOSinc.sharepoint.com", "example.sharepoint.com"),
    ("devops.HealthOS.com", "devops.example.com"),
    ("fhirendpoint.HealthOS.net", "fhir.example.net"),
    ("fhir.HealthOS.com", "fhir.example.com"),
    ("HealthOS.com", "example.com"),
    ("Hassan Ali Laghari", "analyst"),
    ("HEALTHOS", "HEALTHOS"),
    ("HealthOS", "HealthOS"),
    ("HealthOS", "HealthOS"),
    ("HealthOS", "healthos"),
]
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv"}
TEXT_EXT = {".py", ".md", ".json", ".ts", ".js", ".bat", ".yaml", ".yml", ".txt", ".toml", ""}

root = sys.argv[1] if len(sys.argv) > 1 else "legacy-HealthOS-ba-qa"
changed = {}
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
            continue
        fp = os.path.join(dirpath, fn)
        try:
            src = open(fp, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        out, hits = src, 0
        for a, b in REPLACEMENTS:
            n = out.count(a)
            if n:
                out, hits = out.replace(a, b), hits + n
        if hits:
            open(fp, "w", encoding="utf-8", newline="").write(out)
            changed[fp] = hits
total = sum(changed.values())
for p, n in sorted(changed.items()):
    print(f"  {n:4d}  {p}")
print(f"-> {len(changed)} files, {total} replacements")
