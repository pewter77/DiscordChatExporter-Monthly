# Operations

## Manual Operations

### Run Backup Immediately

```bash
docker-compose exec discord-backup python3 discord-backup.py
```

### View Cron Logs

```bash
docker-compose exec discord-backup tail -f /var/log/cron/cron.log
```

### Shell Access

```bash
docker-compose exec discord-backup sh
```

### Stop Container

```bash
docker-compose down
```

### Restart Container

```bash
docker-compose restart
```

## How It Works

### Backup Strategy

1. **Monthly Chunks**: Backups are organized by month (YYYY-MM format)
2. **Incremental**: Only backs up months that haven't been completed yet
3. **Metadata Tracking**: `exports/metadata.json` tracks completed months
4. **Throttling**: Won't re-backup if last attempt was within `throttleHours`

### Container Behavior

1. **On Startup**: Runs backup immediately
2. **Scheduled**: Cron triggers backups based on `CRON_SCHEDULE`
3. **Keeps Running**: Container stays alive via cron daemon
4. **Logging**: All output visible via `docker logs`

### Example Directory Structure

```
exports/
├── metadata.json                    # Tracks completed backups
├── MyServerName/
│   ├── _media/                      # Deduplicated media files
│   ├── 2020/
│   │   ├── 01/                     # January 2020
│   │   │   ├── channel1.json
│   │   │   └── channel2.json
│   │   └── 02/                     # February 2020
│   └── 2021/
│       └── 01/
└── DirectMessages/
    ├── _media/
    └── 2021/
        └── 01/
```
