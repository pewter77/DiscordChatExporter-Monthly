# Troubleshooting

## Container Exits Immediately

Check logs for errors:
```bash
docker-compose logs
```

Common causes:
- `config/config.json` not found or invalid
- Invalid cron schedule syntax

## Permission Denied on Exports

The container creates files with PUID/PGID ownership. Ensure these match your host user:

```bash
# Check your IDs
id -u  # Get UID
id -g  # Get GID

# Update docker-compose.yml with these values
```

## Backups Not Running

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

## Discord API Rate Limiting

If you're hitting rate limits:
- Increase `throttleHours` in config (24 hours recommended)
- Reduce cron frequency (once per day is usually sufficient)
- The script already skips months within throttle window

## Token Errors

Discord tokens can expire or become invalid:
- User tokens: May need to re-authenticate
- Bot tokens: Check Discord Developer Portal
