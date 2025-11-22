import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
BOT_PREFIX = os.getenv('BOT_PREFIX', '/')
BOT_STATUS = os.getenv('BOT_STATUS', 'Online')
OWNER_ID = os.getenv('OWNER_ID')

# Server Region
class ServerRegion:
    ASIA = 'os_asia'
    EUROPE = 'os_euro'
    AMERICA = 'os_usa'
    CHT = 'os_cht'

REGION_NAMES = {
    ServerRegion.ASIA: 'Asia',
    ServerRegion.EUROPE: 'Europe',
    ServerRegion.AMERICA: 'America',
    ServerRegion.CHT: 'HK/TW/MO',
}

# Development
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
