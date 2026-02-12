from datetime import datetime, timezone
import json
import logging
import os
import re
import subprocess

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# dry run option for development
DRY_RUN = False

class Config:
    def __init__(self, config_path='config.json'):
        try:
            with open(config_path) as f:
                self._config = json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            logger.error(f"Copy config.example.json to {config_path} and fill in the values to get started")
            exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_path}: {e}", exc_info=True)
            logger.error(f"Check for syntax errors (missing commas, quotes, brackets)")
            exit(1)

        self._tokens = {}  # key is token name, value is token value
        for token in self._config['tokens']:
            if 'name' not in token or 'value' not in token:
                logger.error(f'Token must have "name" and "value" fields defined - found fields {token.keys()}')
                exit(1)
            self._tokens[token['name']] = token['value']

        guilds = []
        for guild in self._config['guilds']:
            if 'enabled' in guild and not guild['enabled']:
                continue
            self.validate_guild(guild)
            guild['tokenValue'] = self._tokens[guild['tokenName']]
            if guild['guildId'] == '@me':
                guild['type'] = 'exportdm'
            else:
                guild['type'] = 'exportguild'

            if 'throttleHours' not in guild:
                guild['throttleHours'] = 0

            guilds.append(guild)

        logger.info(f"Configuration loaded: {len(guilds)} enabled guild(s), {len(self._tokens)} token(s)")
        for guild in guilds:
            logger.debug(f"  - {guild['guildName']} ({guild['type']}) starting from {guild['startDate']}")

        self.guilds = guilds


    def validate_guild(self, guild) -> None:
        """
        print helpful error messages if guild config is not valid
        is not validated against the actual discord API, just basic checks
        """
        invalid_path_chars = re.compile(r'[<>:"/\\|?*]')
        discord_snowflake = re.compile(r'^\d{17,19}$')  # 19 digits won't be enough in 2090. But you probably won't be using this script then
        required_fields = ['tokenName', 'guildId', 'guildName', 'startDate']

        for required_field in required_fields:
            if required_field not in guild:
                logger.error(f'Guild must have "{required_field}" field defined - found fields {guild.keys()}')
                exit(1)
            if type(guild[required_field]) != str:
                logger.error(f'Guild field "{required_field}" must be a string - found {type(guild[required_field])}')
                exit(1)
            if guild[required_field] == "":
                logger.error(f'Guild must have "{required_field}" field defined - found empty value')
                exit(1)

        if guild['guildId'] != '@me' and not discord_snowflake.match(guild['guildId']):
            logger.error(f'Guild field "guildId" must be a discord snowflake (must be a string of 17-19 digits or "@me" for DMs) - found {guild["guildId"]}')
            exit(1)

        if invalid_path_chars.search(guild['guildName']):
            logger.error(f'Guild field "guildName" must not contain invalid path characters (must be a non-empty string without any of <>:"/\\|?* - because it is used as a folder name) - found {guild["guildName"]}')
            exit(1)

        # Validate startDate format and validity
        date_format = re.compile(r'^(\d{4})-(\d{2})$')
        if not date_format.match(guild['startDate']):
            logger.error(f'Guild field "startDate" must be in YYYY-MM format - found {guild["startDate"]}')
            exit(1)

        year, month = map(int, guild['startDate'].split('-'))
        if month < 1 or month > 12:
            logger.error(f'Guild field "startDate" must have valid month (01-12) - found {guild["startDate"]}')
            exit(1)

        # Check startDate is not in the future
        now = datetime.now(timezone.utc)
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        if start_date > now:
            logger.error(f'Guild field "startDate" cannot be in the future - found {guild["startDate"]}')
            exit(1)

        if "enabled" in guild and type(guild["enabled"]) != bool:
            logger.error(f'Optional guild field "enabled" must be a boolean if set - found {type(guild["enabled"])}')
            exit(1)

        if guild['tokenName'] not in self._tokens:
            logger.error(f'Token "{guild["tokenName"]}" not found in tokens. Available tokens: {", ".join(self._tokens.keys())}')
            exit(1)


