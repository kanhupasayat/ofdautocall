// API Configuration
// This ensures production URL is always used when deployed

// Check if running on localhost or production
const isLocalhost = window.location.hostname === 'localhost' ||
                    window.location.hostname === '127.0.0.1' ||
                    window.location.hostname === ''

// Use environment variable first, then fallback to hardcoded values
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
                     (isLocalhost
                       ? 'http://localhost:8000/api'
                       : 'https://ofdautocall.onrender.com/api')

console.log('[Config] Hostname:', window.location.hostname)
console.log('[Config] Is Localhost:', isLocalhost)
console.log('[Config] API_BASE_URL:', API_BASE_URL)

export { API_BASE_URL }
