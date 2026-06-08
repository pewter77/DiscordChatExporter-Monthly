FROM tyrrrz/discordchatexporter:2.47

# Install Python and cron daemon
RUN apk add --no-cache python3 dcron tzdata

# Ensure DCE binary is executable
RUN chmod +x /opt/app/DiscordChatExporter.Cli

# Copy application files
COPY discord-backup.py /app/discord-backup.py
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create directories
RUN mkdir -p /app/exports /app/config /var/log/cron && \
    touch /var/log/cron/cron.log

# Environment defaults
ENV CRON_SCHEDULE="13 0 * * *" \
    PUID=1000 \
    PGID=1000 \
    TZ=UTC

# Set working directory
WORKDIR /app

# Volumes for persistence
VOLUME ["/app/config", "/app/exports"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]
