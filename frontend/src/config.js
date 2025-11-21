// API Configuration
// This ensures production URL is always used when deployed
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
                     (window.location.hostname === 'localhost'
                       ? 'http://localhost:8000/api'
                       : 'https://ofdautocall.onrender.com/api')

export { API_BASE_URL }
