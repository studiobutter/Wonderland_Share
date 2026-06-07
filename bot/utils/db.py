"""Database utility module for managing user settings."""
from pathlib import Path

import aiosqlite

DB_PATH = Path("data/settings.db")

class Database:
    """Class to handle asynchronous SQLite operations for user settings."""
    def __init__(self):
        self.db_path = DB_PATH
        # Ensure data directory exists
        self.db_path.parent.mkdir(exist_ok=True)

    async def initialize(self):
        """Initializes the database schema."""
        async with aiosqlite.connect(self.db_path) as database:
            await database.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    default_server TEXT,
                    language TEXT DEFAULT 'auto'
                )
            """)
            await database.commit()

    async def get_user_settings(self, user_id: int):
        """Retrieves settings for a specific user."""
        async with aiosqlite.connect(self.db_path) as database:
            async with database.execute(
                "SELECT default_server, language FROM user_settings WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {"default_server": row[0], "language": row[1]}
                return {"default_server": None, "language": "auto"}

    async def update_user_setting(self, user_id: int, key: str, value: str):
        """Updates a specific setting for a user."""
        if key not in ["default_server", "language"]:
            raise ValueError("Invalid setting key")
        
        async with aiosqlite.connect(self.db_path) as database:
            await database.execute(f"""
                INSERT INTO user_settings (user_id, {key})
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET {key} = excluded.{key}
            """, (user_id, value))
            await database.commit()

db = Database()
