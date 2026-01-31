import axios from 'axios';

// En producción (Electron), la URL base debería ser localhost:8000
// En desarrollo web, podría ser el proxy de Vite o directo
const BASE_URL = 'http://localhost:8000';

const client = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor para agregar token si existe
client.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// --- Authentication API Calls ---

export const login = async (username, password) => {
    try {
        const response = await client.post('/auth/login', {
            username: username,
            password: password,
            ip_address: '127.0.0.1' // Placeholder or detect if possible
        });
        return response.data;
    } catch (error) {
        throw error.response ? error.response.data : new Error('Error de red al intentar iniciar sesión.');
    }
};

export const fetchCurrentUser = async () => {
    try {
        const response = await client.get('/auth/me');
        return response.data;
    } catch (error) {
        throw error.response ? error.response.data : new Error('Error de red al obtener el perfil del usuario.');
    }
};

export const logout = async () => {
    try {
        await client.post('/auth/logout');
    } catch (error) {
        console.error("Logout error:", error);
    }
    localStorage.removeItem('token');
};

export default client;