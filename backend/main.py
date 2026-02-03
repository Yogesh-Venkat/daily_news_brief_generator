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
from collections import defaultdict
import hashlib
import secrets
import traceback

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
DB_PATH = "news_brief.db"

def init_db():
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
    
    # Sessions table for authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Cached news table - stores fetched news
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
    
    # User news cache - personalized cache per user
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

class Article(BaseModel):
    title: str
    description: str
    url: str
    source: str
    published_at: str
    summary: Optional[str] = None

class NewsBrief(BaseModel):
    category: str
    date: str
    articles: List[Article]
    consolidated_summary: str
    cached: bool = False

# Initialize summarization pipeline (optional - graceful fallback)
summarizer = None
try:
    from transformers import pipeline
    print("Loading AI summarization model...")
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    print("AI model loaded successfully!")
except Exception as e:
    print(f"AI model not available (using fallback): {e}")
    summarizer = None

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
    "Technology": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.wired.com/feed/rss",
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "Sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ],
    "Health": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
    ],
    "Entertainment": [
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
    "Politics": [
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
    ]
}

# Helper functions
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def create_session_token() -> str:
    """Generate secure session token"""
    return secrets.token_urlsafe(32)
def smart_summarize(text: str) -> str:
    """Extract first 2 key sentences"""
    sentences = text.split('.')
    return '. '.join(sentences[:2])
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {"id": user[0], "email": user[1], "name": user[2]}

def is_cache_valid(created_at_str: str, hours: int = 1) -> bool:
    """Check if cached data is still valid"""
    try:
        created_at = datetime.fromisoformat(created_at_str)
        return datetime.now() - created_at < timedelta(hours=hours)
    except:
        return False

