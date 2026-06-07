# Changelogs

## v1.0.7

**Release Date**: 06/08/2026

- imp: Added settings to set user language and default server region
- loc: Localization support for English, Vietnamese and Chinese (Traditional), more languages coming soon! Contributions coming soon.
- imp: Wonderland command can call Localized texts. Fall back is used in the backend and show said content if said language isn't avaliable
- imp: Code QA Check

## v1.0.6

**Release Date**: 06/07/2026

- imp: Open with Genshin Impact - Cloud
- imp: Added Likes, Hotness and Amount of players requires to play.

## v1.0.5

**Release Date**: 04/26/2026

- fix: GUID characters that are not valid hexadecimal digits are now properly handled in /wonderland command

## v1.0.4

**Release Date**: 04/23/2026

- improve: Support for Python 3.13
- fix: No errors when invalid GUID is provided to /wonderland command
- feat: Added /del for deleting bot messages in DMs only

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
