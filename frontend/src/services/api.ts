import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance
const apiClient = axios.create({
    baseURL: API_BASE_URL,
});

console.log('API Base URL:', API_BASE_URL);

// Token setter function - to be called by auth context
let getTokenFunc: (() => Promise<string | undefined>) | null = null;

export const setTokenGetter = (getter: () => Promise<string | undefined>) => {
    getTokenFunc = getter;
};

// Request interceptor to add auth token
apiClient.interceptors.request.use(
    async (config) => {
        if (getTokenFunc) {
            const token = await getTokenFunc();
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Unauthorized - token expired or invalid
            console.error('Authentication required');
            // Don't auto-logout, let the UI handle it
        } else if (error.response?.status === 403) {
            // Forbidden - insufficient permissions
            console.error('Insufficient permissions');
        }
        return Promise.reject(error);
    }
);

export const uploadDocument = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/documents/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });

    return response.data;
};

export const queryRAGSystem = async (
    query: string, 
    top_k: number = 5,
    search_method: 'vector' | 'keyword' | 'hybrid' = 'hybrid'
) => {
    const response = await apiClient.post('/query', { query, top_k, search_method });
    return response.data;
};

// Alias for backward compatibility
export const fetchQueryResults = queryRAGSystem;

export const checkHealth = async () => {
    const response = await apiClient.get('/health');
    return response.data;
};

export const listDocuments = async () => {
    const response = await apiClient.get('/documents/list');
    return response.data;
};

// Auth endpoints
export const getCurrentUser = async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
};

export const getAuthStatus = async () => {
    const response = await apiClient.get('/auth/status');
    return response.data;
};