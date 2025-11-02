import { http } from "./http";

export const authApi = {
  register: async (name: string, email: string, password: string) => {
    const resp = await http.post("/api/auth/register", { name, email, password });
    return resp.data;
  },
  login: async (email: string, password: string) => {
    const resp = await http.post("/api/auth/login", { email, password });
    // resp is AxiosResponse; real token is in resp.data
    const data = resp.data;
    if (data?.accessToken) {
      localStorage.setItem("auth_token", data.accessToken);
    }
    return data;
  },
  me: async () => {
    const resp = await http.get("/api/customers/me");
    return resp.data;
  },
};

export default authApi;
