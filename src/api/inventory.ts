import { http } from "./http";

export const getInventory = async (sku: string) => {
  const resp = await http.get(`/api/inventory/${sku}`);
  return resp.data;
};

export default { getInventory };
