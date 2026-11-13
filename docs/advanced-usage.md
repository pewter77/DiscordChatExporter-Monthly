# Advanced Usage

## Dry Run Testing

To test without making actual backups:

1. Edit [discord-backup.py:9](../discord-backup.py#L9): Set `DRY_RUN = True`
2. Rebuild container: `docker-compose up --build -d`
3. Check logs to verify behavior
4. Set back to `False` for real backups

## Multiple Tokens

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
