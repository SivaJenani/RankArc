import axios from 'axios';
import { DEMO_MODE, demoAdapter } from './demo';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  ...(DEMO_MODE ? {adapter:demoAdapter} : {}),
});

client.interceptors.request.use((config) => {
  const token = DEMO_MODE ? null : localStorage.getItem('rankly_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!DEMO_MODE && error.response?.status === 401) {
      localStorage.removeItem('rankly_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default client;
