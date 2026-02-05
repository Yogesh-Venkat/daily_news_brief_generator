import sqlite3
import json
from datetime import datetime

DB_PATH = "news_brief_01.db"

def check_database():
    """Inspect database contents"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("="*80)
    print("DATABASE INSPECTION")
    print("="*80)
    
    # 1. Check all cache entries
    print("\n1. ALL CACHED NEWS ENTRIES:")
    print("-"*80)
    cursor.execute("""
        SELECT category, date, articles,
               datetime(created_at, 'localtime') as created,
               datetime(expires_at, 'localtime') as expires
        FROM cached_news 
        ORDER BY date DESC, category
    """)
    
    for row in cursor.fetchall():
        # FIX: Count articles in Python, not SQL
        articles = json.loads(row[2])
        article_count = len(articles)
        
        print(f"Category: {row[0]}")
        print(f"  Date: {row[1]}")
        print(f"  Articles: {article_count}")
        print(f"  Created: {row[3]}")
        print(f"  Expires: {row[4]}")
        print()
    
    # 2. Check articles for specific dates
    print("\n2. ARTICLES BY DATE:")
    print("-"*80)
    
    dates = ['2026-02-05', '2026-02-04', '2026-02-02']
    
    for date in dates:
        print(f"\n📅 DATE: {date}")
        cursor.execute("""
            SELECT category, articles 
            FROM cached_news 
            WHERE date = ?
        """, (date,))
        
        for row in cursor.fetchall():
            articles = json.loads(row['articles'])
            print(f"  {row['category']}: {len(articles)} articles")
            
            if articles:
                print(f"    First article: {articles[0]['title'][:60]}...")
                print(f"    Published: {articles[0].get('published_at', 'N/A')}")
    
    # 3. Check if articles are actually different
    print("\n3. UNIQUENESS CHECK:")
    print("-"*80)
    
    cursor.execute("""
        SELECT date, category, articles 
        FROM cached_news 
        WHERE category = 'Technology'
        ORDER BY date DESC
    """)
    
    all_tech_articles = {}
    for row in cursor.fetchall():
        articles = json.loads(row['articles'])
        titles = [a['title'] for a in articles[:3]]
        all_tech_articles[row['date']] = titles
    
    for date, titles in all_tech_articles.items():
        print(f"\n{date} - Technology Top 3:")
        for i, title in enumerate(titles, 1):
            print(f"  {i}. {title[:70]}")
    
    # 4. Check user cache
    print("\n4. USER CACHE:")
    print("-"*80)
    cursor.execute("""
        SELECT user_id, category, date, 
               datetime(created_at, 'localtime') as created
        FROM user_news_cache
        ORDER BY created_at DESC
    """)
    
    for row in cursor.fetchall():
        print(f"User {row['user_id']}: {row['category']} on {row['date']} (cached: {row['created']})")
    
    conn.close()

if __name__ == "__main__":
    check_database()
