# Deployment Guide 🚀

This guide provides step-by-step instructions for deploying the Daily News Brief Generator application.

## Table of Contents
1. [Quick Deployment (Recommended)](#quick-deployment-recommended)
2. [Backend Deployment](#backend-deployment)
3. [Frontend Deployment](#frontend-deployment)
4. [Environment Variables](#environment-variables)
5. [Testing Deployment](#testing-deployment)

## Quick Deployment (Recommended)

### Option 1: Render + Vercel (Easiest)

**Time: ~15 minutes**

#### Backend on Render
1. Push code to GitHub
2. Go to https://render.com
3. Click "New +" → "Web Service"
4. Connect GitHub repository
5. Select `backend` folder
6. Configure:
   - Name: `news-brief-backend`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Add environment variables (optional):
   - `NEWS_API_KEY`
   - `GNEWS_API_KEY`
8. Click "Create Web Service"
9. Wait for deployment (~5 minutes)
10. Copy your backend URL (e.g., `https://news-brief-backend.onrender.com`)

#### Frontend on Vercel
1. Go to https://vercel.com
2. Click "New Project"
3. Import your GitHub repository
4. Configure:
   - Framework Preset: `Create React App`
   - Root Directory: `frontend`
5. Add environment variable:
   - Name: `REACT_APP_API_URL`
   - Value: Your backend URL from Render
6. Click "Deploy"
7. Wait for deployment (~3 minutes)
8. Visit your deployed app!

### Option 2: Netlify (Alternative)

**Frontend on Netlify**
1. Go to https://netlify.com
2. Click "Add new site" → "Import existing project"
3. Connect GitHub repository
4. Configure:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/build`
5. Add environment variable:
   - Key: `REACT_APP_API_URL`
   - Value: Your backend URL
6. Click "Deploy"

## Backend Deployment

### Render.com (Free Tier Available)

**Prerequisites:**
- GitHub account
- Render account (free)

**Steps:**

1. **Prepare Repository**
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

2. **Create Web Service on Render**
   - Dashboard → New → Web Service
   - Connect GitHub repository
   - Name: `news-brief-backend`
   - Region: Choose closest to your users
   - Branch: `main`
   - Root Directory: `backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Configure Environment Variables**
   - Navigate to Environment tab
   - Add variables:
     ```
     NEWS_API_KEY=your_key_here
     GNEWS_API_KEY=your_key_here
     ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete (~5-10 minutes on first deploy)
   - Note your service URL

**Free Tier Limitations:**
- Spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- 750 hours/month of runtime

### Railway.app (Alternative)

**Steps:**
1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Select your repository
5. Configure:
   - Root directory: `backend`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables
7. Deploy

### Heroku (Classic Option)

**Prerequisites:**
- Heroku CLI installed
- Heroku account

**Steps:**
```bash
cd backend

# Login to Heroku
heroku login

# Create app
heroku create news-brief-backend

# Set environment variables
heroku config:set NEWS_API_KEY=your_key
heroku config:set GNEWS_API_KEY=your_key

# Deploy
git push heroku main
```

### Docker Deployment (Any Platform)

**Build and Run:**
```bash
cd backend

# Build image
docker build -t news-brief-backend .

# Run container
docker run -d -p 8000:8000 \
  -e NEWS_API_KEY=your_key \
  -e GNEWS_API_KEY=your_key \
  --name news-brief-backend \
  news-brief-backend

# Push to Docker Hub (optional)
docker tag news-brief-backend yourusername/news-brief-backend
docker push yourusername/news-brief-backend
```

## Frontend Deployment

### Vercel (Recommended)

**Method 1: Vercel CLI**
```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to frontend
cd frontend

# Create .env.production
echo "REACT_APP_API_URL=https://your-backend-url.com" > .env.production

# Deploy
vercel

# Follow prompts
# Select 'frontend' as root directory
# Framework: Create React App
# Build command: npm run build
# Output directory: build

# Deploy to production
vercel --prod
```

**Method 2: Vercel Web UI**
1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Configure:
   - Framework Preset: `Create React App`
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `build`
4. Environment Variables:
   - `REACT_APP_API_URL`: Your backend URL
5. Deploy

### Netlify

**Method 1: Netlify CLI**
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Navigate to frontend
cd frontend

# Build
npm run build

# Deploy
netlify deploy

# For production
netlify deploy --prod
```

**Method 2: Netlify Web UI**
1. Go to https://app.netlify.com
2. "Add new site" → "Import existing project"
3. Connect GitHub
4. Configure:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/build`
5. Environment variables:
   - `REACT_APP_API_URL`: Your backend URL
6. Deploy

### GitHub Pages (Static Hosting)

**Steps:**
```bash
cd frontend

# Install gh-pages
npm install --save-dev gh-pages

# Add to package.json:
# "homepage": "https://yourusername.github.io/news-brief-generator"
# "predeploy": "npm run build"
# "deploy": "gh-pages -d build"

# Deploy
npm run deploy
```

## Environment Variables

### Backend Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `NEWS_API_KEY` | Optional | NewsAPI key for news fetching | `abc123...` |
| `GNEWS_API_KEY` | Optional | GNews API key | `xyz789...` |
| `PORT` | Auto-set | Port for the server | `8000` |

### Frontend Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `REACT_APP_API_URL` | Yes | Backend API URL | `https://api.example.com` |

## Testing Deployment

### Backend Health Check

```bash
# Test health endpoint
curl https://your-backend-url.com/health

# Expected response:
# {"status":"healthy","timestamp":"2024-01-01T12:00:00"}
```

### Frontend Testing

1. **Open your deployed URL**
2. **Test preferences**:
   - Select news segments
   - Save preferences
   - Verify they persist
3. **Test news fetching**:
   - Check if briefs load
   - Try different dates
   - Filter by categories
4. **Test responsiveness**:
   - Open on mobile device
   - Test different screen sizes

### API Endpoints Testing

```bash
# Get categories
curl https://your-backend-url.com/categories

# Save preferences
curl -X POST https://your-backend-url.com/preferences \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","segments":["Technology","Business"]}'

# Get news brief
curl -X POST https://your-backend-url.com/news-brief \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","date":"2024-01-01"}'
```

## Troubleshooting Deployment

### Backend Issues

**Issue**: Build fails on Render
```bash
# Solution: Check Python version in requirements.txt
# Ensure all dependencies are compatible
```

**Issue**: 502 Bad Gateway
```bash
# Check if service is running
# Verify PORT environment variable
# Check logs for errors
```

**Issue**: API key errors
```bash
# Verify environment variables are set
# Check API key validity
# RSS feeds work without API keys
```

### Frontend Issues

**Issue**: Blank page after deployment
```bash
# Check browser console for errors
# Verify REACT_APP_API_URL is set correctly
# Check if backend is accessible
```

**Issue**: CORS errors
```bash
# Backend should allow frontend origin
# Check CORS middleware configuration
# Ensure frontend URL is allowed
```

**Issue**: Environment variables not working
```bash
# Rebuild after adding environment variables
# Use REACT_APP_ prefix for CRA
# Restart development server
```

## Performance Optimization

### Backend
- Enable caching for news articles
- Use CDN for static assets
- Implement rate limiting
- Optimize database queries

### Frontend
- Enable production build
- Use lazy loading for components
- Implement service workers
- Compress images and assets

## Monitoring

### Backend Monitoring
- Check Render dashboard for logs
- Set up error tracking (e.g., Sentry)
- Monitor API response times
- Track API quota usage

### Frontend Monitoring
- Use Vercel Analytics
- Implement Google Analytics
- Monitor Core Web Vitals
- Track user interactions

## Scaling Considerations

### When to Scale
- >1000 users/day
- High API usage
- Slow response times
- Frequent downtimes

### Scaling Options
1. Upgrade to paid Render tier
2. Use managed database (PostgreSQL)
3. Implement Redis caching
4. Use serverless functions
5. Add load balancer

## Security Best Practices

1. **Never commit API keys**
   - Use environment variables
   - Add .env to .gitignore

2. **HTTPS everywhere**
   - Enforce SSL/TLS
   - Use secure headers

3. **Rate limiting**
   - Implement API rate limits
   - Prevent abuse

4. **Input validation**
   - Sanitize user inputs
   - Validate API responses

## Cost Estimates

### Free Tier (Small Scale)
- **Render**: Free (with limitations)
- **Vercel**: Free for hobby projects
- **NewsAPI**: 100 requests/day free
- **Total**: $0/month

### Paid Tier (Medium Scale)
- **Render**: $7/month (Starter)
- **Vercel**: Free (sufficient for most cases)
- **NewsAPI**: $449/month (Business)
- **Total**: ~$456/month

## Next Steps

1. **Custom Domain**
   - Purchase domain
   - Configure DNS
   - Add SSL certificate

2. **Monitoring**
   - Set up error tracking
   - Add analytics
   - Monitor performance

3. **CI/CD**
   - Automate deployments
   - Add testing pipeline
   - Set up staging environment

4. **Features**
   - Add user authentication
   - Implement email notifications
   - Add social sharing
   - Create mobile app

## Support

If you encounter issues during deployment:
1. Check application logs
2. Review this guide
3. Check service status pages
4. Open GitHub issue
5. Contact support

---

**Happy Deploying! 🎉**
