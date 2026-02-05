from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import json
import os
from dotenv import load_dotenv
import requests
import feedparser
import hashlib
import secrets
import re

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

# Security
security = HTTPBearer()

# Database setup
DB_PATH = "news_brief_01.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            date TEXT,
            articles TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            UNIQUE(category, date)
        )
    """)
    
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
    
    conn.commit()
    conn.close()

init_db()

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    segments: List[str]
    reading_preference: Optional[str] = "short"
    language: Optional[str] = "en"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserPreferences(BaseModel):
    segments: List[str]
    reading_preference: Optional[str] = "short"
    language: Optional[str] = "en"

class NewsBriefRequest(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    force_refresh: Optional[bool] = False

# News Sources Configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")

CATEGORY_MAPPING = {
    "Technology": "technology",
    "Business": "business",
    "Sports": "sports",
    "Health": "health",
    "Entertainment": "entertainment",
    "Politics": "general"
}

RSS_FEEDS = {
    "Technology": ["https://feeds.bbci.co.uk/news/technology/rss.xml"],
    "Business": ["https://feeds.bbci.co.uk/news/business/rss.xml"],
    "Sports": ["https://feeds.bbci.co.uk/sport/rss.xml"],
    "Health": ["https://feeds.bbci.co.uk/news/health/rss.xml"],
    "Entertainment": ["https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"],
    "Politics": ["https://feeds.bbci.co.uk/news/politics/rss.xml"]
}

# Helper functions
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    return {"id": user[0], "email": user[1], "name": user[2]}

def is_cache_valid(created_at_str: str, hours: int = 6) -> bool:
    try:
        created_at = datetime.fromisoformat(created_at_str)
        return datetime.now() - created_at < timedelta(hours=hours)
    except:
        return False

def get_cached_news(category: str, date: str) -> Optional[List[dict]]:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT articles FROM cached_news WHERE category = ? AND date = ? AND expires_at > datetime('now')", (category, date))
        result = cursor.fetchone()
        conn.close()
        if result:
            articles = json.loads(result[0])
            # Return empty list if cached result is empty (means we already checked and found nothing)
            return articles
    except:
        pass
    return None

def cache_news(category: str, date: str, articles: List[dict], hours: int = 24):
    # Cache for 24 hours (even if empty) to avoid repeated API calls for old dates
    try:
        conn = get_db()
        cursor = conn.cursor()
        expires_at = datetime.now() + timedelta(hours=hours)
        cursor.execute("INSERT OR REPLACE INTO cached_news (category, date, articles, expires_at) VALUES (?, ?, ?, ?)",
                      (category, date, json.dumps(articles), expires_at))
        conn.commit()
        conn.close()
    except:
        pass

def get_user_news_cache(user_id: int, category: str, date: str) -> Optional[dict]:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT brief, created_at FROM user_news_cache WHERE user_id = ? AND category = ? AND date = ?",
                      (user_id, category, date))
        result = cursor.fetchone()
        conn.close()
        if result and is_cache_valid(result[1], hours=24):
            return json.loads(result[0])
    except:
        pass
    return None

def cache_user_news(user_id: int, category: str, date: str, brief: dict):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO user_news_cache (user_id, category, date, brief) VALUES (?, ?, ?, ?)",
                      (user_id, category, date, json.dumps(brief)))
        conn.commit()
        conn.close()
    except:
        pass

def smart_summarize(text: str, max_length: int = 200) -> str:
    """Lightweight extractive summarization"""
    if not text or len(text) < 50:
        return text
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    if not sentences:
        return text[:max_length]
    summary = '. '.join(sentences[:2])
    if len(summary) > max_length:
        summary = summary[:max_length] + '...'
    return summary

def fetch_from_newsapi(category: str, date: str = None) -> List[dict]:
    if not NEWS_API_KEY:
        return []
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {"apiKey": NEWS_API_KEY, "category": CATEGORY_MAPPING.get(category, "general"), "language": "en", "pageSize": 10}
        if date:
            params["from"] = date
            params["to"] = date
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            articles = []
            for article in response.json().get("articles", []):
                if article.get("title") and article.get("description"):
                    articles.append({
                        "title": article["title"],
                        "description": article.get("description", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", "NewsAPI"),
                        "published_at": article.get("publishedAt", "")
                    })
            return articles
    except:
        pass
    return []

def fetch_from_gnews(category: str, date: str = None) -> List[dict]:
    if not GNEWS_API_KEY:
        return []
    try:
        url = "https://gnews.io/api/v4/top-headlines"
        params = {"apikey": GNEWS_API_KEY, "category": CATEGORY_MAPPING.get(category, "general"), "lang": "en", "max": 10}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            articles = []
            for article in response.json().get("articles", []):
                if article.get("title") and article.get("description"):
                    articles.append({
                        "title": article["title"],
                        "description": article.get("description", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", "GNews"),
                        "published_at": article.get("publishedAt", "")
                    })
            return articles
    except:
        pass
    return []

def fetch_from_rss(category: str) -> List[dict]:
    articles = []
    for feed_url in RSS_FEEDS.get(category, []):
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                articles.append({
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", entry.get("description", "No description")),
                    "url": entry.get("link", ""),
                    "source": feed.feed.get("title", "RSS Feed"),
                    "published_at": entry.get("published", "")
                })
        except:
            pass
    return articles

def aggregate_news(category: str, date: str = None, use_cache: bool = True) -> tuple[List[dict], bool]:
    """
    Aggregate news from multiple sources with caching
    Returns: (articles_list, is_date_too_old)
    """
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    
    # Check if date is too old (more than 7 days for free tier APIs)
    try:
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        days_old = (datetime.now() - date_obj).days
        is_too_old = days_old > 7
    except:
        days_old = 0
        is_too_old = False
    
    # Check cache first
    if use_cache:
        cached = get_cached_news(category, target_date)
        if cached is not None:  # Found in cache (even if empty)
            print(f"Using cached news for {category} on {target_date} ({len(cached)} articles)")
            return cached, is_too_old
    
    # If date is too old, don't even try APIs (save quota)
    if is_too_old:
        print(f"Date {target_date} is too old ({days_old} days). Caching empty result.")
        cache_news(category, target_date, [])
        return [], True
    
    print(f"Fetching fresh news for {category} on {target_date}")
    all_articles = []
    
    # Fetch from APIs
    all_articles.extend(fetch_from_newsapi(category, date))
    all_articles.extend(fetch_from_gnews(category, date))
    
    # Only fetch RSS for current date (RSS doesn't support historical)
    if days_old <= 1:
        all_articles.extend(fetch_from_rss(category))
    
    # Remove duplicates
    unique_articles = []
    seen_titles = set()
    for article in all_articles:
        title_lower = article["title"].lower()[:50]
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_articles.append(article)
    
    final_articles = unique_articles[:15]
    
    # Cache the results (even if empty)
    cache_news(category, target_date, final_articles)
    
    return final_articles, is_too_old

def create_consolidated_summary(articles: List[dict], category: str, date: str, is_too_old: bool) -> str:
    """Create a consolidated summary for the category"""
    if not articles:
        if is_too_old:
            return f"📅 No news available for {category} on {date}.\n\nHistorical news is not available with free tier APIs (limited to last 7 days).\n\nPlease select a more recent date."
        else:
            return f"📅 No news available for {category} on {date}.\n\nTry refreshing or selecting a different date."
    
    key_points = []
    for article in articles[:5]:
        title = article.get("title", "")
        if title:
            key_points.append(f"• {title}")
    
    summary = f"{category} Highlights:\n\n" + "\n".join(key_points)
    sources = set(article.get("source", "Unknown") for article in articles)
    summary += f"\n\nSources: {', '.join(list(sources)[:5])}"
    return summary

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Daily News Brief Generator API", "version": "2.0", "memory_optimized": True}

@app.get("/categories")
def get_categories():
    return {"categories": list(CATEGORY_MAPPING.keys())}

@app.post("/register")
def register_user(user: UserRegister):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Email already registered")
        password_hash = hash_password(user.password)
        cursor.execute("INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)", (user.email, password_hash, user.name))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO user_preferences (user_id, segments, reading_preference, language) VALUES (?, ?, ?, ?)",
                      (user_id, json.dumps(user.segments), user.reading_preference, user.language))
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=30)
        cursor.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user_id, expires_at))
        conn.commit()
        conn.close()
        return {"message": "User registered successfully", "token": token, "user": {"id": user_id, "email": user.email, "name": user.name}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login_user(credentials: UserLogin):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?", (credentials.email,))
        user = cursor.fetchone()
        if not user or not verify_password(credentials.password, user[3]):
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=30)
        cursor.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user[0], expires_at))
        conn.commit()
        conn.close()
        return {"message": "Login successful", "token": token, "user": {"id": user[0], "email": user[1], "name": user[2]}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT segments, reading_preference, language FROM user_preferences WHERE user_id = ?", (current_user["id"],))
    prefs = cursor.fetchone()
    conn.close()
    if prefs:
        return {"user": current_user, "preferences": {"segments": json.loads(prefs[0]), "reading_preference": prefs[1], "language": prefs[2]}}
    return {"user": current_user, "preferences": {"segments": [], "reading_preference": "short", "language": "en"}}

@app.post("/logout")
def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (credentials.credentials,))
        conn.commit()
        conn.close()
    except:
        pass
    return {"message": "Logged out successfully"}

@app.put("/preferences")
def update_preferences(preferences: UserPreferences, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_preferences (user_id, segments, reading_preference, language, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
                  (current_user["id"], json.dumps(preferences.segments), preferences.reading_preference, preferences.language))
    cursor.execute("DELETE FROM user_news_cache WHERE user_id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return {"message": "Preferences updated successfully", "preferences": preferences}

@app.post("/news-brief")
def get_news_brief(request: NewsBriefRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT segments FROM user_preferences WHERE user_id = ?", (current_user["id"],))
    row = cursor.fetchone()
    categories = json.loads(row[0]) if row else ["Technology", "Business"]
    if request.category:
        categories = [request.category]
    target_date = request.date if request.date else datetime.now().strftime("%Y-%m-%d")
    
    briefs = []
    for category in categories:
        try:
            # Check user cache first
            if not request.force_refresh:
                cached_brief = get_user_news_cache(current_user["id"], category, target_date)
                if cached_brief:
                    cached_brief["cached"] = True
                    briefs.append(cached_brief)
                    continue
            
            # Fetch news
            articles, is_too_old = aggregate_news(category, target_date, use_cache=not request.force_refresh)
            
            # Process articles
            processed_articles = []
            for article in articles:
                processed_articles.append({
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "source": article["source"],
                    "published_at": article["published_at"],
                    "summary": smart_summarize(article.get("description", ""))
                })
            
            # Create brief (even if empty)
            brief = {
                "category": category,
                "date": target_date,
                "articles": processed_articles,
                "consolidated_summary": create_consolidated_summary(processed_articles, category, target_date, is_too_old),
                "cached": False,
                "no_news_available": len(processed_articles) == 0
            }
            
            # Cache the brief
            cache_user_news(current_user["id"], category, target_date, brief)
            briefs.append(brief)
        except:
            continue
    
    conn.close()
    return {"user": current_user["name"], "date": target_date, "briefs": briefs, "generated_at": datetime.now().isoformat()}

@app.delete("/clear-cache")
def clear_cache(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_news_cache WHERE user_id = ?", (current_user["id"],))
    cursor.execute("DELETE FROM cached_news")  # Also clear global cache
    conn.commit()
    conn.close()
    return {"message": "Cache cleared successfully"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "memory_optimized": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
