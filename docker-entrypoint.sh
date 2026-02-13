#!/bin/sh
set -e

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Discord Backup Container"

# Handle PUID/PGID for file permissions
if [ "$PUID" != "1000" ] || [ "$PGID" != "1000" ]; then
    log "Adjusting user permissions to PUID=$PUID, PGID=$PGID"

    # Create a new user/group with specified IDs if needed
    if ! getent group "$PGID" > /dev/null 2>&1; then
        addgroup -g "$PGID" appgroup
    fi

    if ! getent passwd "$PUID" > /dev/null 2>&1; then
        adduser -D -u "$PUID" -G "$(getent group "$PGID" | cut -d: -f1)" appuser
    fi

    USER_NAME=$(getent passwd "$PUID" | cut -d: -f1)
else
    USER_NAME="dce"
fi

# Set ownership of exports directory (always run to fix root-owned directory)
log "Setting ownership of /app/exports to $PUID:$PGID"
if chown -R "$PUID:$PGID" /app/exports; then
    log "Successfully set directory ownership"
else
    log "ERROR: Failed to set directory ownership"
    exit 1
fi

# Validate config file exists
if [ ! -f "/app/config/config.json" ]; then
    log "ERROR: /app/config/config.json not found!"
    log "Please mount your config directory with config.json inside"
    log "Example: docker run -v /path/to/config:/app/config:ro ..."
    exit 1
fi

# Set timezone
if [ -n "$TZ" ]; then
    log "Setting timezone to $TZ"
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
    echo "$TZ" > /etc/timezone
fi

# Set up cron job
log "Setting up cron schedule: $CRON_SCHEDULE"
{
    echo "CRON_TZ=$TZ"
    echo "$CRON_SCHEDULE cd /app && python3 discord-backup.py >> /var/log/cron/cron.log 2>&1"
} > /etc/crontabs/root

# Run backup immediately on startup
log "Running initial backup..."
cd /app
if su -s /bin/sh "$USER_NAME" -c "python3 discord-backup.py"; then
    log "Initial backup completed successfully"
else
    log "Initial backup encountered errors (see above)"
fi

# Start cron in foreground
log "Starting cron daemon with schedule: $CRON_SCHEDULE"
log "Cron logs will be written to /var/log/cron/cron.log"

# Start crond in foreground and tail the log
crond -f -l 2 &
CROND_PID=$!

# Tail the cron log in foreground (keeps container running and shows output)
tail -f /var/log/cron/cron.log &
TAIL_PID=$!

# Handle signals for graceful shutdown
trap "log 'Stopping...'; kill $CROND_PID $TAIL_PID 2>/dev/null; exit 0" SIGTERM SIGINT

# Wait for processes
wait $CROND_PID $TAIL_PID
