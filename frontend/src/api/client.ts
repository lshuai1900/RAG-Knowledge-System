import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    if (detail) {
      console.error(`[API Error] ${detail.code}: ${detail.message}`);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
