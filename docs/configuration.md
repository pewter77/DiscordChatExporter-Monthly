# Configuration

## Environment Variables

Configure these in [docker-compose.yml](../docker-compose.yml):

| Variable | Default | Description |
|----------|---------|-------------|
| `CRON_SCHEDULE` | `13 0 * * *` | Cron expression for backup schedule |
| `PUID` | `1000` | User ID for file ownership |
| `PGID` | `1000` | Group ID for file ownership |
| `TZ` | `UTC` | Timezone for scheduling |
| `HEALTHCHECK_URL` | _(unset)_ | Optional [Healthchecks](https://healthchecks.io) ping URL (hosted or self-hosted). See [Health Check Pings](#health-check-pings) |

## Health Check Pings

Set `HEALTHCHECK_URL` to a check's ping URL (e.g. `https://hc-ping.com/<uuid>`) to be alerted when backups stop running or fail. Each run sends:

| Ping | When |
|------|------|
| `<url>/start` | The run begins (Healthchecks uses this to measure duration) |
| `<url>` | Every guild either exported all of its months or had nothing to do, including guilds skipped by `throttleHours` |
| `<url>/fail` | Any month failed to export, the config is invalid, or the script crashed |

The request body carries a short summary (months backed up/failed and duration), which shows up in the Healthchecks event log. Set the check's period to match `CRON_SCHEDULE` so a missed run is also reported. Ping failures are retried and logged, but never stop the backup. The script also exits with code 1 when a month fails, so failures show in the logs as "Initial backup encountered errors".

## Cron Schedule Examples

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

## File Permissions

The container creates files with the specified PUID/PGID ownership. To find your user IDs:

```bash
id -u  # Your User ID (UID)
id -g  # Your Group ID (GID)
```

Update these values in [docker-compose.yml](../docker-compose.yml) to match your host user for proper file permissions.

## Timezone

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
