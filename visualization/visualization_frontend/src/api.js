import axios from 'axios';

// Determine the API base URL based on environment
const getApiBaseUrl = () => {
  // In production (Vercel), use relative URLs to the same domain
  if (process.env.NODE_ENV === 'production') {
    return '/api';
  }

  // In development, check if custom port is set or use default
  const devPort = process.env.REACT_APP_API_PORT || '5000';
  return `http://localhost:${devPort}/api`;
};

const API_BASE_URL = getApiBaseUrl();

export const fetchTimestamps = async (startDate, endDate, timezone) => {
  const response = await axios.get(`${API_BASE_URL}/timestamps`, {
    params: {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
      timezone: timezone
    }
  });
  return response.data;
};

export const fetchStats = async (timezone) => {
  const response = await axios.get(`${API_BASE_URL}/stats`, {
    params: {
      timezone: timezone
    }
  });
  return response.data;
};

export const fetchAllTimestamps = async (timezone) => {
  const response = await axios.get(`${API_BASE_URL}/timestamps/all`, {
    params: {
      timezone: timezone
    }
  });
  return response.data;
};