def get_cached_news(category: str, date: str) -> Optional[List[dict]]:
    """Get cached news if available and valid"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT articles, created_at 
            FROM cached_news 
            WHERE category = ? AND date = ? AND expires_at > datetime('now')
        """, (category, date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
    except Exception as e:
        print(f"Cache read error: {e}")
    return None

def cache_news(category: str, date: str, articles: List[dict], hours: int = 6):
    """Cache news articles"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=hours)
        
        cursor.execute("""
            INSERT OR REPLACE INTO cached_news (category, date, articles, expires_at)
            VALUES (?, ?, ?, ?)
        """, (category, date, json.dumps(articles), expires_at))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cache write error: {e}")

def get_user_news_cache(user_id: int, category: str, date: str) -> Optional[dict]:
    """Get user's personalized cached brief"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT brief, created_at 
            FROM user_news_cache 
            WHERE user_id = ? AND category = ? AND date = ?
        """, (user_id, category, date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and is_cache_valid(result[1], hours=6):
            return json.loads(result[0])
    except Exception as e:
        print(f"User cache read error: {e}")
    return None

def cache_user_news(user_id: int, category: str, date: str, brief: dict):
    """Cache user's personalized brief"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_news_cache (user_id, category, date, brief)
            VALUES (?, ?, ?, ?)
        """, (user_id, category, date, json.dumps(brief)))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"User cache write error: {e}")

def summarize_text(text: str, max_length: int = 130) -> str:
    """Summarize text using AI model or fallback to extractive summary"""
    if not text or len(text) < 50:
        return text
    
    try:
        if summarizer:
            # Limit input length for model
            input_text = text[:1000]
            result = summarizer(input_text, max_length=max_length, min_length=30, do_sample=False)
            return result[0]['summary_text']
        else:
            # Fallback: extractive summary (first 2 sentences)
            sentences = text.replace('!', '.').replace('?', '.').split('. ')
            summary = '. '.join(sentences[:2])
            return summary[:200] + '...' if len(summary) > 200 else summary
    except Exception as e:
        print(f"Summarization error: {e}")
        # Last resort fallback
        sentences = text.split('. ')
        return sentences[0][:150] + '...' if len(sentences[0]) > 150 else sentences[0]

def fetch_from_newsapi(category: str, date: str = None) -> List[dict]:
    """Fetch news from NewsAPI"""
    if not NEWS_API_KEY:
        return []
    
    try:
        category_key = CATEGORY_MAPPING.get(category, "general")
        url = "https://newsapi.org/v2/top-headlines"
        
        params = {
            "apiKey": NEWS_API_KEY,
            "category": category_key,
            "language": "en",
            "pageSize": 10
        }
        
        if date:
            params["from"] = date
            params["to"] = date
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = []
            
            for article in data.get("articles", []):
                if article.get("title") and article.get("description"):
                    articles.append({
                        "title": article["title"],
                        "description": article.get("description", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", "NewsAPI"),
                        "published_at": article.get("publishedAt", ""),
                    })
            
            return articles
    except Exception as e:
        print(f"NewsAPI error: {e}")
    
    return []

def fetch_from_gnews(category: str, date: str = None) -> List[dict]:
    """Fetch news from GNews"""
    if not GNEWS_API_KEY:
        return []
    
    try:
        category_key = CATEGORY_MAPPING.get(category, "general")
        url = "https://gnews.io/api/v4/top-headlines"
        
        params = {
            "apikey": GNEWS_API_KEY,
            "category": category_key,
            "lang": "en",
            "max": 10
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = []
            
            for article in data.get("articles", []):
                if article.get("title") and article.get("description"):
                    articles.append({
                        "title": article["title"],
                        "description": article.get("description", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", "GNews"),
                        "published_at": article.get("publishedAt", ""),
                    })
            
            return articles
    except Exception as e:
        print(f"GNews error: {e}")
    
    return []

def fetch_from_rss(category: str) -> List[dict]:
    """Fetch news from RSS feeds"""
    articles = []
    feeds = RSS_FEEDS.get(category, [])
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:5]:
                articles.append({
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", entry.get("description", "No description available")),
                    "url": entry.get("link", ""),
                    "source": feed.feed.get("title", "RSS Feed"),
                    "published_at": entry.get("published", ""),
                })
        except Exception as e:
            print(f"RSS feed error for {feed_url}: {e}")
    
    return articles

def aggregate_news(category: str, date: str = None, use_cache: bool = True) -> List[dict]:
    """Aggregate news from multiple sources with caching"""
    
    # Check cache first
    if use_cache:
        cached = get_cached_news(category, date or datetime.now().strftime("%Y-%m-%d"))
        if cached:
            print(f"Using cached news for {category}")
            return cached
    
    print(f"Fetching fresh news for {category}")
    all_articles = []
    
    # Fetch from multiple sources
    try:
        all_articles.extend(fetch_from_newsapi(category, date))
    except Exception as e:
        print(f"Error fetching from NewsAPI: {e}")
    
    try:
        all_articles.extend(fetch_from_gnews(category, date))
    except Exception as e:
        print(f"Error fetching from GNews: {e}")
    
    try:
        all_articles.extend(fetch_from_rss(category))
    except Exception as e:
        print(f"Error fetching from RSS: {e}")
    
    # Remove duplicates
    unique_articles = []
    seen_titles = set()
    
    for article in all_articles:
        title_lower = article["title"].lower()[:50]
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_articles.append(article)
    
    final_articles = unique_articles[:15]
    
    # Cache the results
    if final_articles:
        cache_news(category, date or datetime.now().strftime("%Y-%m-%d"), final_articles)
    
    return final_articles

def create_consolidated_summary(articles: List[dict], category: str) -> str:
    """Create a consolidated summary for the category"""
    if not articles:
        return f"No news available for {category} at this time."
    
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
    return {
        "message": "Daily News Brief Generator API v2.0",
        "version": "2.0.0",
        "features": ["Authentication", "Caching", "Personalization"],
        "ai_model": "loaded" if summarizer else "fallback mode",
        "endpoints": ["/register", "/login", "/preferences", "/news-brief", "/categories"]
    }

@app.get("/categories")
def get_categories():
    """Get available news categories"""
    return {
        "categories": list(CATEGORY_MAPPING.keys())
    }

@app.post("/register")
def register_user(user: UserRegister):
    """Register a new user with preferences"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        password_hash = hash_password(user.password)
        cursor.execute("""
            INSERT INTO users (email, password_hash, name)
            VALUES (?, ?, ?)
        """, (user.email, password_hash, user.name))
        
        user_id = cursor.lastrowid
        
        # Save preferences
        cursor.execute("""
            INSERT INTO user_preferences (user_id, segments, reading_preference, language)
            VALUES (?, ?, ?, ?)
        """, (user_id, json.dumps(user.segments), user.reading_preference, user.language))
        
        # Create session
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=30)
        
        cursor.execute("""
            INSERT INTO sessions (token, user_id, expires_at)
            VALUES (?, ?, ?)
        """, (token, user_id, expires_at))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "User registered successfully",
            "token": token,
            "user": {
                "id": user_id,
                "email": user.email,
                "name": user.name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login_user(credentials: UserLogin):
    """Login user and return session token"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, name, password_hash 
            FROM users 
            WHERE email = ?
        """, (credentials.email,))
        
        user = cursor.fetchone()
        
        if not user or not verify_password(credentials.password, user[3]):
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create new session
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=30)
        
        cursor.execute("""
            INSERT INTO sessions (token, user_id, expires_at)
            VALUES (?, ?, ?)
        """, (token, user[0], expires_at))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user[0],
                "email": user[1],
                "name": user[2]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT segments, reading_preference, language 
            FROM user_preferences 
            WHERE user_id = ?
        """, (current_user["id"],))
        
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
                "segments": [],
                "reading_preference": "short",
                "language": "en"
            }
        }
    except Exception as e:
        print(f"Get user error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logout")
def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user by invalidating session token"""
    try:
        token = credentials.credentials
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        
        return {"message": "Logged out successfully"}
    except Exception as e:
        print(f"Logout error: {e}")
        return {"message": "Logged out"}

