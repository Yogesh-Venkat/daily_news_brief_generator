# Quick Fix for 500 Internal Server Error

## Problem
The backend is returning 500 errors when fetching news. This is likely due to:
1. AI model loading issues
2. News fetching errors
3. Missing error handling

## Solution

### Option 1: Replace with Fixed Version (Recommended)

```bash
# Stop your containers
docker-compose down

# Replace the main.py file
cd backend
cp main_v2_fixed.py main.py

# Restart
cd ..
docker-compose up
```

### Option 2: Manual Fix

If you're not using Docker, just replace the file:

```bash
cd backend
cp main_v2_fixed.py main.py
python main.py
```

## What Was Fixed

### 1. Better Error Handling
- Added try-catch blocks around all critical operations
- Each category is processed independently (one failure doesn't stop others)
- Graceful fallbacks for all operations

### 2. AI Model Made Optional
- App works without AI model
- Uses simple extractive summaries as fallback
- No crashes if model fails to load

### 3. Improved News Fetching
- Better error handling for each news source
- Continue if one source fails
- Always returns results if any source succeeds

### 4. Enhanced Logging
- Prints detailed error messages
- Shows which operations are failing
- Helps with debugging

## Test After Fix

1. **Stop Docker**:
```bash
docker-compose down
```

2. **Update backend file**:
```bash
cd backend
mv main.py main_old.py  # backup
cp main_v2_fixed.py main.py
```

3. **Restart**:
```bash
cd ..
docker-compose up
```

4. **Test in browser**:
- Register new user
- Select categories
- Try to view news
- Should work now!

## If Still Not Working

### Check Logs
Look for specific errors in the Docker logs:
```bash
docker-compose logs backend
```

### Common Issues & Solutions

**Issue**: "No articles found"
```bash
# Check your API keys are set
echo $NEWS_API_KEY
echo $GNEWS_API_KEY

# If not set, add them:
cd backend
echo "NEWS_API_KEY=52f70f3076244e6a9163397bf9ae0f44" >> .env
echo "GNEWS_API_KEY=6370bf4bfcd9634c134fcd949ca2395d" >> .env
```

**Issue**: "AI model error"
```bash
# The fixed version works without AI model
# It will use simple summaries instead
# This is normal and expected
```

**Issue**: "RSS feed timeout"
```bash
# This is normal - RSS feeds can be slow
# The app will continue with other sources
```

### Manual Test

Test the backend directly:

```bash
# 1. Register a user
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@test.com",
    "password": "test123",
    "name": "Test",
    "segments": ["Technology"]
  }'

# Save the token from response

# 2. Get news (replace YOUR_TOKEN)
curl -X POST http://localhost:8000/news-brief \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## What to Expect

### Without AI Model (Normal)
```
INFO: AI model not available (using fallback)
Fetching fresh news for Technology
```

This is fine! The app will use simple summaries.

### With Working News
```
INFO: Using cached news for Technology
```
or
```
Fetching fresh news for Technology
```

### Success Response
You should see news articles in the response with:
- Titles
- Descriptions
- URLs
- Sources
- Summaries

## Still Having Issues?

1. **Check Environment Variables**:
```bash
cd backend
cat .env
```

Should see:
```
NEWS_API_KEY=52f70f3076244e6a9163397bf9ae0f44
GNEWS_API_KEY=6370bf4bfcd9634c134fcd949ca2395d
```

2. **Delete Database and Restart**:
```bash
cd backend
rm news_brief.db
cd ..
docker-compose down
docker-compose up
```

3. **Check Network**:
```bash
# Test if backend can reach news APIs
curl "https://newsapi.org/v2/top-headlines?apiKey=52f70f3076244e6a9163397bf9ae0f44&category=technology"
```

## Alternative: Use Version 1

If all else fails, use the simpler Version 1:

```bash
cd backend
cp main.py main_v2_backup.py
# Use original main.py from the package

cd ../frontend/src
cp App.js App_v2_backup.js
# Use original App.js
```

Version 1 doesn't have authentication but should work reliably.

## Summary

The fixed version (`main_v2_fixed.py`) includes:
- ✅ Comprehensive error handling
- ✅ Works without AI model
- ✅ Continues if news sources fail
- ✅ Better logging
- ✅ Graceful degradation

Just replace `main.py` with `main_v2_fixed.py` and restart!
