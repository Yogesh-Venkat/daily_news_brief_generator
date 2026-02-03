# Daily News Brief Generator 📰

An AI-powered personalized news aggregation and summarization application that delivers customized daily news briefs based on user preferences.

## 🌟 Features

- **Personalized News**: Select your preferred news segments (Technology, Business, Sports, Health, Entertainment, Politics)
- **Multi-Source Aggregation**: Fetches news from NewsAPI, GNews, and RSS feeds
- **AI-Powered Summarization**: Uses transformer models to generate concise, readable summaries
- **Date-Based Navigation**: View news from specific dates
- **Category Filtering**: Filter news by specific categories
- **Clean UI**: Modern, intuitive React interface
- **Real-time Updates**: Refresh to get the latest news

## 🏗️ Architecture

### Backend (Python/FastAPI)
- **Framework**: FastAPI
- **News Sources**: NewsAPI, GNews, RSS Feeds (BBC, Wired, etc.)
- **AI Model**: HuggingFace Transformers (facebook/bart-large-cnn)
- **Database**: SQLite for user preferences
- **API Endpoints**:
  - `GET /categories` - Get available news categories
  - `POST /preferences` - Save user preferences
  - `GET /preferences/{user_id}` - Get user preferences
  - `POST /news-brief` - Generate personalized news brief
  - `GET /health` - Health check

### Frontend (React)
- **Framework**: React 18
- **Styling**: Custom CSS with modern design
- **Icons**: Lucide React
- **API Communication**: Axios
- **Features**: 
  - First-time user onboarding
  - Preference management
  - Date picker for historical news
  - Category filters
  - Responsive design

## 📋 Prerequisites

### Backend
- Python 3.11+
- pip

### Frontend
- Node.js 16+
- npm or yarn

### API Keys (Optional but Recommended)
- **NewsAPI**: https://newsapi.org/ (Free: 100 requests/day)
- **GNews**: https://gnews.io/ (Free: 100 requests/day)

> **Note**: The app works with RSS feeds even without API keys, but having API keys provides better news coverage.

## 🚀 Local Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd news-brief-generator
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your API keys (optional)
# NEWS_API_KEY=your_newsapi_key
# GNEWS_API_KEY=your_gnews_key

# Run the backend
python main.py
```

Backend will run on: http://localhost:8000

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Edit .env if needed (default: http://localhost:8000)
# REACT_APP_API_URL=http://localhost:8000

# Run the frontend
npm start
```

Frontend will run on: http://localhost:3000

## 📦 Deployment

### Backend Deployment (Render)

1. **Create a Render account** at https://render.com

2. **Deploy from GitHub**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `backend` folder
   - Configure:
     - **Name**: news-brief-backend
     - **Environment**: Python
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Add Environment Variables**:
   - `NEWS_API_KEY` (optional)
   - `GNEWS_API_KEY` (optional)

4. **Deploy**: Click "Create Web Service"

Your backend URL will be: `https://news-brief-backend.onrender.com`

### Frontend Deployment (Vercel/Netlify)

#### Option A: Vercel

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
cd frontend
vercel
```

3. Set environment variable:
   - `REACT_APP_API_URL` = your backend URL

#### Option B: Netlify

1. Install Netlify CLI:
```bash
npm install -g netlify-cli
```

2. Build and deploy:
```bash
cd frontend
npm run build
netlify deploy --prod
```

3. Set environment variable in Netlify dashboard:
   - `REACT_APP_API_URL` = your backend URL

### Alternative: Docker Deployment

#### Backend
```bash
cd backend
docker build -t news-brief-backend .
docker run -p 8000:8000 -e NEWS_API_KEY=your_key news-brief-backend
```

#### Full Stack with Docker Compose
```bash
# Create docker-compose.yml in root directory
docker-compose up -d
```

## 🎯 Usage

### First Time User

1. Open the application
2. You'll see the preferences screen
3. Select your preferred news segments (e.g., Technology, Business)
4. Choose reading preference (Short/Detailed)
5. Click "Save Preferences"

### Daily Use

1. **Home Page**: View your personalized news brief
2. **Change Date**: Use the date picker to view past news
3. **Filter by Category**: Click category chips to filter
4. **Refresh**: Click refresh icon for latest updates
5. **Settings**: Click settings icon to update preferences
6. **Read More**: Click "Read More" on any article to view the full story

## 🔧 Configuration

### News Sources

The application aggregates news from multiple sources:

1. **NewsAPI** (if API key provided)
2. **GNews** (if API key provided)
3. **RSS Feeds** (always active):
   - BBC News
   - Wired
   - And more...

### Personalization Logic

1. **User Preferences**: Stored in SQLite database
2. **Default Segments**: Technology, Business (if no preferences set)
3. **Duplicate Handling**: Title-based deduplication
4. **Source Priority**: Combines all sources for comprehensive coverage

### AI Summarization

- **Model**: facebook/bart-large-cnn (HuggingFace)
- **Fallback**: Extractive summarization if model unavailable
- **Summary Length**: ~30-130 characters
- **Processing**: Real-time summarization on news fetch

## 📊 Evaluation Criteria Compliance

| Criteria | Implementation |
|----------|----------------|
| **Personalization Logic** | User preferences stored in DB, customized briefs per user |
| **Insight Quality** | AI-powered summarization with clear, concise summaries |
| **Multi-Source Aggregation** | NewsAPI + GNews + RSS feeds with deduplication |
| **AI Utilization** | HuggingFace transformers for summarization |
| **UI & User Experience** | Clean, modern, intuitive React interface |
| **Deployment** | Ready for Render, Vercel, Netlify, Docker |

## 🎨 Technical Highlights

### Backend
- **FastAPI**: High-performance async API
- **SQLite**: Lightweight persistent storage
- **Multi-source aggregation**: Robust news fetching
- **Error handling**: Graceful fallbacks for API failures
- **Caching**: Optimized for repeated requests

### Frontend
- **React Hooks**: Modern functional components
- **Responsive Design**: Mobile-friendly
- **Loading States**: Smooth user experience
- **Error Handling**: User-friendly error messages
- **Accessibility**: Semantic HTML, keyboard navigation

## 🔍 Sample User Flows

### Flow 1: First-Time User
```
1. User opens app
2. Preferences screen appears
3. User selects: Technology, Business, Sports
4. User saves preferences
5. Home page loads with personalized brief
6. User sees 3 category briefs with top stories
```

### Flow 2: Exploring Past News
```
1. User on home page
2. Clicks date picker
3. Selects date (e.g., yesterday)
4. Brief regenerates for selected date
5. User explores historical news
```

### Flow 3: Category Filtering
```
1. User has multiple segments
2. Clicks "Technology" filter chip
3. View updates to show only Technology news
4. Clicks "All Categories" to reset
```

## 🐛 Troubleshooting

### Backend Issues

**Issue**: Model download fails
```bash
# Solution: Pre-download model
python -c "from transformers import pipeline; pipeline('summarization', model='facebook/bart-large-cnn')"
```

**Issue**: No news appearing
```bash
# Check API keys are set
# Verify RSS feeds are accessible
# Check backend logs for errors
```

### Frontend Issues

**Issue**: API connection error
```bash
# Verify backend is running
# Check REACT_APP_API_URL in .env
# Check CORS settings in backend
```

## 📝 API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is created for educational purposes.

## 🙏 Acknowledgments

- NewsAPI for news data
- GNews for additional news sources
- BBC RSS feeds
- HuggingFace for AI models
- FastAPI and React communities

## 📧 Support

For questions or issues, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ using FastAPI, React, and AI**
