# Arbetsorder: Uppdatera logo + CSS pa member-card (prod)

## Mal

Pulla senaste andringarna fran repot och bygga om containern.
Andringarna ar: ny horisontell logo (transparent PNG), CSS-fix for layout,
TemplateResponse-signaturfix, env-baserade credentials.

## Steg

### 1. Ga till repot

```bash
cd /home/viktor/fgt-member-card
```

### 2. Pulla senaste

```bash
git pull origin main
```

### 3. Bygg om och starta

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Verifiera

```bash
docker ps | grep member-card
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8003/
# Forvantat: 200
```

### 5. Testa i webblasare

Oppna `https://membercard.fgctrollhattan.se/` och kontrollera att:
- Ny horisontell logo visas (FGC TROLLHATTAN i bla text, transparent bakgrund)
- Logon visas korrekt mot mork bakgrund (ingen vit ruta)
- Landningssida visar logon utan dubbel "FGC Trollhattan"-text under

## Klart-kriterier

- [ ] `git pull` lyckades
- [ ] Container kor (`docker ps`)
- [ ] Sidan svarar 200
- [ ] Logo visas korrekt (horisontell, transparent bakgrund)
