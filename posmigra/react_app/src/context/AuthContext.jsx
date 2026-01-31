// src/context/AuthContext.js
import React, { createContext, useState, useEffect, useContext } from 'react';
import { login as apiLogin, fetchCurrentUser, logout as apiLogout } from '../api/client';

// Create the AuthContext
const AuthContext = createContext(null);

// Custom hook to use the AuthContext
export const useAuth = () => {
  return useContext(AuthContext);
};

// AuthProvider component to wrap the application
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true); // For initial loading state
  const [error, setError] = useState(null); // For login/fetch errors

  // Effect to fetch user profile when the component mounts or token changes
  useEffect(() => {
    const initializeAuth = async () => {
      if (token) {
        try {
          // The api.js interceptor will automatically add the token to the header
          const currentUser = await fetchCurrentUser();
          setUser(currentUser);
        } catch (err) {
          // If token is invalid, clear it and log out
          console.error("Failed to fetch user with stored token:", err);
          logout();
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, [token]);

  // Login function
  const login = async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiLogin(username, password);
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        // The useEffect will trigger to fetch the user profile
      }
    } catch (err) {
      console.error("Login failed:", err);
      setError(err.detail || 'Failed to log in. Please check your credentials.');
      setLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    try {
      await apiLogout();
    } catch (err) {
      console.error("Error during API logout:", err);
    }
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  // The value provided to the context consumers
  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};