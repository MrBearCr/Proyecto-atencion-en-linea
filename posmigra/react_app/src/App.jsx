// src/App.jsx
import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import ConfigScreen from './components/config/ConfigScreen';
import api from './api/client';
import './App.css';

const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuth();
    if (loading) return <div>Loading Auth...</div>;
    return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
  const [isConfigured, setIsConfigured] = useState(null); // null=checking, true=ok, false=need setup
  const { loading: authLoading } = useAuth();

  useEffect(() => {
    const checkBackendStatus = async () => {
        try {
            const response = await api.get('/config/status');
            setIsConfigured(response.data.configured);
        } catch (error) {
            console.error("Failed to check backend status:", error);
            // If API is down or 503 (DB not connected), we assume config might be needed 
            // OR backend is just dead.
            // If 503, it means backend is UP but DB is DOWN -> Config needed.
            // If connection refused, backend is DOWN.
            if (error.response && error.response.status === 503) {
                 setIsConfigured(false);
            } else {
                 // Assume not configured if we can't reach it, or maybe show a "Backend Down" screen.
                 // For now, let's default to Setup which will try to connect.
                 setIsConfigured(false);
            }
        }
    };
    checkBackendStatus();
  }, []);

  if (isConfigured === null || authLoading) {
    return <div className="loading-screen">Iniciando aplicación...</div>;
  }

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/setup" 
            element={isConfigured ? <Navigate to="/login" /> : <ConfigScreen />} 
          />
          <Route 
            path="/login" 
            element={
                !isConfigured ? <Navigate to="/setup" /> : <Login />
            } 
          />
          <Route 
            path="/dashboard/*" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          <Route path="/" element={<Navigate to={isConfigured ? "/login" : "/setup"} />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;