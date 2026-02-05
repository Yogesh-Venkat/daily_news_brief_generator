import sqlite3
import requests
import feedparser
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
import time

load_dotenv()

DB_PATH = "news_brief_01.db"
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


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with all required tables"""
    print("\n🔧 Initializing database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_date ON cached_news(date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_news_category_date ON cached_news(category, date DESC)")

    conn.commit()
    conn.close()
    print("  ✅ Database initialized!\n")


def fetch_from_newsapi(category: str, date: str) -> list:
    """Fetch news from NewsAPI for a specific date"""
    if not NEWS_API_KEY:
        print(f"  ⚠️  NewsAPI key not found")
        return []

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": NEWS_API_KEY,
            "q": category.lower(),
            "from": date,
            "to": date,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 20
        }

        response = requests.get(url, params=params, timeout=15)

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
                        "published_at": article.get("publishedAt", "")
                    })

            print(f"  ✓ NewsAPI: {len(articles)} articles")
            return articles
        elif response.status_code == 426:
            print(f"  ⚠️  NewsAPI: Upgrade required for historical data")
        elif response.status_code == 429:
            print(f"  ⚠️  NewsAPI: Rate limit exceeded")
        else:
            print(f"  ⚠️  NewsAPI: Status {response.status_code}")

    except Exception as e:
        print(f"  ⚠️  NewsAPI error: {str(e)}")

    return []


def fetch_from_gnews(category: str, date: str) -> list:
    """Fetch news from GNews for a specific date"""
    if not GNEWS_API_KEY:
        print(f"  ⚠️  GNews key not found")
        return []

    try:
        url = "https://gnews.io/api/v4/search"
        params = {
            "apikey": GNEWS_API_KEY,
            "q": category.lower(),
            "lang": "en",
            "max": 20,
            "from": f"{date}T00:00:00Z",
            "to": f"{date}T23:59:59Z"
        }

        response = requests.get(url, params=params, timeout=15)

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
                        "published_at": article.get("publishedAt", "")
                    })

            print(f"  ✓ GNews: {len(articles)} articles")
            return articles
        else:
            print(f"  ⚠️  GNews: Status {response.status_code}")

    except Exception as e:
        print(f"  ⚠️  GNews error: {str(e)}")

    return []


def fetch_from_rss(category: str) -> list:
    """Fetch news from RSS feeds"""
    articles = []

    for feed_url in RSS_FEEDS.get(category, []):
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:10]:
                articles.append({
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", entry.get("description", "No description")),
                    "url": entry.get("link", ""),
                    "source": feed.feed.get("title", "RSS Feed"),
                    "published_at": entry.get("published", "")
                })
        except Exception as e:
            print(f"  ⚠️  RSS error: {str(e)}")

    if articles:
        print(f"  ✓ RSS: {len(articles)} articles")
    return articles


def aggregate_and_deduplicate(all_articles: list) -> list:
    """Remove duplicate articles based on title similarity"""
    unique_articles = []
    seen_titles = set()

    for article in all_articles:
        title_key = article["title"].lower()[:60]

        if title_key not in seen_titles and title_key.strip():
            seen_titles.add(title_key)
            unique_articles.append(article)

    return unique_articles


def bulk_insert_articles(category: str, date: str, articles: list):
    """Bulk insert articles into database with optimization"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        expires_at = datetime.now() + timedelta(days=365)

        cursor.execute(
            """INSERT OR REPLACE INTO cached_news 
               (category, date, articles, expires_at, created_at) 
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (category, date, json.dumps(articles), expires_at)
        )

        conn.commit()
        print(f"  💾 Saved {len(articles)} articles to database")

    except Exception as e:
        print(f"  ❌ Database error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def seed_specific_dates(start_date_str: str, end_date_str: str, categories: list = None):
    """
    Seed news data for a specific date range

    Args:
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
        categories: List of categories to fetch (default: all)
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        return

    if start_date > end_date:
        print("❌ Start date must be before or equal to end date")
        return

    if categories is None:
        categories = list(CATEGORY_MAPPING.keys())

    print(f"\n{'='*60}")
    print(f"📰 Targeted News Data Seeding")
    print(f"{'='*60}\n")
    print(f"Date Range: {start_date_str} to {end_date_str}")
    print(f"Categories: {', '.join(categories)}\n")

    total_articles = 0
    successful_days = 0
    failed_days = 0

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        days_ago = (datetime.now() - current_date).days

        print(f"\n📅 Date: {date_str} ({days_ago} days ago)")
        print("-" * 60)

        day_articles = 0

        for category in categories:
            print(f"\n📂 Category: {category}")

            all_articles = []

            all_articles.extend(fetch_from_newsapi(category, date_str))
            time.sleep(1)

            all_articles.extend(fetch_from_gnews(category, date_str))
            time.sleep(1)

            # RSS only for recent dates (last 2 days)
            if days_ago <= 2:
                all_articles.extend(fetch_from_rss(category))

            unique_articles = aggregate_and_deduplicate(all_articles)
            final_articles = unique_articles[:15]

            if final_articles:
                bulk_insert_articles(category, date_str, final_articles)
                day_articles += len(final_articles)
                total_articles += len(final_articles)
            else:
                print(f"  ⚠️  No articles found")
                bulk_insert_articles(category, date_str, [])

            time.sleep(2)

        if day_articles > 0:
            successful_days += 1
            print(f"\n✅ Day total: {day_articles} articles")
        else:
            failed_days += 1
            print(f"\n⚠️  No articles for this day")

        current_date += timedelta(days=1)

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SEEDING SUMMARY")
    print(f"{'='*60}")
    print(f"✓ Total articles saved: {total_articles}")
    print(f"✓ Successful days: {successful_days}")
    print(f"⚠ Days with no data: {failed_days}")
    print(f"\n✅ Targeted seeding completed!\n")


def seed_historical_data(days_back: int = 14):
    """Seed historical news data for the past N days"""
    print(f"\n{'='*60}")
    print(f"📰 Historical News Data Seeding")
    print(f"{'='*60}\n")
    print(f"Fetching news for the past {days_back} days...")
    print(f"Categories: {', '.join(CATEGORY_MAPPING.keys())}\n")

    categories = list(CATEGORY_MAPPING.keys())
    today = datetime.now()

    total_articles = 0
    successful_days = 0
    failed_days = 0

    for day_offset in range(days_back):
        target_date = today - timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")

        print(f"\n📅 Date: {date_str} ({day_offset} days ago)")
        print("-" * 60)

        day_articles = 0

        for category in categories:
            print(f"\n📂 Category: {category}")

            all_articles = []

            all_articles.extend(fetch_from_newsapi(category, date_str))
            time.sleep(1)

            all_articles.extend(fetch_from_gnews(category, date_str))
            time.sleep(1)

            if day_offset <= 2:
                all_articles.extend(fetch_from_rss(category))

            unique_articles = aggregate_and_deduplicate(all_articles)
            final_articles = unique_articles[:15]

            if final_articles:
                bulk_insert_articles(category, date_str, final_articles)
                day_articles += len(final_articles)
                total_articles += len(final_articles)
            else:
                print(f"  ⚠️  No articles found")
                bulk_insert_articles(category, date_str, [])

            time.sleep(2)

        if day_articles > 0:
            successful_days += 1
            print(f"\n✅ Day total: {day_articles} articles")
        else:
            failed_days += 1
            print(f"\n⚠️  No articles for this day")

    print(f"\n{'='*60}")
    print(f"📊 SEEDING SUMMARY")
    print(f"{'='*60}")
    print(f"✓ Total articles saved: {total_articles}")
    print(f"✓ Successful days: {successful_days}/{days_back}")
    print(f"⚠ Days with no data: {failed_days}/{days_back}")
    print(f"\n✅ Historical data seeding completed!\n")


def verify_seeded_data():
    """Verify what data has been seeded"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category, date, json_array_length(articles) as count
        FROM cached_news
        ORDER BY date DESC, category
    """)

    results = cursor.fetchall()

    print(f"\n{'='*60}")
    print(f"📊 STORED DATA VERIFICATION")
    print(f"{'='*60}\n")

    if results:
        print(f"{'Date':<12} {'Category':<15} {'Articles':<10}")
        print("-" * 60)
        for row in results:
            print(f"{row[1]:<12} {row[0]:<15} {row[2]:<10}")
        print(f"\nTotal records: {len(results)}")
    else:
        print("No data found in database")

    conn.close()


