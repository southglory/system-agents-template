# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

Un framework multi-agente basado en turnos construido sobre Claude Code.

Cada agente se ejecuta como una sesión independiente de Claude Code, se comunica a través de salas de chat, y un bot gestiona automáticamente el tablero de tareas.

## 🚀 Instalación en una línea

```bash
curl -sSL https://raw.githubusercontent.com/southglory/system-agents-template/main/install.sh -o install.sh
bash install.sh
```

Hace **como máximo dos preguntas** — la ubicación de instalación y qué plugins traer desde [`system-agents-plugins`](https://github.com/southglory/system-agents-plugins). Configura la plantilla, el agente `recruiter`, los plugins seleccionados, las skills globales de Claude Code, las plantillas `.env` y un manifiesto para las futuras herramientas de actualización.

¿Prefieres los pasos manuales o las banderas completas? Mira [`docs/INSTALL.md`](docs/INSTALL.md).

## Estructura

```
system-agents/
├── agents/
│   ├── _example/              ← Plantilla de agente (copia manual)
│   ├── recruiter/             ← Reclutador de agentes (/recruit)
│   │   ├── CLAUDE.md          ← Reglas de comportamiento (por Fase)
│   │   └── role.md            ← Definición de rol
│   ├── antigravity/           ← Plantilla de agente Antigravity
│   │   └── role.md
│   └── {AgentName}/           ← Tus agentes
├── .agents/
│   └── workflows/             ← Flujos de trabajo turbo de Antigravity
├── chatrooms/
│   ├── PROTOCOL.md            ← Protocolo de chat (tipos de mensaje)
│   ├── .read-status/          ← Seguimiento del estado de lectura
│   └── general/               ← Canal compartido
├── tasks/
│   ├── PROTOCOL.md            ← Protocolo de gestión de tareas
│   └── board.yaml             ← Tablero de tareas (solo escritura del bot)
├── bot/
│   ├── turn-bot.py            ← Script del bot de turnos
│   └── requirements.txt
├── skills/
│   ├── check-chatroom/        ← Verificar mensajes no leídos
│   ├── check-mentions/        ← Verificar menciones
│   ├── send-message/          ← Enviar mensaje (validación de tipo)
│   ├── end-turn/              ← Finalizar turno
│   └── report/                ← Compartir resultados automáticamente
└── README.md
```

## Operación basada en turnos

Los agentes no se ejecutan libremente en paralelo. Se ejecutan secuencialmente en **rondas**.

```
=== Ronda N ===

[Fase 1: Bot]  Actualizar board.yaml (reflejar mensajes de la ronda anterior)

[Fase 2: Plan] (los agentes se ejecutan secuencialmente)
  Cada agente → leer mensajes + reclamar tareas (task-claim)

[Fase 3: Bot]  Actualizar board.yaml (reflejar reclamaciones)

[Fase 4: Ejecutar] (los agentes se ejecutan secuencialmente)
  Cada agente → realizar el trabajo real + enviar mensajes de resultado

[Fase 5: Bot]  Actualizar board.yaml (reflejar resultados)

=== Ronda N+1 ===
```

## Compatibilidad multi-agente

Esta plantilla soporta la colaboración entre agentes **Claude Code** y **Antigravity** (Google).

| | Claude Code | Antigravity |
|---|---|---|
| **Configuración** | `agents/{name}/CLAUDE.md` | `agents/antigravity/role.md` |
| **Ejecución** | Por turnos (Phase 2/4) | `.agents/workflows/` turbo |
| **Comunicación** | Mensajes `chatrooms/` | Mensajes `chatrooms/` |
| **Seguimiento de tareas** | `board.yaml` (solo lectura) | `board.yaml` (solo lectura) |

Ambos agentes comparten el mismo `board.yaml` y `chatrooms/` -- siguen el mismo protocolo por turnos para una colaboración sin conflictos.

## Inicio rápido

### 1. Instalar Skills

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. Crear agentes

**Opción A: Usar el reclutador (recomendado)**

```bash
cd agents/recruiter && claude
# Luego escribe: /recruit
```

El reclutador hará preguntas sobre el rol, las habilidades y los colaboradores del nuevo agente, y luego generará automáticamente todos los archivos necesarios.

**Opción B: Copia manual**

```bash
cp -r agents/_example agents/MyAgent
```

Define el rol en `role.md` y las reglas en `CLAUDE.md`.

### 3. Ejecutar una ronda

```bash
# Fase 1: Bot
python bot/turn-bot.py

# Fase 2: Cada agente planifica (detecta la fase automáticamente)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Fase 3: Bot
python bot/turn-bot.py

# Fase 4: Cada agente ejecuta (detecta la fase automáticamente)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Fase 5: Bot
python bot/turn-bot.py
```

## Conceptos clave

### Agentes
- Se ejecutan como sesiones independientes de Claude Code
- Planifican en la Fase 2, ejecutan en la Fase 4
- Acceso de solo lectura a board.yaml — los cambios se realizan a través de mensajes de chat

### Salas de chat
- Mensajería asíncrona basada en archivos
- Los tipos de mensaje distinguen conversaciones de comandos de tareas
- Soporte de archivos adjuntos

### Tipos de mensaje

| type | Propósito |
|------|-----------|
| `message` | Conversación general |
| `task-create` | Solicitar nueva tarea |
| `task-update` | Cambiar estado/asignado |
| `task-done` | Reportar tarea completada |
| `task-claim` | Reclamar una tarea (Fase 2) |
| `turn-end` | Finalizar turno |

### Bot
- Acceso exclusivo de escritura a board.yaml
- Escanea mensajes de la sala de chat (task-*) y actualiza board.yaml
- Asigna IDs (T-001) en task-create y envía confirmación

### Skills
- `/check-chatroom {room}` — Verificar mensajes no leídos
- `/check-mentions` — Verificar mensajes que te mencionan
- `/send-message {room}` — Enviar mensaje (con validación de tipo)
- `/end-turn` — Finalizar tu turno
- `/report` — Compartir automáticamente resultados del trabajo en las salas de chat relevantes

## Escenario: Juego de rondas

Alice (frontend) y Bob (backend) construyendo un panel de control juntos.

### Ronda 1

**Fase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```
> Primera ronda. El tablero está vacío.

**Fase 2 — Turno de Alice (Plan)**
```
Alice : Revisando la sala de chat... No hay mensajes nuevos.
        Revisando el tablero... No hay tareas.
        Necesitamos tareas nuevas.
User  : Necesitamos un panel de control. Tú te encargas del frontend, Bob del API.
Alice : Enviando 2 mensajes task-create.
        → [general] task-create "Dashboard UI" assignee: alice
        → [general] task-create "Dashboard API" assignee: bob
        /end-turn
```

**Fase 2 — Turno de Bob (Plan)**
```
Bob   : Revisando la sala de chat... Alice creó 2 tareas.
        El desarrollo del API me fue asignado. Reclamaré después de que el bot asigne los IDs.
        Nada que hacer en esta fase.
        /end-turn
```

**Fase 3 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 2 messages:
  [task-create] T-001 — Dashboard UI
  [task-create] T-002 — Dashboard API
```
> T-001, T-002 registrados en board.yaml. El bot notifica en general.

**Fase 4 — Turno de Alice (Ejecutar)**
```
Alice : Revisando la sala de chat... El bot registró T-001, T-002.
        Revisando el tablero... T-001 (Dashboard UI) asignado a mí, estado: pending.
        Iniciando T-001.
        ... (escribiendo componentes React) ...
        Estructura básica de la UI completada.
User  : Compártelo.
Alice : /report
        → [general] task-update T-001 status: in-progress "Basic layout done"
        → [alice-bob] message "Please use /api/stats format for the endpoint"
        /end-turn
```

**Fase 4 — Turno de Bob (Ejecutar)**
```
Bob   : Revisando la sala de chat... Alice trabajando en T-001, solicitó formato de API.
        Revisando el tablero... T-002 (Dashboard API) asignado a mí, estado: pending.
        Iniciando T-002 con el endpoint /api/stats.
        ... (escribiendo endpoints FastAPI) ...
        API completada.
        /report
        → [general] task-done T-002 "API complete, includes /api/stats"
        → [alice-bob] message "API is up. Call /api/stats"
        /end-turn
```

**Fase 5 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 3 messages:
  [task-update] T-001 — in-progress
  [task-done] T-002 — done
```

### Ronda 2

**Fase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```

**Fase 2 — Turno de Alice**
```
Alice : Revisando la sala de chat... Bob terminó el API, /api/stats disponible.
        Revisando el tablero... T-001 (UI) in-progress, T-002 (API) done.
        Reclamando T-001 para continuar.
        → [general] task-claim T-001
        /end-turn
```

**Fase 2 — Turno de Bob**
```
Bob   : Revisando la sala de chat... No hay tareas nuevas asignadas.
        Nada que hacer esta ronda.
        /end-turn
```

> Bob no tiene nada que hacer — simplemente finaliza el turno. Ahorra tokens.

**Fase 3 — Bot** → Refleja la reclamación.

**Fase 4 — Turno de Alice**
```
Alice : Integrando el API para terminar el panel de control.
        ... (fetch + renderizado de gráficos) ...
        /report
        → [general] task-done T-001 "API integration complete, dashboard done"
        /end-turn
```

**Fase 4 — Turno de Bob**
```
Bob   : Nada que hacer.
        /end-turn
```

**Fase 5 — Bot** → T-001 marcado como completado. ¡Todas las tareas terminadas!

## Principios de diseño

1. **Separación de roles** — Cada agente tiene una responsabilidad específica
2. **Comunicación por turnos** — Planificar → Ejecutar → Reportar por ronda
3. **Mutación indirecta** — Los cambios en board.yaml solo se realizan a través de mensajes de chat
4. **Prevención de conflictos** — Los agentes solo agregan datos, solo el bot escribe en board.yaml
5. **Ejecución independiente** — Cada agente trabaja sin depender de otros

## Soporte

Si encuentras útil este proyecto, ¡por favor deja una estrella! Ayuda a que otros lo descubran.

## Licencia

Licencia MIT. Úsalo libremente.

## Historial de estrellas

<a href="https://star-history.com/#southglory/system-agents-template&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
 </picture>
</a>
