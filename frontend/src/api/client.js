import axios from "axios";
export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "", timeout: 12000 });
export const readError = (error) => error?.response?.data?.detail || error.message || "Unexpected request failure";
