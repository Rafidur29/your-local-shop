import axios from "axios";
import { v4 as uuidv4 } from "uuid";

export const http = axios.create({
  baseURL: process.env.REACT_APP_API_BASE || "", // set to http://localhost:8000 in .env
  timeout: 15000,
});

// optional: attach auth header
http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    cfg.headers = cfg.headers || {};
    cfg.headers["Authorization"] = `Bearer ${token}`;
  }
  return cfg;
});

// idem header helper
export const idemHeaders = () => {
  let key = localStorage.getItem("idem_key");
  if (!key) {
    key = uuidv4();
    localStorage.setItem("idem_key", key);
  }
  return { "Idempotency-Key": key };
};

export default http;