def find_missing_dates():
    """Find dates with missing or incomplete data"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, 
               COUNT(DISTINCT category) as categories_count,
               SUM(json_array_length(articles)) as total_articles
        FROM cached_news
        GROUP BY date
        ORDER BY date DESC
    """)

    results = cursor.fetchall()

    print(f"\n{'='*60}")
    print(f"🔍 DATA GAP ANALYSIS")
    print(f"{'='*60}\n")

    missing_dates = []
    incomplete_dates = []

    expected_categories = len(CATEGORY_MAPPING)

    for row in results:
        date, cat_count, article_count = row[0], row[1], row[2]

        if cat_count < expected_categories:
            incomplete_dates.append((date, cat_count, article_count))
        elif article_count == 0:
            missing_dates.append(date)

    if missing_dates:
        print("📋 Dates with NO data:")
        for date in missing_dates:
            print(f"  ❌ {date}")

    if incomplete_dates:
        print(f"\n📋 Dates with INCOMPLETE data:")
        print(f"{'Date':<12} {'Categories':<12} {'Articles':<10}")
        print("-" * 40)
        for date, cat_count, article_count in incomplete_dates:
            print(f"{date:<12} {cat_count}/{expected_categories:<10} {article_count:<10}")

    if not missing_dates and not incomplete_dates:
        print("✅ All dates have complete data!")

    conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed historical news data")
    parser.add_argument("--days", type=int, help="Number of days to go back from today")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--categories", type=str, nargs='+', help="Specific categories to fetch")
    parser.add_argument("--verify", action="store_true", help="Verify seeded data")
    parser.add_argument("--find-gaps", action="store_true", help="Find missing/incomplete dates")
    parser.add_argument("--init-only", action="store_true", help="Only initialize database")

    args = parser.parse_args()

    # Always initialize DB first
    init_db()

    if args.init_only:
        print("\n✅ Database initialization complete!")
    elif args.verify:
        verify_seeded_data()
    elif args.find_gaps:
        find_missing_dates()
    elif args.start_date and args.end_date:
        # Specific date range
        seed_specific_dates(args.start_date, args.end_date, args.categories)
        verify_seeded_data()
    elif args.days:
        # Days back from today
        seed_historical_data(days_back=args.days)
        verify_seeded_data()
    else:
        # Default: 14 days
        seed_historical_data(days_back=14)
        verify_seeded_data()
