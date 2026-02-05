import sqlite3

DB_PATH = "news_brief_01.db"

def migrate_database():
    """Add missing columns to existing database without losing data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Starting database migration...")
    
    try:
        # Check if cache_key column exists
        cursor.execute("PRAGMA table_info(cached_news)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'cache_key' not in columns:
            print("Adding cache_key column...")
            cursor.execute("ALTER TABLE cached_news ADD COLUMN cache_key TEXT")
            print("✓ Added cache_key column")
        
        if 'article_count' not in columns:
            print("Adding article_count column...")
            cursor.execute("ALTER TABLE cached_news ADD COLUMN article_count INTEGER DEFAULT 0")
            print("✓ Added article_count column")
        
        if 'is_too_old' not in columns:
            print("Adding is_too_old column...")
            cursor.execute("ALTER TABLE cached_news ADD COLUMN is_too_old BOOLEAN DEFAULT 0")
            print("✓ Added is_too_old column")
        
        # Create indexes for better performance
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON cached_news(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category_date ON cached_news(category, date)")
            print("✓ Created indexes")
        except:
            pass
        
        conn.commit()
        print("\n✓ Database migration completed successfully!")
        
    except Exception as e:
        print(f"✗ Migration error: {e}")
        conn.rollback()
    
    finally:
        conn.close()

def clear_old_cache():
    """Optional: Clear expired cache entries"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM cached_news WHERE expires_at < datetime('now')")
    deleted = cursor.rowcount
    
    cursor.execute("DELETE FROM user_news_cache WHERE datetime(created_at, '+24 hours') < datetime('now')")
    user_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✓ Cleaned up {deleted} expired cache entries")
    print(f"✓ Cleaned up {user_deleted} expired user cache entries")

if __name__ == "__main__":
    migrate_database()
    
    # Uncomment to clear old cache
    # clear_old_cache()
    
    print("\nYou can now run your FastAPI server!")
