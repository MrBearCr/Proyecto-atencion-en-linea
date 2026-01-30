import React, { useState } from 'react';
import './Header.css'; // For specific header styles

const Header = ({ appTitle = "Gestión de Clientes", username = "Usuario" }) => {
  const [menuOpen, setMenuOpen] = useState(false);

  const handleSettingsClick = () => {
    alert("Navegar a Configuración"); // Placeholder for actual navigation
    setMenuOpen(false);
  };

  const handleLogoutClick = () => {
    alert("Cerrar Sesión"); // Placeholder for actual logout logic
    setMenuOpen(false);
  };

  return (
    <header className="header-container">
      <div className="header-canvas">
        <h1 className="app-title">{appTitle}</h1>
        
        <div className="user-menu-wrapper">
          <button className="header-menu-button" onClick={() => setMenuOpen(!menuOpen)}>
            ☰
          </button>
          {menuOpen && (
            <div className="dropdown-menu">
              <button onClick={handleSettingsClick}>Configuración</button>
              <button onClick={handleLogoutClick}>Salir</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
