# Putzplan

Gemeinschaftlicher Haushalts-Putzplan als responsive Webapp mit
LLM-gestütztem Putz-Coach (Text + Sprache). Selbst gehostet als
Docker-Container, läuft auf Smartphone und Desktop.

## Features

- **Fällige Aufgaben** pro Raum & Etage, automatisch wiederkehrend
  (wöchentlich / monatlich / jährlich) — abgehakte Tasks verschwinden,
  bis sie wieder fällig sind
- **Touch-optimiertes Abhaken** mit Konfetti-Explosion zur Motivation
- **Mehrere User parallel** — Liste aktualisiert sich alle 15s
- **Wettbewerbe**: 👑 *Putzkönig* der letzten 10 Tage (rollend) +
  Tages-Leaderboard mit Kalorien
- **Putz-Coach (LLM)** mit Text- und Spracheingabe: kurze, konkrete
  Antworten zu Reinigungsthemen, Material, Flecken, Hausmittel
- **Auth** wie gewohnt: User/Pass + optional Keycloak/OIDC SSO
- **Task-Definition extern**: `seeds/tasks.yaml` per Hand editierbar,
  wird beim App-Start synchronisiert (idempotent)
- **PWA** mit Home-Screen-Icon

## Tech-Stack

- Python 3.12 + FastAPI + SQLAlchemy + SQLite
- Vanilla HTML/CSS/JS Frontend (kein Build)
- Auth: JWT, bcrypt, OIDC Authorization Code Flow
- LLM/STT: OpenAI-kompatible Endpunkte (`.env` konfigurierbar)
- Docker + Docker Compose

## Setup

```bash
git clone git@github.com:chamm-p/putzplan.git
cd putzplan
cp .env.example .env
# .env anpassen (Endpunkte, ggf. SECRET_KEY)
docker compose up -d
```

App läuft auf `http://<host>:${APP_PORT}` (Default `7801`).

## Tasks pflegen

Datei: [`seeds/tasks.yaml`](seeds/tasks.yaml) — beim Container-Start
wird abgeglichen:

- **Neue Räume/Tasks** werden angelegt
- **Geänderte Felder** (Name, Frequenz, Minuten, Kalorien, Icon) werden
  übernommen
- **Entfernte Einträge** werden auf `inactive` gesetzt — bestehende
  Completions bleiben in der Historie erhalten

YAML-Struktur:

```yaml
floors:
  - name: Erdgeschoss
    rooms:
      - name: Küche
        icon: 🍳
        tasks:
          - name: Boden wischen
            frequency: weekly   # weekly | monthly | yearly
            minutes: 10
            calories: 45        # optional, Default = minutes * 4
            hint: ""            # optional
```

Nach Edit: `docker compose restart putzplan_app`.

## Konfiguration (.env)

| Variable | Default | Bedeutung |
|---|---|---|
| `APP_PORT` | `7801` | Host-Port |
| `SECRET_KEY` | — | JWT-Signing-Key |
| `REGISTRATION_ENABLED` | `true` | User/Pass-Register an/aus |
| `TOKEN_EXPIRE_DAYS` | `60` | JWT-Lifetime |
| `LEADERBOARD_DAYS` | `10` | Rolling-Window für "Putzkönig" |
| `OIDC_*` | — | optionales Keycloak SSO |
| `LLM_*` | — | OpenAI-kompatibler Chat-Endpunkt |
| `STT_*` | — | OpenAI-kompatibler STT-Endpunkt (Whisper) |

## Backups

Sidecar-Container macht täglich einen atomaren SQLite-Snapshot nach
`./backups/putzplan-<UTC>.db.gz`, Retention 14 Tage. Wiederherstellen:

```bash
./scripts/restore.sh backups/putzplan-2026-05-14T12-00-00Z.db.gz
```

## Mikrofon-Hinweis

Der Sprach-Modus im Coach benötigt **HTTPS** oder **localhost** (Browser-
Restriktion). Im LAN über IP funktioniert das Mikro nicht — Reverse-Proxy
mit TLS davorschalten.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
