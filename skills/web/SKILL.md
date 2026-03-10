# Web Skill

## Metadata
- name: web
- description: Melakukan operasi terkait web (browsing, scraping, HTTP requests)
- aliases: [browser, scrape, http]
- category: utility

## Description
Skill ini memungkinkan asisten untuk melakukan operasi web seperti:
- HTTP requests (GET, POST)
- Web scraping
- Mengambil konten dari URL

## Triggers
- web 
- browser 
- scrape 
- http 

## AI Instructions
Ketika user meminta operasi web, gunakan skill ini dengan format:
- Jika user ingin scrape konten: `web scrape <URL>`
- Jika user ingin GET request: `web get <URL>`
- Jika user ingin POST request: `web post <URL> <data>`

Contoh:
- "buka google.com" → `web get https://google.com`
- "scrape wikipedia" → `web get https://wikipedia.org`

## Execution
Handler Python terletak di `script/handler.py`
