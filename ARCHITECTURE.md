# Technical Architecture Documentation

## System Overview

The Daily News Brief Generator is a full-stack web application that aggregates news from multiple sources, uses AI to generate summaries, and delivers personalized news briefs to users based on their preferences.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Settings  │  │  Home Page   │  │  News Briefs    │   │
│  │  Component │  │  Component   │  │  Component      │   │
│  └────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/REST API
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │              API Endpoints                          │    │
│  │  /preferences  /news-brief  /categories  /health   │    │
│  └─────────────┬──────────────────────┬────────────────┘    │
│                ↓                      ↓                     │
│  ┌─────────────────────┐   ┌──────────────────────┐       │
│  │  Preference Manager │   │  News Aggregator     │       │
│  └──────────┬──────────┘   └──────────┬───────────┘       │
│             ↓                          ↓                    │
│  ┌─────────────────────┐   ┌──────────────────────┐       │
│  │  SQLite Database    │   │  AI Summarizer       │       │
│  │  (User Preferences) │   │  (HuggingFace)       │       │
│  └─────────────────────┘   └──────────┬───────────┘       │
│                                        ↓                    │
│                          ┌────────────────────────┐        │
│                          │  News Sources          │        │
│                          │  - NewsAPI             │        │
│                          │  - GNews               │        │
│                          │  - RSS Feeds           │        │
│                          └────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend

#### FastAPI Framework
- **Purpose**: REST API server
- **Why**: 
  - High performance (async support)
  - Automatic API documentation
  - Easy to deploy
  - Type safety with Pydantic

#### SQLite Database
- **Purpose**: Store user preferences
- **Schema**:
  ```sql
  CREATE TABLE user_preferences (
      user_id TEXT PRIMARY KEY,
      segments TEXT,  -- JSON array
      reading_preference TEXT DEFAULT 'short',
      language TEXT DEFAULT 'en',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )
  
  CREATE TABLE cached_news (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      category TEXT,
      date TEXT,
      articles TEXT,  -- JSON array
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )
  ```

#### HuggingFace Transformers
- **Model**: facebook/bart-large-cnn
- **Purpose**: Text summarization
- **Why**: 
  - State-of-the-art summarization
  - Free to use
  - Works offline after download

#### News Sources
1. **NewsAPI** (Optional)
   - 100 free requests/day
   - Multiple categories
   - Real-time news
   
2. **GNews** (Optional)
   - 100 free requests/day
   - International coverage
   - Reliable data
   
3. **RSS Feeds** (Always Available)
   - BBC News feeds
   - Wired, others
   - No API key required

### Frontend

#### React 18
- **Purpose**: User interface
- **Architecture**: 
  - Functional components
  - React Hooks (useState, useEffect)
  - Single Page Application (SPA)

#### Key Components
1. **App Component**: Main application container
2. **Settings Modal**: User preference management
3. **News Brief Cards**: Display categorized news
4. **Article Cards**: Individual article display

#### State Management
- React useState for local state
- No global state library needed
- API calls managed with useEffect

#### Styling
- Custom CSS (no framework)
- Responsive design (mobile-first)
- Modern gradient backgrounds
- Smooth transitions

## Data Flow

### 1. User Preference Flow

```
User selects preferences
        ↓
Frontend sends POST to /preferences
        ↓
Backend validates with Pydantic
        ↓
Saves to SQLite database
        ↓
Returns success response
        ↓
Frontend updates UI
```

### 2. News Fetching Flow

```
User requests news brief
        ↓
Frontend sends POST to /news-brief
        ↓
Backend retrieves user preferences
        ↓
For each preferred category:
    ├→ Fetch from NewsAPI
    ├→ Fetch from GNews
    └→ Fetch from RSS feeds
        ↓
Aggregate and deduplicate articles
        ↓
For each article:
    └→ Generate AI summary
        ↓
Create consolidated brief
        ↓
Return JSON response
        ↓
Frontend renders briefs
```

### 3. Duplicate Handling

