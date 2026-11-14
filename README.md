# Discord Backup Docker

[![Docker Image CI](https://github.com/pewter77/DiscordChatExporter-Monthly/actions/workflows/docker-build-publish.yml/badge.svg)](https://github.com/pewter77/DiscordChatExporter-Monthly/actions/workflows/docker-build-publish.yml)
[![GitHub release](https://img.shields.io/github/v/release/pewter77/DiscordChatExporter-Monthly)](https://github.com/pewter77/DiscordChatExporter-Monthly/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A self-contained Docker solution for automatically backing up Discord servers and direct messages using [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter). Backups run on startup and on a configurable cron schedule.

> **Important**: This tool creates **full month backups** (organized by YYYY-MM). The cron schedule controls how often the script checks for new months to backup, not how often individual messages are backed up. The backup process runs both on container startup and according to the configured cron schedule.

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
docker pull ghcr.io/pewter77/discordchatexporter-monthly:latest
```

**Available tags:**
- `latest` - Latest stable release
- `0.0.3`, `0.0`, `0` - Semantic version tags (see [releases](https://github.com/pewter77/DiscordChatExporter-Monthly/releases) for all versions)

### Option 2: Build from Source

Clone and build locally:

```bash
git clone https://github.com/pewter77/DiscordChatExporter-Monthly.git
cd DiscordChatExporter-Monthly
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
  ghcr.io/pewter77/discordchatexporter-monthly:latest
```

**Or with docker-compose:**

Create `docker-compose.yml`:

```yaml
---
services:
  discord-backup:
    image: ghcr.io/pewter77/discordchatexporter-monthly:latest
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

## Documentation

| Doc | Covers |
|---|---|
| [Configuration](docs/configuration.md) | Environment variables, health check pings, cron schedule, permissions, timezone, volume mounts |
| [Operations](docs/operations.md) | Manual backups, logs, shell access, how backups and the container work, export layout |
| [Troubleshooting](docs/troubleshooting.md) | Container exits, permission errors, missed backups, rate limits, token errors |
| [Advanced Usage](docs/advanced-usage.md) | Dry runs, multiple tokens |

## Security Considerations

1. **Protect Your Tokens**
   - Never commit `config.json` to git (already in `.gitignore`)
   - Set proper file permissions: `chmod 600 config/config.json`
   - Config is mounted read-only in the container

2. **Container Security**
   - Runs as non-root user (via PUID/PGID)
   - No ports exposed
   - Minimal Alpine Linux base image

## Credits

- [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) by Tyrrrz - The core export engine
- [DiscordChatExporter-incrementalBackup](https://github.com/slatinsky/DiscordChatExporter-incrementalBackup) by slatinsky - Special thanks for inspiration and incremental backup concepts
- Python backup script with monthly archival and metadata tracking
- Docker containerization for easy deployment

## Disclaimer

**Personal Project**: This is a personal project created and shared to help others with Discord backup automation.

**GenAI Assistance**: This project was developed with the assistance of generative AI tools.

**Limited Support**: This project is provided as-is with limited support. While issues and pull requests are welcome, response times may vary.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

This project is provided as-is for personal backup purposes. Please respect Discord's Terms of Service when using this tool.
