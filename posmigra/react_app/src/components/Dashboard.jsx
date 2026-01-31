// src/components/Dashboard.js
import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Stock from './Stock'; // Placeholder for Stock module
import Tra from './Tra';   // Placeholder for TRA module
import Mbrp from './Mbrp'; // Placeholder for MBRP module

const modules = {
  STOCK: <Stock />,
  TRA: <Tra />,
  MBRP: <Mbrp />,
};

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [activeModule, setActiveModule] = useState('STOCK'); // Default module

  const sidebarStyle = {
    width: '200px',
    backgroundColor: '#f4f4f4',
    padding: '15px',
    height: '100vh',
    position: 'fixed',
    top: 0,
    left: 0,
  };

  const contentStyle = {
    marginLeft: '220px',
    padding: '20px',
  };

  const navButtonStyle = {
    display: 'block',
    width: '100%',
    padding: '10px',
    marginBottom: '10px',
    border: 'none',
    backgroundColor: '#e7e7e7',
    textAlign: 'left',
    cursor: 'pointer',
  };

  const activeNavButtonStyle = {
    ...navButtonStyle,
    backgroundColor: '#007bff',
    color: 'white',
  };

  return (
    <div>
      <div style={sidebarStyle}>
        <h3>Modules</h3>
        <button
          style={activeModule === 'STOCK' ? activeNavButtonStyle : navButtonStyle}
          onClick={() => setActiveModule('STOCK')}
        >
          Stock
        </button>
        <button
          style={activeModule === 'TRA' ? activeNavButtonStyle : navButtonStyle}
          onClick={() => setActiveModule('TRA')}
        >
          TRA
        </button>
        <button
          style={activeModule === 'MBRP' ? activeNavButtonStyle : navButtonStyle}
          onClick={() => setActiveModule('MBRP')}
        >
          MBRP
        </button>
        <div style={{ position: 'absolute', bottom: '20px', width: 'calc(100% - 30px)' }}>
          <p>Welcome, <strong>{user ? user.username : 'User'}</strong></p>
          <button onClick={logout} style={{ ...navButtonStyle, backgroundColor: '#dc3545', color: 'white', textAlign: 'center' }}>
            Logout
          </button>
        </div>
      </div>
      <div style={contentStyle}>
        {modules[activeModule]}
      </div>
    </div>
  );
};

export default Dashboard;
