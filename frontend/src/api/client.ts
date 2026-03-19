import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client: AxiosInstance = axios.create({
  baseURL: apiUrl,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token if available
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ---------------------------------------------------------------------------
// Current user ID helper
// TODO: Replace with real auth context when authentication is implemented
// ---------------------------------------------------------------------------
const DEFAULT_USER_ID = 'test-user-1'

export function getCurrentUserId(): string {
  return localStorage.getItem('userId') || DEFAULT_USER_ID
}

export default client
