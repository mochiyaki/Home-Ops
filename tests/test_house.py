"""The house record backing the homeowner assistant."""

from __future__ import annotations


def test_house_seeds_itself(client):
    h = client.get("/api/house").json()
    assert h["slug"] == "default"
    assert h["address"]
    assert len(h["rooms"]) == 4
    assert len(h["assets"]) == 5
    assert any(a["model"] == "SHPM88Z75N" for a in h["assets"])


def test_house_is_stable_across_reads(client):
    first = client.get("/api/house").json()
    second = client.get("/api/house").json()
    assert first["id"] == second["id"], "must not reseed on every read"


def test_patch_house(client):
    client.get("/api/house")
    r = client.patch("/api/house", json={"homeowner": "Sam Rivera"})
    assert r.status_code == 200
    assert r.json()["homeowner"] == "Sam Rivera"
    assert client.get("/api/house").json()["homeowner"] == "Sam Rivera"


def test_asset_lifecycle(client):
    client.get("/api/house")
    created = client.post("/api/house/assets", json={
        "roomId": "r3", "category": "dryer", "brand": "Miele", "model": "TXR860",
    })
    assert created.status_code == 201
    asset_id = created.json()["id"]
    assert created.json()["brand"] == "Miele"

    patched = client.patch(f"/api/house/assets/{asset_id}",
                           json={"serial": "SN-99", "warrantyUntil": "2030-01-01"})
    assert patched.status_code == 200
    assert patched.json()["serial"] == "SN-99"

    assert client.delete(f"/api/house/assets/{asset_id}").status_code == 204
    assert client.delete(f"/api/house/assets/{asset_id}").status_code == 404
    models = [a["model"] for a in client.get("/api/house").json()["assets"]]
    assert "TXR860" not in models


def test_snapshot_is_agent_readable(client):
    client.get("/api/house")
    snap = client.get("/api/house/snapshot").json()["snapshot"]
    for expected in ("Address:", "Homeowner:", "Rooms:", "Inventory:"):
        assert expected in snap
    assert "SHPM88Z75N" in snap, "the agent must be able to name the dishwasher"


def test_unknown_asset_404(client):
    assert client.patch("/api/house/assets/nope", json={"brand": "x"}).status_code == 404
