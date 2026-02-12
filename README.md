# Discord Backup Docker

[![Docker Image CI](https://github.com/USERNAME/discord-backup-docker/actions/workflows/docker-build-publish.yml/badge.svg)](https://github.com/USERNAME/discord-backup-docker/actions/workflows/docker-build-publish.yml)
[![GitHub release](https://img.shields.io/github/v/release/USERNAME/discord-backup-docker)](https://github.com/USERNAME/discord-backup-docker/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A self-contained Docker solution for automatically backing up Discord servers and direct messages using [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter). Backups run on startup and on a configurable cron schedule.

## Features

- 🐳 **Single Docker Image** - Everything bundled: DiscordChatExporter CLI + Python backup logic
- ⏰ **Scheduled Backups** - Configurable cron schedule (default: daily at 00:13)
- 📅 **Monthly Archival** - Organizes backups by year and month
- 🔄 **Incremental Backups** - Only backs up months that haven't been backed up yet
- 🎯 **Throttling** - Per-guild throttling to prevent too-frequent API calls
- 📦 **Media Support** - Downloads and deduplicates media files
- 🔒 **Permission Handling** - Proper file ownership via PUID/PGID
- 📊 **Progress Tracking** - Metadata tracking for completed backups

## Installation

### Option 1: Using Pre-built Image (Recommended)

Pull the latest image directly from GitHub Container Registry:

```bash
docker pull ghcr.io/USERNAME/discord-backup-docker:latest
```

**Available tags:**
- `latest` - Latest stable release
- `0.0.1`, `0.0`, `0` - Specific semantic version tags
- `v0.0.1` - Version with v prefix

### Option 2: Build from Source

Clone and build locally:

```bash
git clone https://github.com/USERNAME/discord-backup-docker.git
cd discord-backup-docker
docker-compose up --build -d
```

## Quick Start

### 1. Setup Configuration

```bash
# Create config directory
mkdir -p config
cp config.example.json config/config.json

# Edit config.json with your Discord tokens and server IDs
```

Edit `config/config.json` with your Discord tokens and server information:

```json
{
    "tokens": [
        {
            "name": "MyBotToken",
            "value": "YOUR_DISCORD_TOKEN_HERE"
        }
    ],
    "guilds": [
        {
            "tokenName": "MyBotToken",
            "guildId": "123456789012345678",
            "guildName": "MyServerName",
            "startDate": "2020-01",
            "enabled": true,
            "throttleHours": 23.5
        }
    ]
}
```

**Configuration Fields:**

- `tokens`: Array of Discord tokens
  - `name`: A friendly name for the token
  - `value`: Your Discord token (user or bot token)

- `guilds`: Array of servers/DMs to backup
  - `tokenName`: Reference to a token from the `tokens` array
  - `guildId`: Discord server ID (or `"@me"` for direct messages)
  - `guildName`: Folder name for backups (no special characters)
  - `startDate`: Start backing up from this month (format: `YYYY-MM`)
  - `enabled`: Whether to backup this guild (optional, default: `true`)
  - `throttleHours`: Minimum hours between backup attempts (prevents API spam)

### 2. Run Container

**Using pre-built image:**

```bash
docker run -d \
  --name discord-backup \
  --restart unless-stopped \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/exports:/app/exports \
  -e TZ=America/New_York \
  -e CRON_SCHEDULE="13 0 * * *" \
  -e PUID=1000 \
  -e PGID=1000 \
  ghcr.io/USERNAME/discord-backup-docker:latest
```

**Or with docker-compose:**

Create `docker-compose.yml`:

```yaml
---
services:
  discord-backup:
    image: ghcr.io/USERNAME/discord-backup-docker:latest
    container_name: discord-backup
    restart: unless-stopped
    environment:
      CRON_SCHEDULE: "13 0 * * *"
      PUID: 1000
      PGID: 1000
      TZ: "America/New_York"
    volumes:
      - ./config:/app/config:ro
      - ./exports:/app/exports
```

Then run:

```bash
docker-compose up -d

# View logs
docker-compose logs -f
```

**To build from source instead, change the image line to:**

```yaml
    build: .  # Instead of: image: ghcr.io/...
```

Backups will be saved to `./exports/{guildName}/{YYYY}/{MM}/`

## Configuration

### Environment Variables

Configure these in [docker-compose.yml](docker-compose.yml):

| Variable | Default | Description |
|----------|---------|-------------|
| `CRON_SCHEDULE` | `13 0 * * *` | Cron expression for backup schedule |
| `PUID` | `1000` | User ID for file ownership |
| `PGID` | `1000` | Group ID for file ownership |
| `TZ` | `UTC` | Timezone for scheduling |

### Cron Schedule Examples

The `CRON_SCHEDULE` uses standard cron syntax: `minute hour day month weekday`

```yaml
CRON_SCHEDULE: "13 0 * * *"     # Daily at 00:13 / 12:13 AM (default)
CRON_SCHEDULE: "0 0 * * *"      # Daily at midnight
CRON_SCHEDULE: "0 2 * * *"      # Daily at 2 AM
CRON_SCHEDULE: "0 */6 * * *"    # Every 6 hours
CRON_SCHEDULE: "0 */12 * * *"   # Every 12 hours
CRON_SCHEDULE: "0 0 * * SUN"    # Weekly on Sunday at midnight
CRON_SCHEDULE: "*/30 * * * *"   # Every 30 minutes (not recommended)
```

### File Permissions

The container creates files with the specified PUID/PGID ownership. To find your user IDs:

```bash
id -u  # Your User ID (UID)
id -g  # Your Group ID (GID)
```

Update these values in [docker-compose.yml](docker-compose.yml) to match your host user for proper file permissions.

### Timezone

Set `TZ` to your local timezone for accurate scheduling. Examples:
- `America/New_York`
- `Europe/London`
- `Asia/Tokyo`
- `UTC` (default)

[Full list of timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

## Volume Mounts

The container uses two volume mounts:

1. **Config Directory** (`./config:/app/config:ro`)
   - Mount as **read-only** (`:ro`) for security
   - Contains your `config.json`

2. **Exports Directory** (`./exports:/app/exports`)
   - Stores all backups and metadata
   - Structure: `exports/{guildName}/{YYYY}/{MM}/`
   - Media files: `exports/{guildName}/_media/` (deduplicated)

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

## Troubleshooting

### Container Exits Immediately

Check logs for errors:
```bash
docker-compose logs
```

Common causes:
- `config/config.json` not found or invalid
- Invalid cron schedule syntax

### Permission Denied on Exports

The container creates files with PUID/PGID ownership. Ensure these match your host user:

```bash
# Check your IDs
id -u  # Get UID
id -g  # Get GID

# Update docker-compose.yml with these values
```

### Backups Not Running

1. Check cron schedule is valid:
   ```bash
   docker-compose exec discord-backup cat /etc/crontabs/root
   ```

2. Check cron logs:
   ```bash
   docker-compose exec discord-backup tail -f /var/log/cron/cron.log
   ```

3. Verify container is running:
   ```bash
   docker-compose ps
   ```

### Discord API Rate Limiting

If you're hitting rate limits:
- Increase `throttleHours` in config (24 hours recommended)
- Reduce cron frequency (once per day is usually sufficient)
- The script already skips months within throttle window

### Token Errors

Discord tokens can expire or become invalid:
- User tokens: May need to re-authenticate
- Bot tokens: Check Discord Developer Portal

Get your token: [Discord Token Guide](https://github.com/Tyrrrz/DiscordChatExporter/wiki/Obtaining-Token-and-Channel-IDs)

## Security Considerations

1. **Protect Your Tokens**
   - Never commit `config.json` to git (already in `.gitignore`)
   - Set proper file permissions: `chmod 600 config/config.json`
   - Config is mounted read-only in the container

2. **Container Security**
   - Runs as non-root user (via PUID/PGID)
   - No ports exposed
   - Minimal Alpine Linux base image

## Migration from Standalone Script

If you were using the Python script directly:

1. **Preserve Existing Backups**: Just mount your existing `exports/` directory
2. **Config Structure**: No changes needed to `config.json`
3. **Metadata**: Your `exports/metadata.json` will be preserved
4. **Old Files**: Can delete the `dce/` folder (no longer needed)

## Advanced Usage

### Dry Run Testing

To test without making actual backups:

1. Edit [discord-backup.py:9](discord-backup.py#L9): Set `DRY_RUN = True`
2. Rebuild container: `docker-compose up --build -d`
3. Check logs to verify behavior
4. Set back to `False` for real backups

### Resource Limits

Uncomment the `deploy` section in [docker-compose.yml](docker-compose.yml) to limit resources:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

### Multiple Tokens

You can define multiple tokens for different servers:

```json
{
    "tokens": [
        {
            "name": "PersonalAccount",
            "value": "token1..."
        },
        {
            "name": "BotAccount",
            "value": "token2..."
        }
    ],
    "guilds": [
        {
            "tokenName": "PersonalAccount",
            "guildId": "123...",
            ...
        },
        {
            "tokenName": "BotAccount",
            "guildId": "456...",
            ...
        }
    ]
}
```

## Credits

- [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) by Tyrrrz - The core export engine
- [DiscordChatExporter-incrementalBackup](https://github.com/slatinsky/DiscordChatExporter-incrementalBackup) by slatinsky - Special thanks for inspiration and incremental backup concepts
- Python backup script with monthly archival and metadata tracking
- Docker containerization for easy deployment

## License

This project is provided as-is for personal backup purposes. Please respect Discord's Terms of Service when using this tool.
