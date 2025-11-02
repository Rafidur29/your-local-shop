import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getProduct } from "../api/catalogue";
import { getInventory } from "../api/inventory";
import { useCart } from "../stores/cartStore";
import type { Product } from "../types";

export default function PDP() {
  const { sku = "" } = useParams();
  const add = useCart((s) => s.add);

  const [product, setProduct] = useState<Product | null>(null);
  const [available, setAvailable] = useState<number | null>(null);
  const [qty, setQty] = useState(1);

  useEffect(() => {
    getProduct(sku).then(setProduct);
    getInventory(sku).then((inv: any) => setAvailable(inv.available));
  }, [sku]);

  if (!product) return <p style={{ padding: 12 }}>Loading…</p>;
  const low = (available ?? 0) <= 5;
  const cappedQty = available == null ? qty : Math.min(qty, available);

  return (
    <div style={{ padding: 12 }}>
      <h2>{product.name}</h2>
      <img src={product.image} alt={product.name} width={96} height={96} loading="lazy" />
      <p>${product.price.toFixed(2)}</p>
      {available != null && (
        <p style={{ color: low ? "tomato" : "#666" }}>
          {low ? `Low stock: ${available} left` : `In stock: ${available}`}
        </p>
      )}
      <label>
        Qty{" "}
        <input
          type="number"
          min={1}
          value={cappedQty}
          onChange={(e) => setQty(Math.max(1, Number(e.target.value)))}
          style={{ width: 64 }}
        />
      </label>
      <div style={{ marginTop: 8 }}>
        <button
          disabled={available !== null && available < 1}
          onClick={() => add(product, cappedQty)}
        >
          Add to cart
        </button>
      </div>
    </div>
  );
}
