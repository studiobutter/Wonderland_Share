# Changelogs

## v1.0.3

**Release Date**: 01/15/2026

### Fixed

- Fixed `/wonderland` command failing silently when a level description exceeded Discord embed character limits.
- Long descriptions are now safely truncated to improve reliability and mobile readability.

### Improved

- Commands can now be used in Direct Messages (DMs) with the bot.
- Added structured logging with daily rotating log files to improve debugging and stability.
- Added a link to Community server (Wonderland Cafe)

### Internal

- Improved error handling to prevent unhandled exceptions from disrupting command execution.
- General stability and maintenance improvements.

## v1.0.2

**Release Date**: 12/03/2026

### Fixed

- Previous GUID being retained when running `/wonderland`

## v1.0.1

**Release Date**: 11/23/2025

Added `/about`, `/wonderland` cover images now upload to Discord CDN and use it to load instead of loading from HoYo servers. Introduce `/changelogs` command to view changelogs.

## v1.0.0

**Release Date**: 11/22/2025

Initial release
