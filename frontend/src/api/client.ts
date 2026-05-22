import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
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
