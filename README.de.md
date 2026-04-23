# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

Ein rundenbasiertes Multi-Agenten-Framework, aufgebaut auf Claude Code.

Jeder Agent wird als unabhängige Claude-Code-Sitzung ausgeführt, kommuniziert über Chaträume, und ein Bot verwaltet automatisch das Aufgabenboard.

## 🚀 Installation in einer Zeile

```bash
curl -sSL https://raw.githubusercontent.com/southglory/system-agents-template/main/install.sh -o install.sh
bash install.sh
```

Stellt **höchstens zwei Fragen** — den Installationsort und welche Plugins aus [`system-agents-plugins`](https://github.com/southglory/system-agents-plugins) geholt werden sollen. Richtet das Template, den `recruiter`-Agent, die ausgewählten Plugins, die globalen Claude-Code-Skills, `.env`-Vorlagen und ein Manifest für zukünftige Update-Werkzeuge in einem Rutsch ein.

Wer lieber die manuellen Schritte oder die vollständigen Flags sieht: [`docs/INSTALL.md`](docs/INSTALL.md).

## Struktur

```
system-agents/
├── agents/
│   ├── _example/              ← Agenten-Vorlage (manuell kopieren)
│   ├── recruiter/             ← Agenten-Recruiter (/recruit)
│   │   ├── CLAUDE.md          ← Verhaltensregeln (pro Phase)
│   │   └── role.md            ← Rollendefinition
│   ├── antigravity/           ← Antigravity-Agenten-Vorlage
│   │   └── role.md
│   └── {AgentName}/           ← Ihre Agenten
├── .agents/
│   └── workflows/             ← Antigravity-Turbo-Workflows
├── chatrooms/
│   ├── PROTOCOL.md            ← Chat-Protokoll (Nachrichtentypen)
│   ├── .read-status/          ← Lesestatus-Verfolgung
│   └── general/               ← Gemeinsamer Kanal
├── tasks/
│   ├── PROTOCOL.md            ← Aufgabenverwaltungsprotokoll
│   └── board.yaml             ← Aufgabenboard (nur Bot schreibt)
├── bot/
│   ├── turn-bot.py            ← Turn-Bot-Skript
│   └── requirements.txt
├── skills/
│   ├── check-chatroom/        ← Ungelesene Nachrichten prüfen
│   ├── check-mentions/        ← Erwähnungen prüfen
│   ├── send-message/          ← Nachricht senden (Typvalidierung)
│   ├── end-turn/              ← Runde beenden
│   └── report/                ← Arbeitsergebnisse automatisch teilen
└── README.md
```

## Rundenbasierter Betrieb

Agenten laufen nicht frei parallel. Sie werden sequenziell in **Runden** ausgeführt.

```
=== Runde N ===

[Phase 1: Bot]  board.yaml aktualisieren (Nachrichten der vorherigen Runde einbeziehen)

[Phase 2: Planung] (Agenten laufen sequenziell)
  Jeder Agent → Nachrichten lesen + Aufgaben beanspruchen (task-claim)

[Phase 3: Bot]  board.yaml aktualisieren (Beanspruchungen einbeziehen)

[Phase 4: Ausführung] (Agenten laufen sequenziell)
  Jeder Agent → eigentliche Arbeit erledigen + Ergebnisnachrichten senden

[Phase 5: Bot]  board.yaml aktualisieren (Ergebnisse einbeziehen)

=== Runde N+1 ===
```

## Multi-Agenten-Kompatibilität

Diese Vorlage unterstützt die Zusammenarbeit von **Claude Code** und **Antigravity** (Google) Agenten.

| | Claude Code | Antigravity |
|---|---|---|
| **Konfiguration** | `agents/{name}/CLAUDE.md` | `agents/antigravity/role.md` |
| **Ausführung** | Rundenbasiert (Phase 2/4) | `.agents/workflows/` Turbo |
| **Kommunikation** | `chatrooms/` Nachrichten | `chatrooms/` Nachrichten |
| **Aufgabenverfolgung** | `board.yaml` (nur lesen) | `board.yaml` (nur lesen) |

Beide Agenten teilen dasselbe `board.yaml` und `chatrooms/` -- sie folgen demselben rundenbasierten Protokoll für konfliktfreie Zusammenarbeit.

## Schnellstart

### 1. Skills installieren

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. Agenten erstellen

**Option A: Recruiter verwenden (empfohlen)**

```bash
cd agents/recruiter && claude
# Dann eingeben: /recruit
```

Der Recruiter stellt Fragen zur Rolle, den Skills und der Zusammenarbeit des neuen Agenten und generiert anschließend alle erforderlichen Dateien automatisch.

**Option B: Manuell kopieren**

```bash
cp -r agents/_example agents/MyAgent
```

Definieren Sie die Rolle in `role.md` und die Regeln in `CLAUDE.md`.

### 3. Eine Runde ausführen

```bash
# Phase 1: Bot
python bot/turn-bot.py

# Phase 2: Jeder Agent plant (Phase wird automatisch erkannt)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 3: Bot
python bot/turn-bot.py

# Phase 4: Jeder Agent führt aus (Phase wird automatisch erkannt)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 5: Bot
python bot/turn-bot.py
```

## Kernkonzepte

### Agenten
- Werden als unabhängige Claude-Code-Sitzungen ausgeführt
- Planen in Phase 2, führen aus in Phase 4
- Nur Lesezugriff auf board.yaml — Änderungen erfolgen über Chat-Nachrichten

### Chaträume
- Dateibasierte asynchrone Nachrichtenübermittlung
- Nachrichtentypen unterscheiden Konversationen von Aufgabenbefehlen
- Anhang-Unterstützung

### Nachrichtentypen

| Typ | Zweck |
|-----|-------|
| `message` | Allgemeine Konversation |
| `task-create` | Neue Aufgabe anfordern |
| `task-update` | Status/Zuständigen ändern |
| `task-done` | Aufgabenabschluss melden |
| `task-claim` | Aufgabe beanspruchen (Phase 2) |
| `turn-end` | Runde beenden |

### Bot
- Alleiniger Schreibzugriff auf board.yaml
- Scannt Chatraum-Nachrichten (task-*) und aktualisiert board.yaml
- Vergibt IDs (T-001) bei task-create und sendet Bestätigung

### Skills
- `/check-chatroom {room}` — Ungelesene Nachrichten prüfen
- `/check-mentions` — Nachrichten prüfen, in denen Sie erwähnt werden
- `/send-message {room}` — Nachricht senden (mit Typvalidierung)
- `/end-turn` — Ihre Runde beenden
- `/report` — Arbeitsergebnisse automatisch in relevante Chaträume teilen

## Szenario: Rundenablauf

Alice (Frontend) und Bob (Backend) bauen gemeinsam ein Dashboard.

### Runde 1

**Phase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```
> Erste Runde. Das Board ist leer.

**Phase 2 — Alices Runde (Planung)**
```
Alice : Chatraum prüfen... Keine neuen Nachrichten.
        Board prüfen... Keine Aufgaben.
        Wir brauchen neue Aufgaben.
User  : Wir brauchen ein Dashboard. Du machst das Frontend, Bob die API.
Alice : Sende 2 task-create-Nachrichten.
        → [general] task-create "Dashboard UI" assignee: alice
        → [general] task-create "Dashboard API" assignee: bob
        /end-turn
```

**Phase 2 — Bobs Runde (Planung)**
```
Bob   : Chatraum prüfen... Alice hat 2 Aufgaben erstellt.
        API-Entwicklung ist mir zugewiesen. Ich beanspruche sie, nachdem der Bot IDs vergeben hat.
        In dieser Phase nichts zu tun.
        /end-turn
```

**Phase 3 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 2 messages:
  [task-create] T-001 — Dashboard UI
  [task-create] T-002 — Dashboard API
```
> T-001, T-002 in board.yaml registriert. Bot benachrichtigt in general.

**Phase 4 — Alices Runde (Ausführung)**
```
Alice : Chatraum prüfen... Bot hat T-001, T-002 registriert.
        Board prüfen... T-001 (Dashboard UI) mir zugewiesen, Status: pending.
        Beginne T-001.
        ... (React-Komponenten schreiben) ...
        Grundlegende UI-Struktur fertig.
User  : Teile es.
Alice : /report
        → [general] task-update T-001 status: in-progress "Grundlayout fertig"
        → [alice-bob] message "Bitte /api/stats-Format für den Endpunkt verwenden"
        /end-turn
```

**Phase 4 — Bobs Runde (Ausführung)**
```
Bob   : Chatraum prüfen... Alice arbeitet an T-001, hat API-Format angefragt.
        Board prüfen... T-002 (Dashboard API) mir zugewiesen, Status: pending.
        Beginne T-002 mit /api/stats-Endpunkt.
        ... (FastAPI-Endpunkte schreiben) ...
        API fertig.
        /report
        → [general] task-done T-002 "API fertig, enthält /api/stats"
        → [alice-bob] message "API ist bereit. Rufe /api/stats auf"
        /end-turn
```

**Phase 5 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 3 messages:
  [task-update] T-001 — in-progress
  [task-done] T-002 — done
```

### Runde 2

**Phase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```

**Phase 2 — Alices Runde**
```
Alice : Chatraum prüfen... Bob hat API fertiggestellt, /api/stats verfügbar.
        Board prüfen... T-001 (UI) in-progress, T-002 (API) done.
        Beanspruche T-001, um fortzufahren.
        → [general] task-claim T-001
        /end-turn
```

**Phase 2 — Bobs Runde**
```
Bob   : Chatraum prüfen... Keine neuen Aufgaben zugewiesen.
        In dieser Runde nichts zu tun.
        /end-turn
```

> Bob hat nichts zu tun — beendet einfach die Runde. Spart Tokens.

**Phase 3 — Bot** → Beanspruchung übernommen.

**Phase 4 — Alices Runde**
```
Alice : API integrieren, um das Dashboard fertigzustellen.
        ... (Fetch + Diagramm-Rendering) ...
        /report
        → [general] task-done T-001 "API-Integration abgeschlossen, Dashboard fertig"
        /end-turn
```

**Phase 4 — Bobs Runde**
```
Bob   : Nichts zu tun.
        /end-turn
```

**Phase 5 — Bot** → T-001 als erledigt markiert. Alle Aufgaben abgeschlossen!

## Designprinzipien

1. **Rollentrennung** — Jeder Agent hat eine fokussierte Verantwortung
2. **Rundenbasierte Kommunikation** — Planen → Ausführen → Berichten pro Runde
3. **Indirekte Mutation** — board.yaml-Änderungen nur über Chat-Nachrichten
4. **Konfliktvermeidung** — Agenten schreiben nur anhängend, nur der Bot schreibt board.yaml
5. **Unabhängige Ausführung** — Jeder Agent arbeitet ohne Abhängigkeit von anderen

## Unterstützung

Wenn Sie dieses Projekt nützlich finden, hinterlassen Sie bitte einen Stern! Das hilft anderen, es zu entdecken.

## Lizenz

MIT-Lizenz. Frei verwendbar.

## Stern-Verlauf

<a href="https://star-history.com/#southglory/system-agents-template&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
 </picture>
</a>
