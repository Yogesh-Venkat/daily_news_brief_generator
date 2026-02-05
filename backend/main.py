from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import json
import feedparser
import hashlib
import secrets
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Daily News Brief Generator")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
DB_PATH = "news_brief_01.db"

# BBC RSS Feeds (Fallback source)
RSS_FEEDS = {
    "Technology": ["https://feeds.bbci.co.uk/news/technology/rss.xml"],
    "Business": ["https://feeds.bbci.co.uk/news/business/rss.xml"],
    "Sports": ["https://feeds.bbci.co.uk/sport/rss.xml"],
    "Health": ["https://feeds.bbci.co.uk/news/health/rss.xml"],
    "Entertainment": ["https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"],
    "Politics": ["https://feeds.bbci.co.uk/news/politics/rss.xml"]
}

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Initialize database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User preferences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            segments TEXT,
            reading_preference TEXT DEFAULT 'short',
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Cached news table - check if it exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cached_news'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Create new table with all columns
        cursor.execute("""
            CREATE TABLE cached_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT,
                category TEXT,
                date TEXT,
                articles TEXT,
                article_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(category, date)
            )
        """)
    else:
        # Add missing columns to existing table
        cursor.execute("PRAGMA table_info(cached_news)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'cache_key' not in columns:
            cursor.execute("ALTER TABLE cached_news ADD COLUMN cache_key TEXT")
            print("  ✓ Added cache_key column")
        
        if 'article_count' not in columns:
            cursor.execute("ALTER TABLE cached_news ADD COLUMN article_count INTEGER DEFAULT 0")
            print("  ✓ Added article_count column")
    
    # User news cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_news_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            date TEXT,
            brief TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, category, date)
        )
    """)
    
    # Create indexes (only if columns exist)
    cursor.execute("PRAGMA table_info(cached_news)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Always safe indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_date ON cached_news(date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_category_date ON cached_news(category, date DESC)")
    
    # Conditional index
    if 'cache_key' in columns:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_cache_key ON cached_news(cache_key)")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


# Initialize database on startup
init_db()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    segments: List[str]

class UserPreferences(BaseModel):
    segments: List[str]
    reading_preference: Optional[str] = "short"
    language: Optional[str] = "en"

class NewsBriefRequest(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    force_refresh: Optional[bool] = False

# ============================================================================
# HELPER FUNCTIONS - DATABASE
# ============================================================================

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def create_session_token() -> str:
    """Generate secure session token"""
    return secrets.token_urlsafe(32)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT users.id, users.email, users.name 
        FROM sessions 
        JOIN users ON sessions.user_id = users.id
        WHERE sessions.token = ? AND sessions.expires_at > datetime('now')
    """, (token,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {"id": user[0], "email": user[1], "name": user[2]}

# ============================================================================
# HELPER FUNCTIONS - NEWS FETCHING
# ============================================================================

def normalize_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD format"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def generate_cache_key(category: str, date: str) -> str:
    """Generate unique cache key for category + date"""
    key_string = f"{category}_{normalize_date(date)}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_news_from_database(category: str, date: str) -> Optional[List[dict]]:
    """
    PRIMARY SOURCE: Fetch news from database (seeded historical data)
    Returns articles if found, None otherwise
    """
    try:
        normalized_date = normalize_date(date)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Query database for seeded news
        cursor.execute("""
            SELECT articles, datetime(created_at) as created
            FROM cached_news 
            WHERE category = ? AND date = ?
        """, (category, normalized_date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            articles = json.loads(result[0])
            if articles:  # Only return if not empty
                print(f"✓ Database HIT: {category} on {normalized_date} ({len(articles)} articles)")
                return articles
        
        print(f"✗ Database MISS: {category} on {normalized_date}")
        return None
        
    except Exception as e:
        print(f"Database query error: {e}")
        return None

def fetch_from_bbc_rss(category: str) -> List[dict]:
    """
    FALLBACK SOURCE: Fetch latest news from BBC RSS feeds
    Only used when database has no data for requested date
    """
    print(f"→ Fetching from BBC RSS for {category}...")
    articles = []
    
    for feed_url in RSS_FEEDS.get(category, []):
        try:
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                continue
            
            for entry in feed.entries[:10]:
                try:
                    articles.append({
                        "title": entry.get("title", "No Title"),
                        "description": entry.get("summary", entry.get("description", "No description available")),
                        "url": entry.get("link", ""),
                        "source": feed.feed.get("title", "BBC News"),
                        "published_at": entry.get("published", ""),
                        "category": category
                    })
                except Exception as e:
                    print(f"  ✗ Error parsing entry: {e}")
                    continue
            
        except Exception as e:
            print(f"  ✗ Error fetching feed: {e}")
            continue
    
    print(f"  ✓ Fetched {len(articles)} articles from RSS")
    return articles

def save_to_cache(category: str, date: str, articles: List[dict], hours: int = 24):
    """Save news to cache"""
    try:
        normalized_date = normalize_date(date)
        cache_key = generate_cache_key(category, normalized_date)
        expires_at = datetime.now() + timedelta(hours=hours)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO cached_news 
            (cache_key, category, date, articles, article_count, expires_at, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (cache_key, category, normalized_date, json.dumps(articles), len(articles), expires_at))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Cached: {category} on {normalized_date} ({len(articles)} articles)")
        
    except Exception as e:
        print(f"Cache save error: {e}")

def aggregate_news(category: str, date: str, use_cache: bool = True) -> tuple[List[dict], str]:
    """
    Aggregate news with priority system:
    1. Database (seeded historical data) - PRIMARY
    2. BBC RSS (fallback for recent dates only) - SECONDARY
    
    Returns: (articles_list, source_type)
    """
    target_date = normalize_date(date)
    
    print(f"\n{'='*60}")
    print(f"Fetching news for: {category} on {target_date}")
    print(f"{'='*60}")
    
    # PRIORITY 1: Check database first (seeded data)
    if use_cache:
        db_articles = get_news_from_database(category, target_date)
        if db_articles:
            return db_articles, "database"
    
    # PRIORITY 2: Fallback to BBC RSS (only for very recent dates)
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    days_old = (datetime.now() - date_obj).days
    
    if days_old <= 1:  # Only use RSS for today/yesterday
        print(f"→ Falling back to BBC RSS (recent date: {days_old} days old)")
        articles = fetch_from_bbc_rss(category)
        
        if articles:
            # Remove duplicates
            unique_articles = []
            seen_titles = set()
            
            for article in articles:
                title_key = article["title"].lower()[:50]
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_articles.append(article)
            
            final_articles = unique_articles[:15]
            
            # Cache for future requests
            save_to_cache(category, target_date, final_articles)
            return final_articles, "rss"
    
    # No data available
    print(f"✗ No articles available for {category} on {target_date}")
    print(f"  (Date is {days_old} days old - too old for RSS, not in database)")
    return [], "none"

def create_summary(articles: List[dict], category: str, date: str, source: str) -> str:
    """Create consolidated summary"""
    if not articles:
        if source == "none":
            return f"📅 No news available for {category} on {date}.\n\n" \
                   f"This date is not in our database. Historical data is available for " \
                   f"dates that have been pre-seeded.\n\n" \
                   f"Please select a more recent date or run the seeding script to populate historical data."
        return f"No news available for {category} at this time."
    
    highlights = []
    for article in articles[:5]:
        highlights.append(f"• {article['title']}")
    
    summary = f"{category} Highlights:\n\n" + "\n\n".join(highlights)
    
    # Add source information
    if source == "database":
        summary += f"\n\n📊 Source: Pre-seeded historical database"
    elif source == "rss":
        summary += f"\n\n📡 Source: BBC News RSS (Live)"
    
    return summary

# ============================================================================
# API ENDPOINTS - ROOT & UTILITY
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Daily News Brief Generator",
        "version": "3.0",
        "features": [
            "Database-first architecture",
            "Historical news support (seeded data)",
            "BBC RSS fallback for recent dates",
            "User authentication",
            "Personalized news preferences"
        ],
        "sources": {
            "primary": "Seeded Database (NewsAPI + GNews historical data)",
            "fallback": "BBC News RSS Feeds (live)"
        }
    }

@app.get("/categories")
def get_categories():
    """Get available news categories"""
    return {"categories": list(RSS_FEEDS.keys())}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": DB_PATH
    }

# ============================================================================
# API ENDPOINTS - AUTHENTICATION
# ============================================================================

@app.post("/register")
def register(user: UserRegister):
    """Register a new user"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Insert user
        password_hash = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, created_at) VALUES (?, ?, ?, datetime('now'))",
            (user.email, password_hash, user.name)
        )
        user_id = cursor.lastrowid
        
        # Insert preferences
        cursor.execute("""
            INSERT INTO user_preferences (user_id, segments, created_at, updated_at) 
            VALUES (?, ?, datetime('now'), datetime('now'))
        """, (user_id, json.dumps(user.segments)))
        
        # Create session
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=30)
        cursor.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, datetime('now'))",
            (token, user_id, expires_at)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "message": "User registered successfully",
            "token": token,
            "user": {"id": user_id, "email": user.email, "name": user.name}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login(credentials: UserLogin):
    """Login user"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?", 
                      (credentials.email,))
        user = cursor.fetchone()
        
        if not user or not verify_password(credentials.password, user[3]):
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=30)
        
        cursor.execute("INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, datetime('now'))",
                      (token, user[0], expires_at))
        conn.commit()
        conn.close()
        
        return {
            "message": "Login successful",
            "token": token,
            "user": {"id": user[0], "email": user[1], "name": user[2]}
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (credentials.credentials,))
        conn.commit()
        conn.close()
    except:
        pass
    return {"message": "Logged out successfully"}