```python
def remove_duplicates(articles):
    """Remove duplicate articles based on title similarity"""
    unique = []
    seen_titles = set()
    
    for article in articles:
        # Use first 50 chars of title for comparison
        title_key = article['title'].lower()[:50]
        
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(article)
    
    return unique
```

## Personalization Logic

### Preference Storage
```python
{
    "user_id": "default_user",
    "segments": ["Technology", "Business", "Sports"],
    "reading_preference": "short",
    "language": "en"
}
```

### News Brief Generation
1. **Category Selection**: Use user's preferred segments
2. **Source Aggregation**: Fetch from multiple sources
3. **Deduplication**: Remove similar articles
4. **Prioritization**: Rank by recency and source reliability
5. **Summarization**: Generate concise summaries
6. **Consolidation**: Create category-wise briefs

### AI Summarization Strategy

```python
def summarize_text(text: str, max_length: int = 130) -> str:
    """
    Two-tier summarization:
    1. Try AI model (HuggingFace BART)
    2. Fallback to extractive (first 2 sentences)
    """
    try:
        if ai_model_available:
            return model.summarize(text, max_length)
        else:
            sentences = text.split('. ')
            return '. '.join(sentences[:2]) + '.'
    except Exception:
        # Extractive fallback
        return extract_key_sentences(text)
```

## API Endpoints

### GET /categories
**Purpose**: Get available news categories

**Response**:
```json
{
  "categories": [
    "Technology",
    "Business",
    "Sports",
    "Health",
    "Entertainment",
    "Politics"
  ]
}
```

### POST /preferences
**Purpose**: Save user preferences

**Request**:
```json
{
  "user_id": "default_user",
  "segments": ["Technology", "Business"],
  "reading_preference": "short",
  "language": "en"
}
```

**Response**:
```json
{
  "message": "Preferences saved successfully",
  "preferences": { ... }
}
```

### GET /preferences/{user_id}
**Purpose**: Retrieve user preferences

**Response**:
```json
{
  "user_id": "default_user",
  "segments": ["Technology", "Business"],
  "reading_preference": "short",
  "language": "en"
}
```

### POST /news-brief
**Purpose**: Generate personalized news brief

**Request**:
```json
{
  "user_id": "default_user",
  "category": "Technology",  // optional
  "date": "2024-01-01"       // optional
}
```

**Response**:
```json
{
  "user_id": "default_user",
  "date": "2024-01-01",
  "briefs": [
    {
      "category": "Technology",
      "date": "2024-01-01",
      "articles": [
        {
          "title": "Article Title",
          "description": "Full description",
          "url": "https://...",
          "source": "BBC",
          "published_at": "2024-01-01T10:00:00",
          "summary": "AI-generated summary"
        }
      ],
      "consolidated_summary": "Technology Highlights:\n\n• Point 1\n• Point 2"
    }
  ],
  "generated_at": "2024-01-01T12:00:00"
}
```

## Security Considerations

### API Keys
- Stored in environment variables
- Never committed to repository
- Separated per environment (dev/prod)

### CORS Policy
```python
allow_origins=["*"]  # Development
# Production: specify exact frontend URL
allow_origins=["https://your-frontend.com"]
```

### Input Validation
- Pydantic models for request validation
- SQL injection prevention (parameterized queries)
- XSS prevention (React escapes by default)

### Rate Limiting
- Not implemented (can add with slowapi)
- API providers have their own limits
- Recommended for production

## Performance Optimization

### Backend
1. **Model Caching**: HuggingFace model loads once
2. **Database Indexing**: User_id primary key
3. **Async Operations**: FastAPI async support
4. **Connection Pooling**: SQLite connection reuse

### Frontend
1. **React Optimization**: 
   - Functional components (faster)
   - Conditional rendering
   - Minimal re-renders
2. **Asset Optimization**:
   - Lazy loading (can implement)
   - Code splitting (can implement)
3. **Caching**:
   - Browser caching
   - API response caching

