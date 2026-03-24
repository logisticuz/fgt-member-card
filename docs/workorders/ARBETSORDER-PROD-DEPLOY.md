# Arbetsorder: Prod-deploy av fgt-member-card

## Mål

Deploya det digitala medlemskortssystemet på Raspberry Pi 4 och göra det
tillgängligt via `https://membercard.fgctrollhattan.se`.

## Förutsättningar

- DNS A-post skapad: `membercard.fgctrollhattan.se` → `213.89.64.103`
- Repot: `github.com/logisticuz/fgt-member-card`
- Port **8003** (extern) → **8002** (intern)
- Delar Postgres + n8n med checkin-systemet via `fgt-checkin-system_fgt-net`

## Steg

### 1. Klona repot på Pi:n

```bash
cd /home/viktor  # eller var FGC-projekt ligger
git clone https://github.com/logisticuz/fgt-member-card.git
cd fgt-member-card
```

### 2. Skapa .env

```bash
cp .env.example .env
```

Filen behöver bara finnas — `docker-compose.prod.yml` overridar DATABASE_URL
och N8N_INTERNAL_URL via `environment:`.

### 3. Bygg och starta

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Verifiera att containern körs

```bash
docker ps | grep member-card
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8003/
# Förväntat: 200
```

### 5. Verifiera DNS-propagering

```bash
getent hosts membercard.fgctrollhattan.se
# Förväntat: 213.89.64.103
```

### 6. Lägg till nginx server block

Pi:ns nginx kör i Docker (fgt-checkin-system). Lägg till ett nytt
server-block för `membercard.fgctrollhattan.se` i den befintliga
`nginx.conf` (samma fil som meetup + checkin).

**HTTP-block:**
```nginx
server {
    listen 80;
    server_name membercard.fgctrollhattan.se;

    location / {
        proxy_pass http://member-card:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**OBS:** `proxy_pass` beror på hur nginx når containern:
- Om nginx är i samma Docker-nätverk → `http://member-card:8002`
- Om nginx proxar via host → `http://127.0.0.1:8003`

Kolla hur meetup-blocket (`meetup.fgctrollhattan.se`) är konfigurerat
och följ samma mönster.

### 7. Testa nginx + reload

```bash
docker compose ... exec nginx nginx -t
docker compose ... restart nginx
# eller
docker compose ... up -d --force-recreate nginx
```

### 8. Testa HTTP

```bash
curl -I http://membercard.fgctrollhattan.se/
# Förväntat: 200
```

### 9. SSL med certbot

```bash
docker compose -f docker-compose.prod.yml run --rm certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d membercard.fgctrollhattan.se --agree-tos --no-eff-email
```

Följ samma certbot-mönster som för meetup-domänen.

### 10. Verifiera HTTPS

```bash
curl -I https://membercard.fgctrollhattan.se/
# Förväntat: 200, valid cert

curl -I http://membercard.fgctrollhattan.se/
# Förväntat: 301 → https://
```

### 11. E2E-test

```bash
# Landningssidan
curl -s https://membercard.fgctrollhattan.se/ | grep "Medlemskort"

# Ogiltigt kort-ID → 404
curl -s -o /dev/null -w '%{http_code}' https://membercard.fgctrollhattan.se/robots.txt
# Förväntat: 404

# Giltigt kort-format → 200 (JS renderar)
curl -s -o /dev/null -w '%{http_code}' https://membercard.fgctrollhattan.se/FGC-TEST01
# Förväntat: 200

# API card lookup → 404 (kort finns inte i DB, men endpoint fungerar)
curl -s -o /dev/null -w '%{http_code}' https://membercard.fgctrollhattan.se/api/card/FGC-TEST01
# Förväntat: 404
```

## Klart-kriterier

- [ ] Container körs (`docker ps`)
- [ ] `https://membercard.fgctrollhattan.se/` svarar 200
- [ ] HTTP redirectar till HTTPS
- [ ] SSL-cert giltigt (Let's Encrypt)
- [ ] `/robots.txt` returnerar 404 (inte catch-all)
- [ ] `/FGC-TEST01` returnerar 200
- [ ] Nginx configtest utan fel
