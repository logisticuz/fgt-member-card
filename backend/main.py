"""
FGC Trollhättan — Digital Membership Card
Minimal FastAPI backend that serves membership cards
and verifies members via the shared Postgres players table.
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from . import db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="FGC THN Medlemskort")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

N8N_INTERNAL_URL = os.getenv("N8N_INTERNAL_URL", "http://n8n:5678")


# --- Models ---

class VerifyRequest(BaseModel):
    personnummer: str
    tag: str


# --- Routes ---

@app.get("/")
async def landing(request: Request):
    """Landing page — enter personnummer to retrieve card."""
    return templates.TemplateResponse("index.html", {"request": request, "page": "landing"})


@app.get("/{card_id}")
async def card_page(request: Request, card_id: str):
    """Serve the card page — JS handles rendering."""
    import re
    if not re.match(r"^FGC-[A-Z0-9]{4,8}$", card_id):
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse("index.html", {"request": request, "page": "card"})


# --- API ---

@app.post("/api/verify")
async def verify_member(payload: VerifyRequest):
    """
    Verify personnummer against eBas via n8n, match to player, return card.
    Flow:
    1. Call n8n eBas membership check with personnummer
    2. If member: match name to players table
    3. If player found: get or create card_id
    4. Return card_id + player info
    """
    import httpx
    from .validation import sanitize_personnummer, validate_personnummer

    pnr = sanitize_personnummer(payload.personnummer)
    is_valid, error = validate_personnummer(pnr)
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": error or "Ogiltigt personnummer"},
        )

    # Call n8n eBas check
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{N8N_INTERNAL_URL}/webhook/ebas/check",
                json={"personnummer": pnr},
            )
            result = resp.json()
    except Exception as e:
        logger.error(f"eBas check failed: {e}")
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": "Kunde inte verifiera medlemskap just nu. Försök igen."},
        )

    is_member = result.get("isMember", False)

    if not is_member:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "Inget aktivt medlemskap hittades. Kontakta styrelsen."},
        )

    # Match to players table via tag
    tag = payload.tag.strip()
    player = db.find_player_by_tag(tag)

    if not player:
        # Member in eBas but not in players yet — create minimal player
        player_uuid = db.create_player(name=tag, tag=tag)
        player = {"uuid": player_uuid, "name": tag, "tag": tag}

    # Mark as member in players table
    db.update_player_membership(player["uuid"], is_member=True)

    # Get or create card_id
    card_id = db.get_card_id_for_player(player["uuid"])
    if not card_id:
        card_id = db.create_card_id(player["uuid"])

    return {
        "ok": True,
        "card_id": card_id,
        "player": {
            "name": player["name"],
            "tag": player.get("tag"),
        },
    }


@app.get("/api/card/{card_id}")
async def get_card_data(card_id: str):
    """Return card data as JSON for client-side rendering."""
    card = db.get_card(card_id)

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return {
        "card_id": card_id,
        "name": card["name"],
        "tag": card.get("tag"),
        "total_events": card.get("total_events", 0),
        "favorite_game": card.get("favorite_game"),
        "first_seen": card.get("first_seen"),
        "last_seen": card.get("last_seen"),
    }
