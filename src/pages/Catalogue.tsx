import { useEffect, useState } from "react";
import { listProducts } from "../api/catalogue";
import type { Product } from "../types";
import ProductCard from "../components/ProductCard";

export default function Catalogue() {
  const [data, setData] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
  listProducts()
    .then(setData)
    .catch((e: unknown) => setError(String(e)))
    .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ padding: 12 }}>Loading products…</p>;
  if (error)   return <p style={{ padding: 12, color: "crimson" }}>{error}</p>;

  if (data.length === 0) {
    return <p style={{ padding: 12 }}>No products found.</p>;
  }

  return (
    <div
      style={{
        display: "grid",
        gap: 12,
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        padding: 12,
      }}
    >
      {data.map((p) => (
        <ProductCard key={p.sku} product={p} />
      ))}
    </div>
  );
}
