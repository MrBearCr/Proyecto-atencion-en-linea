import React, { useState, useEffect } from 'react';
import api from '../../api/client';
import './ConfigScreen.css';
import { useNavigate } from 'react-router-dom';

const ConfigScreen = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        server: '',
        database: 'vad10',
        user: '',
        password: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [statusMessage, setStatusMessage] = useState('');

    useEffect(() => {
        // Opcional: Verificar estado al montar por si ya se arregló
        checkStatus();
    }, []);

    const checkStatus = async () => {
        try {
            const response = await api.get('/config/status');
            if (response.data.configured) {
                navigate('/login');
            }
        } catch (err) {
            // Ignorar errores aquí, ya estamos en la pantalla de config
            console.log("Backend offline or unconfigured:", err);
        }
    };

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setStatusMessage('Guardando configuración y probando conexión...');

        try {
            const response = await api.post('/config/setup', formData);
            setStatusMessage('¡Conexión exitosa! Redirigiendo...');
            setTimeout(() => {
                navigate('/login');
            }, 1500);
        } catch (err) {
            console.error("Setup error:", err);
            setError(err.response?.data?.detail || "Error al conectar con la base de datos. Verifique los datos.");
            setStatusMessage('');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="config-container">
            <div className="config-card">
                <div className="config-header">
                    <h2>Configuración de Base de Datos</h2>
                    <p>Conexión inicial al servidor SQL Server</p>
                </div>

                {error && <div className="error-message">{error}</div>}

                <form onSubmit={handleSubmit} className="config-form">
                    <div className="form-group">
                        <label htmlFor="server">Servidor (IP o Host)</label>
                        <input
                            type="text"
                            id="server"
                            name="server"
                            className="form-input"
                            value={formData.server}
                            onChange={handleChange}
                            placeholder="Ej: 192.168.1.100 o SRV-SQL"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="database">Base de Datos</label>
                        <input
                            type="text"
                            id="database"
                            name="database"
                            className="form-input"
                            value={formData.database}
                            onChange={handleChange}
                            placeholder="Ej: vad10"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="user">Usuario SQL (Opcional)</label>
                        <input
                            type="text"
                            id="user"
                            name="user"
                            className="form-input"
                            value={formData.user}
                            onChange={handleChange}
                            placeholder="Dejar vacío para Auth Windows"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Contraseña</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            className="form-input"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="Contraseña del usuario SQL"
                        />
                    </div>

                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? 'Conectando...' : 'Guardar y Conectar'}
                    </button>
                    
                    {statusMessage && <p className="status-check">{statusMessage}</p>}
                </form>
            </div>
        </div>
    );
};

export default ConfigScreen;
