import { http } from "./http";
export const paymentsApi = {
  tokenize: async (cardNumber: string, expiry: string, name: string) => {
    const resp = await http.post("/api/payments/tokenize", { cardNumber, expiry, name });
    return resp.data;
  },
};

export default paymentsApi;
