import { http } from "./http";

export const adminApi = {
  // existing
  listPacking: async () => {
    const resp = await http.get("/api/admin/packing"); // or /api/packing depending on backend
    return resp.data;
  },

  createProduct: async (p: any) => {
    const resp = await http.post("/api/admin/products", p);
    return resp.data;
  },

  // NEW: markPacked
  markPacked: async (taskId: string) => {
    // two common possible backend endpoints; prefer /api/admin/packing/{id}/mark-packed
    // adjust if your backend exposes a different path.
    const resp = await http.post(`/api/admin/packing/${taskId}/mark-packed`);
    return resp.data;
  },
};

export default adminApi;