### News Aggregation
```python
# Parallel fetching (can implement)
import asyncio

async def fetch_all_sources(category):
    tasks = [
        fetch_newsapi(category),
        fetch_gnews(category),
        fetch_rss(category)
    ]
    results = await asyncio.gather(*tasks)
    return aggregate(results)
```

## Error Handling

### Backend
```python
try:
    result = fetch_news()
except APIException:
    # Fallback to RSS
    result = fetch_rss()
except Exception as e:
    logger.error(f"Error: {e}")
    raise HTTPException(500, detail="Service unavailable")
```

### Frontend
```javascript
try {
  const response = await axios.post('/news-brief', data);
  setNewsBriefs(response.data.briefs);
} catch (error) {
  console.error('Error:', error);
  setNewsBriefs([]);
  // Show user-friendly error message
}
```

## Database Schema Design

### User Preferences Table
- **user_id**: Primary key, identifies user
- **segments**: JSON array of preferred categories
- **reading_preference**: Short or detailed summaries
- **language**: Preferred language (future use)
- **created_at**: Timestamp for tracking

### Cached News Table (Optional Enhancement)
- **id**: Auto-increment primary key
- **category**: News category
- **date**: Date of news
- **articles**: JSON array of articles
- **created_at**: Cache timestamp

## Testing Strategy

### Backend Testing
```python
# Unit tests
def test_summarization():
    text = "Long article text..."
    summary = summarize_text(text)
    assert len(summary) < len(text)

# Integration tests
def test_news_aggregation():
    articles = aggregate_news("Technology")
    assert len(articles) > 0
    assert no_duplicates(articles)
```

### Frontend Testing
```javascript
// Component tests
test('renders settings modal', () => {
  render(<App />);
  expect(screen.getByText('Welcome')).toBeInTheDocument();
});

// API integration tests
test('fetches news brief', async () => {
  const brief = await fetchNewsBrief();
  expect(brief.briefs).toBeDefined();
});
```

## Deployment Architecture

### Development
```
Local Backend (localhost:8000)
    ↓
Local Frontend (localhost:3000)
```

### Production
```
Backend (Render)
    ↓
Frontend (Vercel/Netlify)
    ↓
Users (Global CDN)
```

## Scalability Considerations

### Current Limitations
- Single server backend
- SQLite database (file-based)
- No caching layer
- Sequential news fetching

### Scaling Path
1. **Phase 1**: Add Redis caching
2. **Phase 2**: Move to PostgreSQL
3. **Phase 3**: Implement CDN
4. **Phase 4**: Microservices architecture
5. **Phase 5**: Kubernetes deployment

### Estimated Capacity
- **Current**: ~100 concurrent users
- **With optimization**: ~1,000 concurrent users
- **With scaling**: 10,000+ concurrent users

## Monitoring & Logging

### Backend Logs
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Fetching news for {category}")
logger.error(f"API error: {error}")
```

### Frontend Analytics
- User interactions
- Page views
- Error tracking
- Performance metrics

## Future Enhancements

### Technical
1. **User Authentication**: JWT tokens, OAuth
2. **Real-time Updates**: WebSockets
3. **Advanced Caching**: Redis integration
4. **Microservices**: Separate summarization service
5. **GraphQL API**: More flexible queries

### Features
1. **Email Notifications**: Daily digest emails
2. **Mobile App**: React Native
3. **Social Sharing**: Share briefs
4. **Bookmarking**: Save articles
5. **Multi-language**: i18n support

## Code Quality

### Backend Standards
- PEP 8 style guide
- Type hints throughout
- Docstrings for functions
- Error handling

### Frontend Standards
- ESLint configuration
- Component documentation
- PropTypes validation
- Consistent naming

## Conclusion

This architecture provides:
- **Modularity**: Easy to modify components
- **Scalability**: Can grow with demand
- **Reliability**: Multiple fallbacks
- **Performance**: Optimized for speed
- **Maintainability**: Clean, documented code

The system is production-ready and can handle hundreds of users with the free tier infrastructure.
