import axios from 'axios';

// Create a centralized Axios instance for full-stack communication
// In development: uses Vite proxy to http://127.0.0.1:8000 (configured in vite.config.ts)
// In production: can be overridden via VITE_API_BASE_URL env variable
const api = axios.create({
  baseURL: typeof __API_BASE_URL__ !== 'undefined' ? __API_BASE_URL__ : '/api',
  timeout: 60000, // 60s timeout for RAG LLM queries and document embedding tasks
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor (Logging / Request preparation)
api.interceptors.request.use(
  (config) => {
    // Standard request interceptor middleware
    // Could add auth tokens here in the future: config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor (Middleware for error handling & status formatting)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(`[API Error ${error.response.status}]:`, error.response.data);
    } else if (error.request) {
      console.error('[API Error]: No response received from server. Is the FastAPI backend running on port 8000?');
    } else {
      console.error('[API Error]:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api;
