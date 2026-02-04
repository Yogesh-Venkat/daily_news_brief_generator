// ✅ CLEAN, ESLINT-CI SAFE VERSION

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Newspaper, Settings, RefreshCw, Loader, Check,
  ExternalLink, TrendingUp, Briefcase, Dumbbell,
  Heart, Film, Landmark, LogOut, Database
} from 'lucide-react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const CATEGORY_ICONS = {
  Technology: TrendingUp,
  Business: Briefcase,
  Sports: Dumbbell,
  Health: Heart,
  Entertainment: Film,
  Politics: Landmark
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(true);

  const [formData, setFormData] = useState({
    email: '', password: '', name: '',
    segments: [], reading_preference: 'short'
  });

  const [preferences, setPreferences] = useState({
    segments: [], reading_preference: 'short', language: 'en'
  });

  const [categories, setCategories] = useState([]);
  const [newsBriefs, setNewsBriefs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedCategory, setSelectedCategory] = useState(null);

  // ✅ Stable headers
  const getAuthHeaders = useCallback(() => ({
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json'
  }), [token]);

  // ✅ Logout first (others depend on it)
  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  // ✅ Load user
  const loadUserData = useCallback(async (authToken) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/me`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setUser(res.data.user);
      setPreferences(res.data.preferences);
    } catch {
      handleLogout();
    }
  }, [handleLogout]);

  // ✅ Categories
  const fetchCategories = useCallback(async () => {
    const res = await axios.get(`${API_BASE_URL}/categories`);
    setCategories(res.data.categories);
  }, []);

  // ✅ News
  const fetchNewsBrief = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/news-brief`, {
        category: selectedCategory,
        date: selectedDate
      }, { headers: getAuthHeaders() });

      setNewsBriefs(res.data.briefs);
    } catch {
      handleLogout();
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedDate, getAuthHeaders, handleLogout]);

  // ✅ Effects
  useEffect(() => {
    const t = localStorage.getItem('token');
    if (t) {
      setToken(t);
      setIsAuthenticated(true);
      loadUserData(t);
    }
    fetchCategories();
  }, [loadUserData, fetchCategories]);

  useEffect(() => {
    if (isAuthenticated && preferences.segments.length) {
      fetchNewsBrief();
    }
  }, [isAuthenticated, preferences.segments, fetchNewsBrief]);

  if (!isAuthenticated) {
    return <div className="app"><h1>Login Screen</h1></div>;
  }

  return (
    <div className="app">
      <header className="header">
        <Newspaper size={28} />
        <h2>Welcome {user?.name}</h2>
        <button onClick={handleLogout}><LogOut /></button>
      </header>

      <main>
        {loading ? <Loader /> : (
          newsBriefs.map((brief, i) => (
            <div key={i}>
              <h3>{brief.category}</h3>
              {brief.articles.map((a, j) => (
                <div key={j}>
                  <h4>{a.title}</h4>
                  <p>{a.summary}</p>
                  <a href={a.url} target="_blank" rel="noreferrer">
                    Read <ExternalLink size={14}/>
                  </a>
                </div>
              ))}
            </div>
          ))
        )}
      </main>
    </div>
  );
}

export default App;
