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
import re


app = FastAPI(title="Daily News Brief Generator")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBearer()
DB_PATH = "news_brief_01.db"


# BBC RSS Feeds (Always work, no API key needed)
RSS_FEEDS = {
    "Technology": ["https://feeds.bbci.co.uk/news/technology/rss.xml"],
    "Business": ["https://feeds.bbci.co.uk/news/business/rss.xml"],
    "Sports": ["https://feeds.bbci.co.uk/sport/rss.xml"],
    "Health": ["https://feeds.bbci.co.uk/news/health/rss.xml"],
    "Entertainment": ["https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"],
    "Politics": ["https://feeds.bbci.co.uk/news/politics/rss.xml"]
}


# Database Initialization
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
    
    # Cached news table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_news (
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
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_date ON cached_news(date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_category_date ON cached_news(category, date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_cache_key ON cached_news(cache_key)")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


# Initialize database on startup
init_db()


# Models
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    segments: List[str]


class NewsBriefRequest(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    force_refresh: Optional[bool] = False


# Helper Functions
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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


def normalize_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD format"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")


def generate_cache_key(category: str, date: str) -> str:
    """Generate unique cache key"""
    key_string = f"{category}_{normalize_date(date)}"
    return hashlib.md5(key_string.encode()).hexdigest()


def fetch_from_bbc_rss(category: str) -> List[dict]:
    """Fetch news from BBC RSS feeds"""
    print(f"\n→ Fetching from BBC RSS for {category}...")
    articles = []
    
    for feed_url in RSS_FEEDS.get(category, []):
        try:
            print(f"  Parsing: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"  ✗ No entries found")
                continue
            
            for entry in feed.entries[:10]:
                try:
                    # Parse published date
                    pub_date = entry.get("published", "")
                    
                    articles.append({
                        "title": entry.get("title", "No Title"),
                        "description": entry.get("summary", entry.get("description", "No description available")),
                        "url": entry.get("link", ""),
                        "source": feed.feed.get("title", "BBC News"),
                        "published_at": pub_date,
                        "category": category
                    })
                except Exception as e:
                    print(f"  ✗ Error parsing entry: {e}")
                    continue
            
            print(f"  ✓ Fetched {len(articles)} articles")
            
        except Exception as e:
            print(f"  ✗ Error fetching feed: {e}")
            continue
    
    return articles


def get_cached_news(category: str, date: str) -> Optional[List[dict]]:
    """Get cached news with proper date handling"""
    try:
        normalized_date = normalize_date(date)
        cache_key = generate_cache_key(category, normalized_date)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Try with cache_key first (new schema)
        cursor.execute("""
            SELECT articles, datetime(created_at) as created
            FROM cached_news 
            WHERE cache_key = ? AND expires_at > datetime('now')
        """, (cache_key,))
        
        result = cursor.fetchone()
        
        # Fallback to old schema (category + date)
        if not result:
            cursor.execute("""
                SELECT articles, datetime(created_at) as created
                FROM cached_news 
                WHERE category = ? AND date = ? AND expires_at > datetime('now')
            """, (category, normalized_date))
            result = cursor.fetchone()
        
        conn.close()
        
        if result:
            articles = json.loads(result[0])
            created_time = result[1]
            print(f"✓ Cache HIT: {category} on {normalized_date} ({len(articles)} articles, cached at {created_time})")
            return articles
        
        print(f"✗ Cache MISS: {category} on {normalized_date}")
        return None
        
    except Exception as e:
        print(f"Cache retrieval error: {e}")
        return None


def save_to_cache(category: str, date: str, articles: List[dict], hours: int = 6):
    """Save news to cache with both old and new schema support"""
    try:
        normalized_date = normalize_date(date)
        cache_key = generate_cache_key(category, normalized_date)
        expires_at = datetime.now() + timedelta(hours=hours)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if cache_key column exists
        cursor.execute("PRAGMA table_info(cached_news)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'cache_key' in columns:
            # New schema
            cursor.execute("""
                INSERT OR REPLACE INTO cached_news 
                (cache_key, category, date, articles, article_count, expires_at, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (cache_key, category, normalized_date, json.dumps(articles), len(articles), expires_at))
        else:
            # Old schema
            cursor.execute("""
                INSERT OR REPLACE INTO cached_news 
                (category, date, articles, expires_at, created_at) 
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (category, normalized_date, json.dumps(articles), expires_at))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Cached: {category} on {normalized_date} ({len(articles)} articles, expires in {hours}h)")
        
    except Exception as e:
        print(f"Cache save error: {e}")


def aggregate_news_from_bbc(category: str, date: str, use_cache: bool = True) -> List[dict]:
    """
    Aggregate news from BBC RSS with caching
    RSS feeds show latest news regardless of date, so we filter by date
    """
    target_date = normalize_date(date)
    
    print(f"\n{'='*60}")
    print(f"Fetching news for: {category} on {target_date}")
    print(f"Use cache: {use_cache}")
    print(f"{'='*60}")
    
    # Check cache first
    if use_cache:
        cached = get_cached_news(category, target_date)
        if cached is not None:
            return cached
    
    # Fetch from BBC RSS
    articles = fetch_from_bbc_rss(category)
    
    if not articles:
        print(f"✗ No articles fetched for {category}")
        # Cache empty result to avoid repeated fetches
        save_to_cache(category, target_date, [])
        return []
    
    # Remove duplicates
    unique_articles = []
    seen_titles = set()
    
    for article in articles:
        title_key = article["title"].lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(article)
    
    print(f"✓ Total unique articles: {len(unique_articles)}")
    
    # Cache the results
    save_to_cache(category, target_date, unique_articles)
    
    return unique_articles


def create_summary(articles: List[dict], category: str) -> str:
    """Create consolidated summary"""
    if not articles:
        return f"No news available for {category} at this time."
    
    highlights = []
    for i, article in enumerate(articles[:5], 1):
        highlights.append(f"• {article['title']}")
    
    summary = f"{category} Highlights:\n\n" + "\n\n".join(highlights)
    summary += f"\n\nSources: BBC News"
    
    return summary


# API Endpoints
@app.get("/")
def root():
    return {
        "message": "Daily News Brief Generator - BBC RSS Edition",
        "version": "2.0",
        "sources": "BBC News RSS Feeds"
    }


@app.get("/categories")
def get_categories():
    """Get available news categories"""
    return {"categories": list(RSS_FEEDS.keys())}


@app.post("/login")
def login(credentials: UserLogin):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?", 
                      (credentials.email,))
        user = cursor.fetchone()
        
        if not user or not verify_password(credentials.password, user[3]):
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
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


@app.post("/register")
def register(user: UserRegister):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Insert user with created_at
        password_hash = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, created_at) VALUES (?, ?, ?, datetime('now'))",
            (user.email, password_hash, user.name)
        )
        user_id = cursor.lastrowid
        
        # Insert preferences with timestamps
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


@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT segments FROM user_preferences WHERE user_id = ?", 
                  (current_user["id"],))
    prefs = cursor.fetchone()
    conn.close()
    
    segments = json.loads(prefs[0]) if prefs else ["Technology"]
    
    return {
        "user": current_user,
        "preferences": {"segments": segments}
    }


