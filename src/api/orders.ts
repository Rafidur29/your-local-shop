import { http, idemHeaders } from "./http";

export const ordersApi = {
  create: async (payload: any) => {
    // include idempotency header (frontend may create an id and save in localStorage)
    const headers = idemHeaders ? idemHeaders() : {};
    const resp = await http.post("/api/orders", payload, { headers });
    return resp.data;
  },

  get: async (id: string) => {
    const resp = await http.get(`/api/orders/${id}`);
    return resp.data;
  },
};

export default ordersApi;
