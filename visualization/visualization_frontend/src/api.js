import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

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