class MonthlyBackupTracker:
    def __init__(self, metadata_path='exports/metadata.json'):
        self._metadata_path = metadata_path
        self._completed_months = {}  # {guildId: [list of YYYY-MM strings]}
        self._last_attempts = {}     # {guildId: ISO timestamp string}

        try:
            with open(metadata_path, encoding='utf-8') as f:
                metadata = json.load(f)
                self._completed_months = metadata.get('completedMonthlyBackups', {})
                self._last_attempts = metadata.get('lastBackupAttempts', {})

            total_completed = sum(len(months) for months in self._completed_months.values())
            logger.info(f"Loaded metadata: {len(self._completed_months)} guilds, {total_completed} completed months")
        except FileNotFoundError:
            logger.info(f"Metadata file not found at {metadata_path}, starting fresh")
        except json.JSONDecodeError as e:
            logger.warning(f"Metadata file corrupted, starting fresh: {e}")

    def get_completed_months(self, guild_id: str) -> list:
        return self._completed_months.get(guild_id, [])

    def is_month_completed(self, guild_id: str, month_str: str) -> bool:
        return month_str in self.get_completed_months(guild_id)

    def mark_month_completed(self, guild_id: str, month_str: str) -> None:
        if guild_id not in self._completed_months:
            self._completed_months[guild_id] = []
        if month_str not in self._completed_months[guild_id]:
            self._completed_months[guild_id].append(month_str)
            self._completed_months[guild_id].sort()
        self._save_metadata()

    def get_last_attempt(self, guild_id: str) -> str:
        return self._last_attempts.get(guild_id, None)

    def set_last_attempt(self, guild_id: str, timestamp: str) -> None:
        self._last_attempts[guild_id] = timestamp
        self._save_metadata()

    def _save_metadata(self) -> None:
        try:
            with open(self._metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except FileNotFoundError:
            metadata = {}
        except json.JSONDecodeError as e:
            logger.error(f"Metadata file corrupted, creating fresh: {e}")
            metadata = {}

        metadata['completedMonthlyBackups'] = self._completed_months
        metadata['lastBackupAttempts'] = self._last_attempts

        try:
            with open(self._metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logger.debug(f"Metadata saved successfully to {self._metadata_path}")
        except IOError as e:
            logger.error(f"Failed to save metadata to {self._metadata_path}: {e}", exc_info=True)


def get_current_month() -> str:
    """Returns current month in YYYY-MM format"""
    now = datetime.now(timezone.utc)
    return now.strftime('%Y-%m')


def parse_month(month_str: str) -> tuple:
    """Parse YYYY-MM string to (year, month) integers"""
    year, month = month_str.split('-')
    return int(year), int(month)


def get_month_boundaries(month_str: str) -> tuple:
    """
    Returns (start_iso, end_iso) for a given month in YYYY-MM format
    start_iso: first second of the month (YYYY-MM-01T00:00:00Z)
    end_iso: first second of next month (YYYY-(MM+1)-01T00:00:00Z)
    """
    year, month = parse_month(month_str)

    # Start of month
    start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    start_iso = start_dt.isoformat().replace('+00:00', 'Z')

    # Start of next month (end boundary)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end_dt = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_iso = end_dt.isoformat().replace('+00:00', 'Z')

    return start_iso, end_iso


def generate_months_to_backup(start_month: str, current_month: str, completed_months: list) -> list:
    """
    Generate list of months to backup from start_month to current_month (exclusive)
    Filters out already completed months
    Returns sorted list of YYYY-MM strings
    """
    start_year, start_mon = parse_month(start_month)
    current_year, current_mon = parse_month(current_month)

    months = []
    year, month = start_year, start_mon

    while (year < current_year) or (year == current_year and month < current_mon):
        month_str = f"{year:04d}-{month:02d}"
        if month_str not in completed_months:
            months.append(month_str)

        # Increment month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return months


class CommandRunner:
    def __init__(self, config: Config, tracker: MonthlyBackupTracker) -> None:
        self.config = config
        self.tracker = tracker

    def redact_dce_command(self, dce_command) -> str:
        """
        returns redacted discord token in command to safely print them to the console
        """
        dce_command = re.sub(r'--token "(.{5})[^"]+"', r'--token "\1***"', dce_command)
        return dce_command

    def export(self) -> None:
        total_guilds = len(self.config.guilds)
        logger.info(f"Starting backup for {total_guilds} guild(s)")

        guilds_processed = 0
        guilds_skipped = 0
        total_months_backed_up = 0

        for guild in self.config.guilds:
            logger.info(f'Processing guild: {guild["guildName"]} ({guild["guildId"]})')

            # Check throttle (once per guild before processing months)
            now_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            last_attempt = self.tracker.get_last_attempt(guild['guildId'])

            if last_attempt is not None:
                hours_since_last = (datetime.fromisoformat(now_timestamp) - datetime.fromisoformat(last_attempt)).total_seconds() / 3600
                logger.info(f'  Last backup attempt: {hours_since_last:.2f} hours ago')
                if hours_since_last < guild['throttleHours']:
                    logger.warning(f'  Skipping guild (throttled): {hours_since_last:.2f} < {guild["throttleHours"]} hours')
                    guilds_skipped += 1
                    continue

            # Get months to backup
            current_month = get_current_month()
            completed_months = self.tracker.get_completed_months(guild['guildId'])
            months_to_backup = generate_months_to_backup(guild['startDate'], current_month, completed_months)

            if not months_to_backup:
                logger.info(f'  All months up to {current_month} already backed up')
                guilds_processed += 1
                continue

            logger.info(f'  Found {len(months_to_backup)} month(s) to backup: {months_to_backup[:5]}{"..." if len(months_to_backup) > 5 else ""}')

            # Process each month
            months_backed_up = 0
            months_failed = 0
            total_months = len(months_to_backup)

            for idx, month_str in enumerate(months_to_backup, 1):
                logger.info(f'  Progress: Month {idx}/{total_months}')
                success = self._export_month(guild, month_str)
                if success:
                    months_backed_up += 1
                else:
                    months_failed += 1

            if months_failed > 0:
                logger.warning(f'  {months_failed} month(s) failed to backup')

            # Update last attempt timestamp after processing
            if months_backed_up > 0:
                self.tracker.set_last_attempt(guild['guildId'], now_timestamp)
                logger.info(f'  Successfully backed up {months_backed_up} month(s)')
                total_months_backed_up += months_backed_up

            guilds_processed += 1

        logger.info("=" * 50)
        logger.info(f"Backup summary:")
        logger.info(f"  Guilds processed: {guilds_processed}/{total_guilds}")
        logger.info(f"  Guilds skipped (throttled): {guilds_skipped}")
        logger.info(f"  Total months backed up: {total_months_backed_up}")
        logger.info("=" * 50)

    def _export_month(self, guild: dict, month_str: str) -> bool:
        """
        Export a single month for a guild
        Returns True if successful, False otherwise
        """
        logger.info(f'  Processing month: {month_str}')

        # Parse month for directory structure
        year, month = parse_month(month_str)
        year_str = f"{year:04d}"
        month_num = f"{month:02d}"

        # Create output directory structure: YYYY/MM/
        month_dir = f'exports/{guild["guildName"]}/{year_str}/{month_num}'
        completion_marker = os.path.join(month_dir, '.complete')

        # Check if backup was previously completed successfully
        if os.path.exists(completion_marker):
            logger.info(f'    Month {month_str} already completed (found .complete marker), skipping')
            self.tracker.mark_month_completed(guild['guildId'], month_str)
            return True

        # Warn if directory exists without completion marker (incomplete backup)
        if os.path.exists(month_dir) and os.listdir(month_dir):
            logger.warning(f'    Directory {month_dir} exists without .complete marker (incomplete backup detected)')
            logger.info(f'    Re-running backup for {month_str} to ensure completeness')

        # Create month directory if needed
        try:
            os.makedirs(month_dir, exist_ok=True)
            logger.debug(f'    Created directory: {month_dir}')
        except OSError as e:
            logger.error(f'    Failed to create directory {month_dir}: {e}', exc_info=True)
            return False

        # Get month boundaries
        start_iso, end_iso = get_month_boundaries(month_str)
        logger.debug(f'    Date range: {start_iso} to {end_iso}')

        # Build DiscordChatExporter command
        # Inside Docker container, DCE is always at /opt/app/DiscordChatExporter.Cli
        dce_path = '/opt/app/DiscordChatExporter.Cli'
        common_args = f'--format Json --media --reuse-media --fuck-russia --markdown false'
        custom_args = f'--token "{guild["tokenValue"]}" --media-dir "exports/{guild["guildName"]}/_media/" --output "{month_dir}/"'

        # Build export command based on guild type
        if guild['type'] == 'exportguild':
            command = f"{dce_path} exportguild --guild {guild['guildId']} --include-threads All {common_args} {custom_args}"
        elif guild['type'] == 'exportdm':
            command = f"{dce_path} exportdm {common_args} {custom_args}"
        else:
            logger.error(f'    Unknown export type: {guild["type"]}')
            return False

        # Add date range filters
        command = f'{command} --after "{start_iso}" --before "{end_iso}"'

        logger.info(f"    Running: {self.redact_dce_command(command)}")

        if not DRY_RUN:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )
            return_code = proc.returncode

            logger.info(f"    DCE exit code: {return_code}")

            # Log DCE stdout if present
            if proc.stdout:
                for line in proc.stdout.strip().split('\n'):
                    if line.strip():
                        logger.debug(f"    DCE stdout: {line}")

            # Log DCE stderr if present (errors/warnings)
            if proc.stderr:
                for line in proc.stderr.strip().split('\n'):
                    if line.strip():
                        logger.warning(f"    DCE stderr: {line}")

            if return_code == 0:
                # Mark month as completed in metadata
                self.tracker.mark_month_completed(guild['guildId'], month_str)

                # Create completion marker file
                try:
                    with open(completion_marker, 'w') as f:
                        f.write(f'Completed: {datetime.now(timezone.utc).isoformat()}\n')
                    logger.debug(f'    Created completion marker: {completion_marker}')
                except IOError as e:
                    logger.warning(f'    Failed to create completion marker: {e}')

                logger.info(f'    ✓ Successfully exported {month_str}')
                return True
            else:
                logger.error(f'    ✗ Failed to export {month_str} (exit code {return_code})')
                return False
        else:
            logger.warning("    Dry run mode - command not executed")
            return False


def main():
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("Discord Backup Script Starting")
    logger.info(f"Start time: {start_time.isoformat()}")
    logger.info("=" * 60)

    try:
        os.makedirs('exports', exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create exports directory: {e}", exc_info=True)
        exit(1)

    tracker = MonthlyBackupTracker(metadata_path='exports/metadata.json')
    config = Config(config_path='config/config.json')

    logger.info(f"Loaded {len(config.guilds)} guild(s) from configuration")

    command_runner = CommandRunner(config=config, tracker=tracker)
    command_runner.export()

    end_time = datetime.now(timezone.utc)
    duration = end_time - start_time

    logger.info("=" * 60)
    logger.info("Discord Backup Script Completed")
    logger.info(f"End time: {end_time.isoformat()}")
    logger.info(f"Total duration: {duration}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
