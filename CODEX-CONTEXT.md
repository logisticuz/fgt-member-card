# Codex Context — fgt-member-card

Senast uppdaterad: 2026-03-24

## Vad ar det har?

Digitalt medlemskortssystem for FGC Trollhattan. Verifierar medlemskap via
personnummer (eBas/n8n), genererar unika kort-ID:n (FGC-XXXXXX), och visar
digitala kort med spelardata och QR-kod.

FastAPI + Jinja2 + vanilla JS. Kors i Docker.

## Ekosystem

Tre system delar en Postgres-databas (`fgc_checkin`):

| System | Repo | Port | Status |
|--------|------|------|--------|
| Turneringar | `fgt-checkin-system` | 8001 | Produktion |
| **Medlemskort** | `fgt-member-card` | 8003 | **Produktion** |
| Meetups | `fgc-thn-meetups` | 8004 | DEV |

Alla tre ansluter till Docker-natverket `fgt-checkin-system_fgt-net` i prod
(`fgt-dev_fgt-net` i dev) for att na Postgres och n8n.

## Prod-deploy (Raspberry Pi 4)

Deployat 2026-03-24 pa Pi:n. Tillgangligt via `https://membercard.fgctrollhattan.se`.

### Senaste sync-andring (2026-03-24)

Prod-agenten fixade tva problem under deploy. Dessa fixar har synkats tillbaka
till repot i commit `7746dae`:

1. **TemplateResponse-signatur** — Starlette 0.28+ andrade signaturen fran
   `TemplateResponse("name.html", {"request": req, ...})` till
   `TemplateResponse(request, "name.html", {...})`. Repot anvander opinnande
   versioner sa prod fick senaste Starlette.

2. **Hardkodad devpassword i docker-compose.prod.yml** — Bytt fran
   `postgresql://fgc:devpassword@...` till `postgresql://fgc:${POSTGRES_PASSWORD}@...`
   sa att credentials laser fran `.env`-filen istallet for att ligga i
   versionshanterad kod.

### Prod-agenten skapade aven:

- `card_ids`-tabellen i prod-databasen (saknades)
- SSL-cert via certbot (Let's Encrypt)
- Nginx server-block i fgt-checkin-system's nginx.conf

## Databasschema

### Delade tabeller (ags av fgt-checkin-system)

```sql
players (uuid TEXT PK, name, tag, email, telephone, total_events, is_member, ...)
card_ids (card_id TEXT PK, player_uuid TEXT FK -> players.uuid)
audit_log (id SERIAL, timestamp, user_name, action, target_table, details)
```

### Inga egna tabeller

Detta system lagger till rader i `card_ids` och laser fran `players`.
Det skapar inga egna tabeller.

## Kodmonster

- **Ingen ORM.** Raw SQL med `psycopg3`. Connection pool via `psycopg_pool`.
- **`backend/db.py`** — alla DB-operationer (get_card, create_card_id, find_player_by_tag, etc.)
- **`backend/main.py`** — FastAPI app med routes + API
- **`backend/validation.py`** — personnummer-validering (Luhn, format)
- **`backend/static/`** — JS for kortrendering, QR-generering
- **`backend/templates/`** — Jinja2 (index.html, landningssida + kort-vy)
- **Autocommit.** Poolen skapas med `kwargs={"autocommit": True}`.

## API-endpoints

| Metod | Path | Beskrivning |
|-------|------|-------------|
| GET | `/` | Landningssida — ange personnummer + tag |
| GET | `/{card_id}` | Kort-vy (JS renderar) — validerar FGC-[A-Z0-9]{4,8} |
| POST | `/api/verify` | Verifiera medlem via eBas/n8n, returnerar card_id |
| GET | `/api/card/{card_id}` | Kort-data som JSON |

## QR-kod — dual purpose

QR-koden pa kortet pekar till `https://membercard.fgctrollhattan.se/FGC-XXXXXX`.
Den fungerar bade som:
- **Visningslanke** — oppna i webblasare for att se kortet
- **Checkin-token** — meetup/turneringssystem skannar QR:n och extraherar card_id

## Viktiga regler

- **Personnummer lagras aldrig.** GDPR — anvands bara for realtidsverifiering mot eBas.
- **Skapa inte tabeller.** Tabellerna ags av `fgt-checkin-system/init.sql`.
- **`players` ar delad.** Lasning ar fritt, men skapa/uppdatera spelare gors primant av turneringssystemet.
- **Pinna inte versioner.** `requirements.txt` ar opinnad — var medveten om att API:er (som TemplateResponse) kan andra signatur vid uppgradering.

## Vad som ATERSTAR

- [ ] Logo med transparent bakgrund (vantar pa Viktor)
- [ ] Spelarstatistik pa kortet (events, favorit-spel, streak)
- [ ] Rate limiting pa `/api/verify` (personnummer-endpoint)
- [ ] Pinna versioner i requirements.txt for stabilitet
