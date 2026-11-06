"""Upload WhatsApp webhook fix to the Timeweb API host. Password via IWT_PASS_FILE."""

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
        ROOT / "backend/app/api/whatsapp_webhook.py",
        "/opt/iwt-ai-sales-platform/backend/app/api/whatsapp_webhook.py",
    ),
    (
        ROOT / "backend/app/db/models.py",
        "/opt/iwt-ai-sales-platform/backend/app/db/models.py",
    ),
    (
        ROOT / "backend/app/channel_adapters/whatsapp_adapter.py",
        "/opt/iwt-ai-sales-platform/backend/app/channel_adapters/whatsapp_adapter.py",
    ),
]
for local, remote in files:
    sftp.put(str(local), remote)
    print("uploaded", remote)
sftp.close()
_, stdout, stderr = ssh.exec_command(
    "cd /opt/iwt-ai-sales-platform && docker compose -f docker-compose.prod.yml exec -T db "
    "sh -c 'psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -c \""
    "ALTER TABLE messages ALTER COLUMN id TYPE varchar(255); "
    "ALTER TABLE ai_logs ALTER COLUMN message_id TYPE varchar(255); "
    "ALTER TABLE error_logs ALTER COLUMN message_id TYPE varchar(255); "
    "ALTER TABLE conversation_messages ALTER COLUMN message_id TYPE varchar(255); "
    "ALTER TABLE processing_logs ALTER COLUMN request_id TYPE varchar(255); "
    "ALTER TABLE manager_queue ALTER COLUMN request_id TYPE varchar(255);"
    "\"'",
    timeout=60,
)
print(stdout.read().decode("utf-8", "replace")[-2000:])
print(stderr.read().decode("utf-8", "replace")[-1000:])
cmd = "cd /opt/iwt-ai-sales-platform && docker compose -f docker-compose.prod.yml up -d --build api"
_, stdout, stderr = ssh.exec_command(cmd, timeout=300)
print(stdout.read().decode("utf-8", "replace")[-2500:])
err = stderr.read().decode("utf-8", "replace")
if err.strip():
    print(err[-1500:])
ssh.close()
print("deployed")
