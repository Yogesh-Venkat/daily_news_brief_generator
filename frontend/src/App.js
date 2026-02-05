import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  Newspaper, 
  Settings, 
  RefreshCw, 
  Loader, 
  Check,
  ExternalLink,
  TrendingUp,
  Briefcase,
  Dumbbell,
  Heart,
  Film,
  Landmark,
  LogOut,
  Database
} from 'lucide-react';
import './App.css';


const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';


const CATEGORY_ICONS = {
  'Technology': TrendingUp,
  'Business': Briefcase,
  'Sports': Dumbbell,
  'Health': Heart,
  'Entertainment': Film,
  'Politics': Landmark
};


function App() {
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(true);

  // Registration/Login form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    segments: [],
    reading_preference: 'short'
  });
  const [authError, setAuthError] = useState('');

  // App state
  const [preferences, setPreferences] = useState({
    segments: [],
    reading_preference: 'short',
    language: 'en'
  });
  const [showSettings, setShowSettings] = useState(false);
  const [categories, setCategories] = useState([]);
  const [newsBriefs, setNewsBriefs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');


  // Define handleLogout first (used by other functions)
  const handleLogout = useCallback(() => {
    if (token) {
      axios.post(`${API_BASE_URL}/logout`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }).catch(console.error);
    }

    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    setPreferences({ segments: [], reading_preference: 'short', language: 'en' });
    setNewsBriefs([]);
    setFormData({ email: '', password: '', name: '', segments: [], reading_preference: 'short' });
  }, [token]);

  // Define loadUserData with proper dependencies
  const loadUserData = useCallback(async (authToken) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      setUser(response.data.user);
      setPreferences(response.data.preferences);
    } catch (error) {
      console.error('Error loading user data:', error);
      handleLogout();
    }
  }, [handleLogout]);

  // Define fetchCategories
  const fetchCategories = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/categories`);
      setCategories(response.data.categories);
    } catch (error) {
      console.error('Error fetching categories:', error);
      setCategories(['Technology', 'Business', 'Sports', 'Health', 'Entertainment', 'Politics']);
    }
  }, []);

  // Define fetchNewsBrief with proper dependencies
  const fetchNewsBrief = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/news-brief`, {
        category: selectedCategory,
        date: selectedDate,
        force_refresh: forceRefresh
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      setNewsBriefs(response.data.briefs);
    } catch (error) {
      console.error('Error fetching news brief:', error);
      if (error.response?.status === 401) {
        handleLogout();
      }
      setNewsBriefs([]);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedDate, token, handleLogout]);

  // Setup axios interceptor for auth
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
      setIsAuthenticated(true);
      loadUserData(storedToken);
    }

    fetchCategories();
  }, [loadUserData, fetchCategories]);

  useEffect(() => {
    if (isAuthenticated && preferences.segments.length > 0) {
      fetchNewsBrief();
    }
  }, [isAuthenticated, preferences.segments, fetchNewsBrief]);

  const getAuthHeaders = () => ({
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  });

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError('');

    if (formData.segments.length === 0) {
      setAuthError('Please select at least one news category');
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/register`, formData);

      const { token: newToken, user: newUser } = response.data;

      localStorage.setItem('token', newToken);
      setToken(newToken);
      setUser(newUser);
      setPreferences({
        segments: formData.segments,
        reading_preference: formData.reading_preference,
        language: 'en'
      });
      setIsAuthenticated(true);
    } catch (error) {
      setAuthError(error.response?.data?.detail || 'Registration failed');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/login`, {
        email: formData.email,
        password: formData.password
      });

      const { token: newToken, user: newUser } = response.data;

      localStorage.setItem('token', newToken);
      setToken(newToken);
      setUser(newUser);
      setIsAuthenticated(true);

      await loadUserData(newToken);
    } catch (error) {
      setAuthError(error.response?.data?.detail || 'Login failed');
    }
  };

  const updatePreferences = async () => {
    try {
      await axios.put(`${API_BASE_URL}/preferences`, preferences, {
        headers: getAuthHeaders()
      });

      setSaveMessage('Preferences updated successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
      setShowSettings(false);
      fetchNewsBrief(true);
    } catch (error) {
      console.error('Error updating preferences:', error);
      setSaveMessage('Error updating preferences');
    }
  };

  const toggleSegment = (segment) => {
    if (isAuthenticated) {
      setPreferences(prev => ({
        ...prev,
        segments: prev.segments.includes(segment)
          ? prev.segments.filter(s => s !== segment)
          : [...prev.segments, segment]
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        segments: prev.segments.includes(segment)
          ? prev.segments.filter(s => s !== segment)
          : [...prev.segments, segment]
      }));
    }
  };

  const handleRefresh = () => {
    fetchNewsBrief(true);
  };

  const handleCategoryFilter = (category) => {
    setSelectedCategory(category === selectedCategory ? null : category);
  };

  const clearCache = async () => {
    try {
      await axios.delete(`${API_BASE_URL}/clear-cache`, {
        headers: getAuthHeaders()
      });
      setSaveMessage('Cache cleared! Fetching fresh news...');
      setTimeout(() => setSaveMessage(''), 3000);
      fetchNewsBrief(true);
    } catch (error) {
      console.error('Error clearing cache:', error);
    }
  };

  // Auth screens
  if (!isAuthenticated) {
    return (
      <div className="app">
        <div className="auth-container">
          <div className="auth-content">
            <div className="auth-header">
              <Newspaper size={48} />
              <h1>Daily News Brief</h1>
              <p>Your personalized AI-powered news assistant</p>
            </div>

            <div className="auth-tabs">
              <button
                className={showLogin ? 'active' : ''}
                onClick={() => {
                  setShowLogin(true);
                  setAuthError('');
                }}
              >
                Login
              </button>
              <button
                className={!showLogin ? 'active' : ''}
                onClick={() => {
                  setShowLogin(false);
                  setAuthError('');
                }}
              >
                Sign Up
              </button>
            </div>

            {showLogin ? (
              <form onSubmit={handleLogin} className="auth-form">
                <h2>Welcome Back!</h2>

                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="email"
                    placeholder="your.email@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Password</label>
                  <input
                    type="password"
                    placeholder="Enter your password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                  />
                </div>

                {authError && <div className="auth-error">{authError}</div>}

                <button type="submit" className="auth-submit">Login</button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="auth-form">
                <h2>Create Your Account</h2>

                <div className="form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    placeholder="Your name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="email"
                    placeholder="your.email@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Password</label>
                  <input
                    type="password"
                    placeholder="Choose a password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                    minLength={6}
                  />
                </div>

                <div className="form-group">
                  <label>Select Your News Interests</label>
                  <div className="category-grid">
                    {categories.map(category => {
                      const Icon = CATEGORY_ICONS[category] || Newspaper;
                      return (
                        <button
                          key={category}
                          type="button"
                          className={`category-button ${formData.segments.includes(category) ? 'selected' : ''}`}
                          onClick={() => toggleSegment(category)}
                        >
                          <Icon size={20} />
                          <span>{category}</span>
                          {formData.segments.includes(category) && (
                            <Check size={16} className="check-icon" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="form-group">
                  <label>Reading Preference</label>
                  <div className="radio-group">
                    <label>
                      <input
                        type="radio"
                        value="short"
                        checked={formData.reading_preference === 'short'}
                        onChange={(e) => setFormData({ ...formData, reading_preference: e.target.value })}
                      />
                      Short Summaries
                    </label>
                    <label>
                      <input
                        type="radio"
                        value="detailed"
                        checked={formData.reading_preference === 'detailed'}
                        onChange={(e) => setFormData({ ...formData, reading_preference: e.target.value })}
                      />
                      Detailed Summaries
                    </label>
                  </div>
                </div>

                {authError && <div className="auth-error">{authError}</div>}

                <button type="submit" className="auth-submit">Create Account</button>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Settings modal
  if (showSettings) {
    return (
      <div className="app">
        <div className="settings-modal">
          <div className="settings-content">
            <div className="settings-header">
              <Settings size={32} />
              <h1>Preferences</h1>
              <p>Customize your news experience</p>
            </div>

            <div className="preferences-section">
              <h3>News Segments</h3>
              <div className="category-grid">
                {categories.map(category => {
                  const Icon = CATEGORY_ICONS[category] || Newspaper;
                  return (
                    <button
                      key={category}
                      className={`category-button ${preferences.segments.includes(category) ? 'selected' : ''}`}
                      onClick={() => toggleSegment(category)}
                    >
                      <Icon size={24} />
                      <span>{category}</span>
                      {preferences.segments.includes(category) && (
                        <Check size={20} className="check-icon" />
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="reading-preference">
                <h3>Reading Preference</h3>
                <div className="radio-group">
                  <label>
                    <input
                      type="radio"
                      value="short"
                      checked={preferences.reading_preference === 'short'}
                      onChange={(e) => setPreferences(prev => ({ ...prev, reading_preference: e.target.value }))}
                    />
                    Short Summaries
                  </label>
                  <label>
                    <input
                      type="radio"
                      value="detailed"
                      checked={preferences.reading_preference === 'detailed'}
                      onChange={(e) => setPreferences(prev => ({ ...prev, reading_preference: e.target.value }))}
                    />
                    Detailed Summaries
                  </label>
                </div>
              </div>

              {saveMessage && (
                <div className="save-message">{saveMessage}</div>
              )}

              <div className="settings-actions">
                <button 
                  className="save-button"
                  onClick={updatePreferences}
                  disabled={preferences.segments.length === 0}
                >
                  Save Changes
                </button>
                <button 
                  className="cancel-button"
                  onClick={() => {
                    setShowSettings(false);
                    loadUserData(token);
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Main app
  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <Newspaper size={32} />
            <div>
              <h1>Daily News Brief</h1>
              <span className="user-greeting">Welcome, {user?.name}!</span>
            </div>
          </div>

          <div className="header-actions">
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className="date-picker"
            />
            <button 
              className="icon-button" 
              onClick={handleRefresh} 
              disabled={loading}
              title="Force refresh from API"
            >
              <RefreshCw size={20} className={loading ? 'spinning' : ''} />
            </button>
            <button 
              className="icon-button" 
              onClick={clearCache}
              title="Clear cache"
            >
              <Database size={20} />
            </button>
            <button className="icon-button" onClick={() => setShowSettings(true)}>
              <Settings size={20} />
            </button>
            <button className="icon-button logout-button" onClick={handleLogout}>
              <LogOut size={20} />
            </button>
          </div>
        </div>

        <div className="category-filters">
          <button
            className={`filter-chip ${!selectedCategory ? 'active' : ''}`}
            onClick={() => setSelectedCategory(null)}
          >
            All Categories
          </button>
          {preferences.segments.map(segment => (
            <button
              key={segment}
              className={`filter-chip ${selectedCategory === segment ? 'active' : ''}`}
              onClick={() => handleCategoryFilter(segment)}
            >
              {segment}
            </button>
          ))}
        </div>
      </header>

      <main className="main-content">
        {saveMessage && (
          <div className="info-banner">{saveMessage}</div>
        )}

        {loading ? (
          <div className="loading-container">
            <Loader size={48} className="spinning" />
            <p>Loading your personalized news brief...</p>
          </div>
        ) : newsBriefs.length === 0 ? (
          <div className="empty-state">
            <Newspaper size={64} />
            <h2>No News Available</h2>
            <p>Try selecting a different date or refreshing the page</p>
          </div>
        ) : (
          <div className="briefs-container">
            {newsBriefs.map((brief, index) => {
              const Icon = CATEGORY_ICONS[brief.category] || Newspaper;
              return (
                <div key={index} className="brief-card">
                  <div className="brief-header">
                    <div className="brief-title">
                      <Icon size={28} />
                      <h2>{brief.category}</h2>
                      {brief.cached && (
                        <span className="cached-badge" title="From cache">
                          <Database size={16} /> Cached
                        </span>
                      )}
                    </div>
                    <span className="brief-date">{brief.date}</span>
                  </div>

                  <div className="consolidated-summary">
                    {brief.consolidated_summary.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>

                  <div className="articles-section">
                    <h3>Top Stories</h3>
                    <div className="articles-grid">
                      {brief.articles.slice(0, 6).map((article, idx) => (
                        <div key={idx} className="article-card">
                          <h4>{article.title}</h4>
                          <p className="article-description">
                            {article.description && article.description.length > 150
                              ? article.description.substring(0, 150) + '...'
                              : article.description || 'No description available'}
                          </p>
                          <div className="article-footer">
                            <span className="article-source">{article.source}</span>
                            <a 
                              href={article.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="read-more"
                            >
                              Read More <ExternalLink size={14} />
                            </a>  
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      <footer className="footer">
        <p>Daily News Brief Generator • Personalized AI-Powered News • Logged in as {user?.email}</p>
      </footer>
    </div>
  );
}


export default App;