@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT segments, reading_preference, language FROM user_preferences WHERE user_id = ?", 
                  (current_user["id"],))
    prefs = cursor.fetchone()
    conn.close()
    
    if prefs:
        return {
            "user": current_user,
            "preferences": {
                "segments": json.loads(prefs[0]),
                "reading_preference": prefs[1],
                "language": prefs[2]
            }
        }
    
    return {
        "user": current_user,
        "preferences": {
            "segments": ["Technology"],
            "reading_preference": "short",
            "language": "en"
        }
    }

@app.put("/preferences")
def update_preferences(preferences: UserPreferences, current_user: dict = Depends(get_current_user)):
    """Update user preferences"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_preferences 
        (user_id, segments, reading_preference, language, updated_at) 
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (current_user["id"], json.dumps(preferences.segments), 
          preferences.reading_preference, preferences.language))
    
    # Clear user's personalized cache when preferences change
    cursor.execute("DELETE FROM user_news_cache WHERE user_id = ?", (current_user["id"],))
    
    conn.commit()
    conn.close()
    
    return {"message": "Preferences updated successfully", "preferences": preferences}

# ============================================================================
# API ENDPOINTS - NEWS
# ============================================================================

@app.post("/news-brief")
def get_news_brief(request: NewsBriefRequest, current_user: dict = Depends(get_current_user)):
    """
    Get personalized news brief
    Priority: Database (seeded data) → BBC RSS (fallback)
    """
    
    # Get user preferences
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT segments FROM user_preferences WHERE user_id = ?", 
                  (current_user["id"],))
    row = cursor.fetchone()
    conn.close()
    
    categories = json.loads(row[0]) if row else ["Technology", "Business"]
    
    # Override with specific category if requested
    if request.category:
        categories = [request.category]
    
    target_date = normalize_date(request.date or datetime.now().strftime("%Y-%m-%d"))
    
    briefs = []
    for category in categories:
        print(f"\n{'='*60}")
        print(f"Processing: {category}")
        print(f"{'='*60}")
        
        # Fetch news (database first, RSS fallback)
        articles, source = aggregate_news(
            category,
            target_date,
            use_cache=not request.force_refresh
        )
        
        # Create brief
        brief = {
            "category": category,
            "date": target_date,
            "articles": articles[:10],
            "consolidated_summary": create_summary(articles, category, target_date, source),
            "cached": not request.force_refresh,
            "no_news_available": len(articles) == 0,
            "source": source  # "database", "rss", or "none"
        }
        
        briefs.append(brief)
    
    return {
        "user": current_user["name"],
        "date": target_date,
        "briefs": briefs,
        "generated_at": datetime.now().isoformat()
    }

# ============================================================================
# API ENDPOINTS - CACHE MANAGEMENT
# ============================================================================

@app.delete("/clear-cache")
def clear_cache(current_user: dict = Depends(get_current_user)):
    """Clear user's news cache"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_news_cache WHERE user_id = ?", (current_user["id"],))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    
    return {"message": f"Cleared {count} user cache entries"}

@app.get("/cache-stats")
def cache_stats():
    """Get cache statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get cache entries
    cursor.execute("""
        SELECT category, date, article_count,
               datetime(created_at, 'localtime') as created,
               datetime(expires_at, 'localtime') as expires
        FROM cached_news 
        ORDER BY date DESC, category
        LIMIT 50
    """)
    
    cache_entries = [dict(row) for row in cursor.fetchall()]
    
    # Get total counts
    cursor.execute("SELECT COUNT(*) FROM cached_news")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cached_news WHERE article_count > 0")
    non_empty = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_entries": total,
        "non_empty_entries": non_empty,
        "recent_entries": cache_entries
    }

# ============================================================================
# ADMIN ENDPOINTS (Optional - for manual seeding)
# ============================================================================

@app.post("/admin/seed-news")
async def trigger_seed(days: int = 3, current_user: dict = Depends(get_current_user)):
    """
    Manually trigger news seeding (admin only)
    Requires seed_historical_news.py in same directory
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ["python", "seed_historical_news.py", "--days", str(days)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        return {
            "status": "completed",
            "days_seeded": days,
            "stdout": result.stdout[-1000:],  # Last 1000 chars
            "stderr": result.stderr[-500:] if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Seeding took too long"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
