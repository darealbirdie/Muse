import aiosqlite
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="muse_bot.db"):
        self.db_path = db_path

    async def get_premium_users(self):
        """Get list of premium user IDs from database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                "SELECT user_id FROM users WHERE is_premium = TRUE AND (premium_expires IS NULL OR premium_expires > ?)",
                (datetime.now().isoformat(),)
            ) as cursor:
                    results = await cursor.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            print(f"Error getting premium users: {e}")
        return []
    async def set_channel_restriction(self, guild_id, channel_id, channel_type, languages, block_all=False):
        """Set allowed languages for a channel/type. block_all=True blocks all translations."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM channel_restrictions WHERE guild_id=? AND channel_id=? AND channel_type=?",
                (guild_id, channel_id, channel_type)
            )
            if block_all:
                await db.execute(
                    "INSERT INTO channel_restrictions (guild_id, channel_id, channel_type, language_code, block_all) VALUES (?, ?, ?, NULL, 1)",
                    (guild_id, channel_id, channel_type)
                )
            elif not languages:
                await db.execute(
                    "INSERT INTO channel_restrictions (guild_id, channel_id, channel_type, language_code, block_all) VALUES (?, ?, ?, NULL, 0)",
                    (guild_id, channel_id, channel_type)
                )
            else:
                for lang in languages:
                    await db.execute(
                        "INSERT INTO channel_restrictions (guild_id, channel_id, channel_type, language_code, block_all) VALUES (?, ?, ?, ?, 0)",
                        (guild_id, channel_id, channel_type, lang)
                    )
            await db.commit()

    async def is_translation_allowed(self, guild_id, channel_id, channel_type, lang_code):
        """Check if translation is allowed in this channel/type/language."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT language_code, block_all FROM channel_restrictions WHERE guild_id=? AND channel_id=? AND channel_type=?",
                (guild_id, channel_id, channel_type)
            ) as cursor:
                rows = await cursor.fetchall()
            if not rows:
                return True  # No restriction set
            for row in rows:
                if row[1]:  # block_all == 1
                    return False
            allowed_langs = {row[0] for row in rows if row[0]}
            if not allowed_langs:
                return True  # All languages allowed (NULL row exists)
            return lang_code.lower() in allowed_langs
    async def init_db(self):
        """Initialize database with all required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_premium BOOLEAN DEFAULT FALSE,
                    premium_expires DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_translations INTEGER DEFAULT 0,
                    preferred_source_lang TEXT DEFAULT 'auto',
                    preferred_target_lang TEXT DEFAULT 'en'
                )
            ''')
            
            # Usage tracking table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS usage_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date DATE,
                    text_characters_used INTEGER DEFAULT 0,
                    voice_seconds_used INTEGER DEFAULT 0,
                    translations_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, date)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS channel_restrictions (
                    guild_id      INTEGER NOT NULL,
                    channel_id    INTEGER NOT NULL,
                    channel_type  TEXT    NOT NULL, -- 'text' or 'voice'
                    language_code TEXT,             -- NULL means all languages allowed
                    PRIMARY KEY (guild_id, channel_id, channel_type, language_code)
                )
            ''')
            # Translation history table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS translation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    original_text TEXT,
                    translated_text TEXT,
                    source_lang TEXT,
                    target_lang TEXT,
                    translation_type TEXT, -- 'text', 'voice', 'auto'
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Server settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS server_settings (
                    guild_id INTEGER PRIMARY KEY,
                    translation_channel_id INTEGER,
                    auto_translate_enabled BOOLEAN DEFAULT FALSE,
                    default_source_lang TEXT DEFAULT 'auto',
                    default_target_lang TEXT DEFAULT 'en',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # ...existing code...
            # --- Add these reward/achievement tables ---
# ...existing code...
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    total_points INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    total_usage_hours REAL DEFAULT 0.0,
                    total_sessions INTEGER DEFAULT 0,
                    last_daily_claim DATE,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_translations INTEGER DEFAULT 0,
                    voice_sessions INTEGER DEFAULT 0,
                    unique_languages INTEGER DEFAULT 0,
                    servers_invited INTEGER DEFAULT 0
                )
            ''')
            # ...existing code...
            await db.execute('''
                CREATE TABLE IF NOT EXISTS point_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    transaction_type TEXT DEFAULT 'earned',
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_stats (user_id)
                )
            ''')
# ...existing code...
            await db.execute('''
                CREATE TABLE IF NOT EXISTS active_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reward_type TEXT NOT NULL,
                    reward_id TEXT,
                    name TEXT,
                    expires_at TEXT NOT NULL,
                    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
# ...existing code...
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    achievement_name TEXT NOT NULL,
                    achieved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            # Premium subscriptions table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS premium_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subscription_id TEXT,
                    provider TEXT, -- 'kofi', 'stripe', etc.
                    amount REAL,
                    currency TEXT DEFAULT 'USD',
                    status TEXT, -- 'active', 'cancelled', 'expired'
                    started_at DATETIME,
                    expires_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            # Add this to your init_db method after creating channel_restrictions table:
            await db.execute('''
                ALTER TABLE channel_restrictions ADD COLUMN block_all BOOLEAN DEFAULT 0
            ''')