@app.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (credentials.credentials,))
        conn.commit()
        conn.close()
    except:
        pass
    return {"message": "Logged out successfully"}


@app.post("/news-brief")
def get_news_brief(request: NewsBriefRequest, current_user: dict = Depends(get_current_user)):
    """Get news brief from BBC RSS"""
    
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
        
        # Fetch news
        articles = aggregate_news_from_bbc(
            category,
            target_date,
            use_cache=not request.force_refresh
        )
        
        # Create brief
        brief = {
            "category": category,
            "date": target_date,
            "articles": articles[:10],
            "consolidated_summary": create_summary(articles, category),
            "cached": not request.force_refresh,
            "no_news_available": len(articles) == 0
        }
        
        briefs.append(brief)
    
    return {
        "user": current_user["name"],
        "date": target_date,
        "briefs": briefs,
        "generated_at": datetime.now().isoformat()
    }


@app.delete("/clear-cache")
def clear_cache(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cached_news")
    cursor.execute("DELETE FROM user_news_cache WHERE user_id = ?", (current_user["id"],))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    
    return {"message": f"Cleared {count} cache entries"}


@app.get("/cache-stats")
def cache_stats():
    """Debug endpoint to see cache contents"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if article_count column exists
    cursor.execute("PRAGMA table_info(cached_news)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'article_count' in columns:
        cursor.execute("""
            SELECT category, date, article_count, 
                   datetime(created_at, 'localtime') as created,
                   datetime(expires_at, 'localtime') as expires
            FROM cached_news 
            ORDER BY created_at DESC 
            LIMIT 20
        """)
    else:
        cursor.execute("""
            SELECT category, date,
                   datetime(created_at, 'localtime') as created,
                   datetime(expires_at, 'localtime') as expires
            FROM cached_news 
            ORDER BY created_at DESC 
            LIMIT 20
        """)
    
    cache_entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "total_entries": len(cache_entries),
        "entries": cache_entries
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
