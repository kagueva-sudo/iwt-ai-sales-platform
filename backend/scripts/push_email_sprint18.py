"""Upload Sprint 18 Email files and rebuild api + email-worker. Password via IWT_PASS_FILE."""

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

# Ensure remote dirs exist
for remote_dir in (
    "/opt/iwt-ai-sales-platform/backend/app/integrations/email",
    "/opt/iwt-ai-sales-platform/backend/app/workers",
    "/opt/iwt-ai-sales-platform/backend/app/static/inbox",
):
    try:
        sftp.stat(remote_dir)
    except OSError:
        # mkdir -p via ssh
        ssh.exec_command(f"mkdir -p {remote_dir}")

files = [
    "backend/app/core/config.py",
    "backend/app/core/constants.py",
    "backend/app/domain/messages.py",
    "backend/app/domain/manager_queue.py",
    "backend/app/db/models.py",
    "backend/app/db/init_db.py",
    "backend/app/channel_adapters/email_adapter.py",
    "backend/app/integrations/email/__init__.py",
    "backend/app/integrations/email/config.py",
    "backend/app/integrations/email/exceptions.py",
    "backend/app/integrations/email/schemas.py",
    "backend/app/integrations/email/parsing.py",
    "backend/app/integrations/email/imap_client.py",
    "backend/app/integrations/email/smtp_client.py",
    "backend/app/repositories/email_processed.py",
    "backend/app/repositories/manager_queue.py",
    "backend/app/services/email_inbox_policy.py",
    "backend/app/services/email_poller.py",
    "backend/app/services/decision_router.py",
    "backend/app/services/handoff_manager.py",
    "backend/app/services/message_pipeline.py",
    "backend/app/services/message_service.py",
    "backend/app/services/manager_queue_service.py",
    "backend/app/services/composition.py",
    "backend/app/schemas/manager_queue.py",
    "backend/app/api/manager_queue_mappers.py",
    "backend/app/workers/__init__.py",
    "backend/app/workers/email_worker.py",
    "backend/app/static/inbox/index.html",
    "backend/app/static/inbox/inbox.js",
    "docker-compose.prod.yml",
    "EMAIL_SETUP.md",
    "PROJECT_ROADMAP.md",
    "PROJECT_MEMORY.md",
    "README.md",
]
for rel in files:
    local = ROOT / rel
    remote = f"/opt/iwt-ai-sales-platform/{rel.replace(chr(92), '/')}"
    sftp.put(str(local), remote)
    print("uploaded", remote)
sftp.close()

# Ensure email columns + rebuild
cmds = [
    "cd /opt/iwt-ai-sales-platform && docker compose -f docker-compose.prod.yml up -d --build api email-worker",
]
for cmd in cmds:
    print("RUN", cmd)
    _, stdout, stderr = ssh.exec_command(cmd, timeout=480)
    print(stdout.read().decode("utf-8", "replace")[-3000:])
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print(err[-2000:])

_, stdout, stderr = ssh.exec_command(
    "docker ps --format '{{.Names}} {{.Status}}' | grep -E 'api|email'",
    timeout=30,
)
print(stdout.read().decode("utf-8", "replace"))
ssh.close()
print("deployed")
