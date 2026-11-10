"""Upload service contact updates. Password via IWT_PASS_FILE."""

import os
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[2]
password = Path(os.environ["IWT_PASS_FILE"]).read_text(encoding="utf-8").strip()
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    "72.56.85.214",
    username="root",
    password=password,
    timeout=30,
    allow_agent=False,
    look_for_keys=False,
)
sftp = ssh.open_sftp()
files = [
    (
        ROOT / "knowledge/services.json",
        "/opt/iwt-ai-sales-platform/knowledge/services.json",
    ),
    (
        ROOT / "knowledge/faq_phrases.json",
        "/opt/iwt-ai-sales-platform/knowledge/faq_phrases.json",
    ),
    (
        ROOT / "backend/app/ai_core/prompts.py",
        "/opt/iwt-ai-sales-platform/backend/app/ai_core/prompts.py",
    ),
    (
        ROOT / "backend/app/ai_core/core.py",
        "/opt/iwt-ai-sales-platform/backend/app/ai_core/core.py",
    ),
]
for local, remote in files:
    sftp.put(str(local), remote)
    print("uploaded", remote)
sftp.close()
cmd = "cd /opt/iwt-ai-sales-platform && docker compose -f docker-compose.prod.yml up -d --build api"
_, stdout, stderr = ssh.exec_command(cmd, timeout=420)
print(stdout.read().decode("utf-8", "replace")[-2000:])
err = stderr.read().decode("utf-8", "replace")
if err.strip():
    print(err[-1500:])
ssh.close()
print("deployed")
