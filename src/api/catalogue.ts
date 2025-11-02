import { http } from "./http";

export const listProducts = async (q = "", page = 1, size = 20) => {
  const resp = await http.get("/api/products", { params: { q, page, size } });
  // backend returns { items: [...], total: N }
  return resp.data;
};

export const getProduct = async (sku: string) => {
  const resp = await http.get(`/api/products/${sku}`);
  return resp.data;
};

export default { listProducts, getProduct };
