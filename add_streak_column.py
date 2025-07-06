import sqlite3

# Hard-coded database path
DB_PATH = "muse_bot.db"

def add_streak_column():
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column already exists first
        cursor.execute("PRAGMA table_info(user_stats)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'daily_streak' in columns:
            print("✅ daily_streak column already exists!")
            conn.close()
            return True
            
        # Add the column
        cursor.execute("ALTER TABLE user_stats ADD COLUMN daily_streak INTEGER DEFAULT 0")
        
        # Commit changes
        conn.commit()
        
        # Verify it was added
        cursor.execute("PRAGMA table_info(user_stats)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print("✅ SUCCESS!")
        print(f"All columns: {columns}")
        print(f"daily_streak exists: {'daily_streak' in columns}")
        
        conn.close()
        return True
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✅ Column already exists!")
            return True
        else:
            print(f"❌ Error: {e}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_column_exists():
    """Check if daily_streak column exists"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(user_stats)")
        columns = [col[1] for col in cursor.fetchall()]
        exists = 'daily_streak' in columns
        conn.close()
        return exists
    except:
        return False

if __name__ == "__main__":
    add_streak_column()
