# Quick Start Guide 🚀

Get your Daily News Brief Generator running in minutes!

## Prerequisites

Choose one of the following setups:

### Option A: Docker (Easiest)
- Docker Desktop installed
- Docker Compose installed

### Option B: Local Development
- Python 3.11+
- Node.js 16+
- npm or yarn

## Quick Start - Docker (Recommended)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd news-brief-generator

# 2. Create environment file (optional)
cp backend/.env.example backend/.env
# Edit backend/.env to add your API keys (optional)

# 3. Start with Docker Compose
docker-compose up

# 4. Access the application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

That's it! The app is now running.

## Quick Start - Local Development

### Terminal 1: Backend

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (optional)
cp .env.example .env
# Edit .env to add API keys if you have them

# Run backend
python main.py

# Backend running on http://localhost:8000
```

### Terminal 2: Frontend

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Default API URL is http://localhost:8000

# Run frontend
npm start

# Frontend running on http://localhost:3000
```

## First Time Usage

1. **Open your browser**: Navigate to http://localhost:3000

2. **Welcome Screen**: You'll see the preferences setup

3. **Select Categories**: 
   - Click on your preferred news segments
   - Examples: Technology, Business, Sports

4. **Choose Reading Preference**:
   - Short: Quick summaries
   - Detailed: More comprehensive summaries

5. **Save Preferences**: Click "Save Preferences"

6. **View Your Brief**: Your personalized news brief will load automatically!

## Using the App

### Home Page
- View your personalized news briefs
- Each category shows top stories with AI-generated summaries
- Click "Read More" to view full articles

### Change Date
- Use the date picker in the header
- View news from past dates
- Limited by news source availability

### Filter Categories
- Click category chips to filter
- View one category at a time
- Click "All Categories" to reset

### Update Preferences
- Click the settings icon (⚙️)
- Modify your preferences
- Save and see updated briefs

### Refresh
- Click the refresh icon (🔄)
- Get the latest news updates

## API Keys (Optional)

The app works with RSS feeds without API keys, but you can get better coverage with:

### NewsAPI (Free Tier)
1. Visit https://newsapi.org/register
2. Sign up for free account
3. Copy your API key
4. Add to `backend/.env`:
   ```
   NEWS_API_KEY=your_key_here
   ```

### GNews (Free Tier)
1. Visit https://gnews.io/register
2. Sign up for free account
3. Copy your API key
4. Add to `backend/.env`:
   ```
   GNEWS_API_KEY=your_key_here
   ```

### Free Tier Limits
- NewsAPI: 100 requests/day
- GNews: 100 requests/day
- RSS Feeds: Unlimited

## Troubleshooting

### Backend won't start

**Issue**: Missing dependencies
```bash
pip install -r requirements.txt
```

**Issue**: Port 8000 already in use
```bash
# Find and kill the process
# On macOS/Linux:
lsof -ti:8000 | xargs kill -9
# On Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Frontend won't start

**Issue**: Port 3000 already in use
```bash
# Kill process on port 3000
# On macOS/Linux:
lsof -ti:3000 | xargs kill -9
# On Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**Issue**: Dependencies not installed
```bash
rm -rf node_modules package-lock.json
npm install
```

### No news appearing

**Issue**: API rate limits exceeded
- Wait for rate limit reset (24 hours)
- RSS feeds will still work

**Issue**: Network connectivity
- Check internet connection
- Try refreshing the page
- Check backend logs for errors

### Backend logs showing errors

**Issue**: HuggingFace model download
```bash
# Pre-download the model
python -c "from transformers import pipeline; pipeline('summarization', model='facebook/bart-large-cnn')"
```

## Testing the API

### Using curl

```bash
# Test health
curl http://localhost:8000/health

# Get categories
curl http://localhost:8000/categories

# Save preferences
curl -X POST http://localhost:8000/preferences \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","segments":["Technology","Business"]}'

# Get news brief
curl -X POST http://localhost:8000/news-brief \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test"}'
```

### Using API Documentation

Visit http://localhost:8000/docs for interactive API documentation with Swagger UI.

## Development Tips

### Backend Hot Reload
The backend automatically reloads when you make changes to Python files.

### Frontend Hot Reload
The frontend automatically reloads when you make changes to React files.

### View Logs
- **Backend**: Check terminal running `python main.py`
- **Frontend**: Check terminal running `npm start`
- **Browser**: Open browser DevTools (F12)

### Debug Mode
```bash
# Backend with debug logging
python main.py --log-level debug

# Frontend with debug info
REACT_APP_DEBUG=true npm start
```

## Stopping the Application

### Docker
```bash
# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Local Development
- Press `Ctrl+C` in both terminal windows

## Next Steps

1. ✅ App is running
2. 📝 Check out the full [README.md](README.md) for detailed info
3. 🚀 Read [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions
4. 🏗️ Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
5. 🎨 Customize the app to your needs
6. 🌐 Deploy to production!

## Getting Help

- Check the logs for errors
- Review the README for detailed documentation
- Open an issue on GitHub
- Check API documentation at /docs

## Common Questions

**Q: Do I need API keys?**
A: No, the app works with RSS feeds. API keys provide more coverage.

**Q: How many categories can I select?**
A: All 6 if you want! Technology, Business, Sports, Health, Entertainment, Politics.

**Q: Can I view past news?**
A: Yes, use the date picker. Availability depends on news sources.

**Q: Is my data saved?**
A: Yes, preferences are saved locally in SQLite database.

**Q: Can I use this commercially?**
A: Check the licenses of the news APIs you use. RSS feeds have their own terms.

---

**Enjoy your personalized news experience! 📰**