@app.put("/preferences")
def update_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    """Update user preferences"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_preferences 
            (user_id, segments, reading_preference, language, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (
            current_user["id"],
            json.dumps(preferences.segments),
            preferences.reading_preference,
            preferences.language
        ))
        
        # Clear user's cached news when preferences change
        cursor.execute("""
            DELETE FROM user_news_cache WHERE user_id = ?
        """, (current_user["id"],))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Preferences updated successfully",
            "preferences": preferences
        }
    except Exception as e:
        print(f"Update preferences error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news-brief")
def get_news_brief(
    request: NewsBriefRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate personalized news brief for authenticated user"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get user preferences
        cursor.execute("""
            SELECT segments FROM user_preferences WHERE user_id = ?
        """, (current_user["id"],))
        
        row = cursor.fetchone()
        
        if row:
            categories = json.loads(row[0])
        else:
            categories = ["Technology", "Business"]
        
        # If specific category requested, use that
        if request.category:
            categories = [request.category]
        
        # Determine date
        target_date = request.date if request.date else datetime.now().strftime("%Y-%m-%d")
        
        # Generate briefs for each category
        briefs = []
        
        for category in categories:
            try:
                # Check user's personalized cache first (unless force_refresh)
                if not request.force_refresh:
                    cached_brief = get_user_news_cache(current_user["id"], category, target_date)
                    if cached_brief:
                        cached_brief["cached"] = True
                        briefs.append(cached_brief)
                        continue
                
                # Fetch and aggregate news
                articles = aggregate_news(category, target_date, use_cache=not request.force_refresh)
                
                # If no articles found, skip this category
                if not articles:
                    print(f"No articles found for {category}")
                    continue
                
                # Generate summaries for each article
                processed_articles = []
                for article in articles:
                    try:
                        summary = summarize_text(article.get("description", ""))
                        processed_articles.append({
                            "title": article["title"],
                            "description": article["description"],
                            "url": article["url"],
                            "source": article["source"],
                            "published_at": article["published_at"],
                            "summary": summary
                        })
                    except Exception as e:
                        print(f"Error processing article: {e}")
                        # Add article without summary
                        processed_articles.append({
                            "title": article["title"],
                            "description": article["description"],
                            "url": article["url"],
                            "source": article["source"],
                            "published_at": article["published_at"],
                            "summary": article["description"][:200]
                        })
                
                # Create consolidated summary
                consolidated = create_consolidated_summary(processed_articles, category)
                
                brief = {
                    "category": category,
                    "date": target_date,
                    "articles": processed_articles,
                    "consolidated_summary": consolidated,
                    "cached": False
                }
                
                # Cache this personalized brief
                cache_user_news(current_user["id"], category, target_date, brief)
                
                briefs.append(brief)
                
            except Exception as e:
                print(f"Error processing category {category}: {e}")
                traceback.print_exc()
                continue
        
        conn.close()
        
        return {
            "user": current_user["name"],
            "date": target_date,
            "briefs": briefs,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"News brief error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating news brief: {str(e)}")

@app.delete("/clear-cache")
def clear_cache(current_user: dict = Depends(get_current_user)):
    """Clear user's cached news"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_news_cache WHERE user_id = ?", (current_user["id"],))
        
        conn.commit()
        conn.close()
        
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        print(f"Clear cache error: {e}")
        return {"message": "Cache cleared"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "caching": "enabled",
        "ai_model": "loaded" if summarizer else "fallback mode"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
