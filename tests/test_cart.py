def test_add_update_delete_cart_items(client):
# seed one product via API seed or direct model
    from app.db import SessionLocal
    from app.models import Product, ProductVariant
    db = SessionLocal()
    p = Product(sku="SKUZ", name="Test Z", price_cents=500)
    db.add(p); db.flush()
    pv = ProductVariant(product_id=p.id, sku="SKUZ", price_cents=500, stock=10)
    db.add(pv); db.commit(); db.close()


    # add item
    r = client.post("/api/cart/items", json={"sku":"SKUZ","qty":2})
    assert r.status_code == 201
    item_id = r.json()["id"]


    # update
    r = client.patch(f"/api/cart/items/{item_id}", json={"sku":"SKUZ","qty":5})
    assert r.status_code == 200


    # delete
    r = client.delete(f"/api/cart/items/{item_id}")
    assert r.status_code == 204