# (Wrap in try/except in case the column already exists)
            await db.commit()
            logger.info("Database initialized successfully")
    
    # User management methods
    async def get_or_create_user(self, user_id: int, username: str = None):
        """Get user or create if doesn't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            # Try to get existing user
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                user = await cursor.fetchone()
            
            if user:
                # Update last active and username if provided
                await db.execute(
                    "UPDATE users SET last_active = ?, username = COALESCE(?, username) WHERE user_id = ?",
                    (datetime.now(), username, user_id)
                )
                await db.commit()
                return dict(zip([col[0] for col in cursor.description], user))
            else:
                # Create new user
                await db.execute(
                    "INSERT INTO users (user_id, username) VALUES (?, ?)",
                    (user_id, username)
                )
                await db.commit()
                return await self.get_or_create_user(user_id, username)
    
    async def update_user_premium(self, user_id: int, is_premium: bool, expires_at: datetime = None):
        """Update user premium status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_premium = ?, premium_expires = ? WHERE user_id = ?",
                (is_premium, expires_at, user_id)
            )
            await db.commit()
    
    async def get_user_preferences(self, user_id: int):
        """Get user's language preferences"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT preferred_source_lang, preferred_target_lang FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {"source": result[0], "target": result[1]}
                return {"source": "auto", "target": "en"}
    
    async def update_user_preferences(self, user_id: int, source_lang: str = None, target_lang: str = None):
        """Update user's language preferences"""
        async with aiosqlite.connect(self.db_path) as db:
            if source_lang:
                await db.execute(
                    "UPDATE users SET preferred_source_lang = ? WHERE user_id = ?",
                    (source_lang, user_id)
                )
            if target_lang:
                await db.execute(
                    "UPDATE users SET preferred_target_lang = ? WHERE user_id = ?",
                    (target_lang, user_id)
                )
            await db.commit()
    
    # Usage tracking methods
    async def track_usage(self, user_id: int, text_chars: int = 0, voice_seconds: int = 0):
        """Track daily usage for a user"""
        today = datetime.now().date()
        async with aiosqlite.connect(self.db_path) as db:
            # Insert or update today's usage
            await db.execute('''
                INSERT INTO usage_tracking (user_id, date, text_characters_used, voice_seconds_used, translations_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id, date) DO UPDATE SET
                    text_characters_used = text_characters_used + ?,
                    voice_seconds_used = voice_seconds_used + ?,
                    translations_count = translations_count + 1
            ''', (user_id, today, text_chars, voice_seconds, text_chars, voice_seconds))
            
            # Update total translations count
            await db.execute(
                "UPDATE users SET total_translations = total_translations + 1 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
    
    async def get_daily_usage(self, user_id: int, date: datetime.date = None):
        """Get usage for a specific date (default: today)"""
        if date is None:
            date = datetime.now().date()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT text_characters_used, voice_seconds_used, translations_count FROM usage_tracking WHERE user_id = ? AND date = ?",
                (user_id, date)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        "text_chars": result[0],
                        "voice_seconds": result[1],
                        "translations": result[2]
                    }
                return {"text_chars": 0, "voice_seconds": 0, "translations": 0}
    
    async def get_user_stats(self, user_id: int):
        """Get comprehensive user statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get user info
            async with db.execute(
                "SELECT total_translations, created_at, is_premium FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                user_info = await cursor.fetchone()
            
            # Get this month's usage
            first_day_of_month = datetime.now().replace(day=1).date()
            async with db.execute('''
                SELECT 
                    SUM(text_characters_used) as total_chars,
                    SUM(voice_seconds_used) as total_voice,
                    SUM(translations_count) as total_translations
                FROM usage_tracking 
                WHERE user_id = ? AND date >= ?
            ''', (user_id, first_day_of_month)) as cursor:
                monthly_stats = await cursor.fetchone()
            
            return {
                "total_translations": user_info[0] if user_info else 0,
                "member_since": user_info[1] if user_info else None,
                "is_premium": user_info[2] if user_info else False,
                "monthly_chars": monthly_stats[0] or 0,
                "monthly_voice": monthly_stats[1] or 0,
                "monthly_translations": monthly_stats[2] or 0
            }
    
    # Translation history methods
    async def save_translation(self, user_id: int, guild_id: int, original_text: str, 
                             translated_text: str, source_lang: str, target_lang: str, 
                             translation_type: str = "text"):
        """Save translation to history"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO translation_history 
                (user_id, guild_id, original_text, translated_text, source_lang, target_lang, translation_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, guild_id, original_text, translated_text, source_lang, target_lang, translation_type))
            await db.commit()
    
    async def get_translation_history(self, user_id: int, limit: int = 10):
        """Get recent translation history for user"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT original_text, translated_text, source_lang, target_lang, translation_type, created_at
                FROM translation_history 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit)) as cursor:
                results = await cursor.fetchall()
                return [
                    {
                        "original": row[0],
                        "translated": row[1],
                        "source_lang": row[2],
                        "target_lang": row[3],
                        "type": row[4],
                        "created_at": row[5]
                    }
                    for row in results
                ]
    
    # Server settings methods
    async def get_server_settings(self, guild_id: int):
        """Get server settings"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM server_settings WHERE guild_id = ?", (guild_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        "guild_id": result[0],
                        "translation_channel_id": result[1],
                        "auto_translate_enabled": result[2],
                        "default_source_lang": result[3],
                        "default_target_lang": result[4]
                    }
                return None
    
    async def update_server_settings(self, guild_id: int, **settings):
        """Update server settings"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create server settings if doesn't exist
            await db.execute(
                "INSERT OR IGNORE INTO server_settings (guild_id) VALUES (?)",
                (guild_id,)
            )
            
            # Update provided settings
            for key, value in settings.items():
                if key in ['translation_channel_id', 'auto_translate_enabled', 'default_source_lang', 'default_target_lang']:
                    await db.execute(
                        f"UPDATE server_settings SET {key} = ? WHERE guild_id = ?",
                        (value, guild_id)
                    )
            await db.commit()




# Global database instance
db = Database()
