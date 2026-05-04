# Telegram Undervisnings-CRM Bot

MVP til kunder, lektioner og månedsafregning.

## Deploy på Railway (dit Hobby workspace)
1. New Project → Add Database → PostgreSQL
2. Deploy fra GitHub eller upload disse filer
3. Sæt Environment Variables:
   - TELEGRAM_BOT_TOKEN
4. Railway tilføjer DATABASE_URL automatisk
5. Deploy

## Funktioner
- /start med knapper
- Tilføj kunde
- Ny lektion (beløb + note)
- Månedsafslutning summerer og markerer betalt/skylder


## Docker
Railway detekterer Dockerfile automatisk. Ingen ekstra config nødvendig.
