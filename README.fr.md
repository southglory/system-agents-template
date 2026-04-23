# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)
![install CI](https://github.com/southglory/system-agents-template/actions/workflows/install.yml/badge.svg)
![Release](https://img.shields.io/github/v/release/southglory/system-agents-template)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

Un framework multi-agents basé sur les tours, construit sur Claude Code.

Chaque agent s'exécute en tant que session Claude Code indépendante, communique via des salons de discussion, et un bot gère automatiquement le tableau des tâches.

## 🚀 Installation en une ligne

Rolling (toujours le `main` le plus récent):

```bash
curl -sSL https://raw.githubusercontent.com/southglory/system-agents-template/main/install.sh -o install.sh
bash install.sh
```

Épinglé sur une Release stable (recommandé pour la reproductibilité):

```bash
curl -sSL https://github.com/southglory/system-agents-template/releases/latest/download/install.sh -o install.sh
bash install.sh
```


Pose **au maximum deux questions** — l'emplacement d'installation et les plugins à récupérer depuis [`system-agents-plugins`](https://github.com/southglory/system-agents-plugins). Configure le template, l'agent `recruiter`, les plugins sélectionnés, les compétences globales de Claude Code, les modèles `.env` et un manifeste pour les futurs outils de mise à jour, le tout en une seule étape.

Pour les étapes manuelles ou l'ensemble des options, voir [`docs/INSTALL.md`](docs/INSTALL.md).

## Structure

```
system-agents/
├── agents/
│   ├── _example/              ← Modèle d'agent (copie manuelle)
│   ├── recruiter/             ← Recruteur d'agent (/recruit)
│   │   ├── CLAUDE.md          ← Règles de comportement (par Phase)
│   │   └── role.md            ← Définition du rôle
│   ├── antigravity/           ← Modèle d'agent Antigravity
│   │   └── role.md
│   └── {AgentName}/           ← Vos agents
├── .agents/
│   └── workflows/             ← Workflows turbo Antigravity
├── chatrooms/
│   ├── PROTOCOL.md            ← Protocole de discussion (types de messages)
│   ├── .read-status/          ← Suivi du statut de lecture
│   └── general/               ← Canal partagé
├── tasks/
│   ├── PROTOCOL.md            ← Protocole de gestion des tâches
│   └── board.yaml             ← Tableau des tâches (écriture bot uniquement)
├── bot/
│   ├── turn-bot.py            ← Script du bot de tours
│   └── requirements.txt
├── skills/
│   ├── check-chatroom/        ← Vérifier les messages non lus
│   ├── check-mentions/        ← Vérifier les mentions
│   ├── send-message/          ← Envoyer un message (validation de type)
│   ├── end-turn/              ← Terminer le tour
│   └── report/                ← Partage automatique des résultats
└── README.md
```

## Fonctionnement par tours

Les agents ne s'exécutent pas librement en parallèle. Ils s'exécutent séquentiellement par **rounds**.

```
=== Round N ===

[Phase 1 : Bot]  Mise à jour de board.yaml (reflet des messages du round précédent)

[Phase 2 : Plan] (les agents s'exécutent séquentiellement)
  Chaque agent → lit les messages + réclame des tâches (task-claim)

[Phase 3 : Bot]  Mise à jour de board.yaml (reflet des réclamations)

[Phase 4 : Exécution] (les agents s'exécutent séquentiellement)
  Chaque agent → effectue le travail + envoie les messages de résultat

[Phase 5 : Bot]  Mise à jour de board.yaml (reflet des résultats)

=== Round N+1 ===
```

## Compatibilité multi-agent

Ce modèle prend en charge la collaboration entre les agents **Claude Code** et **Antigravity** (Google).

| | Claude Code | Antigravity |
|---|---|---|
| **Configuration** | `agents/{name}/CLAUDE.md` | `agents/antigravity/role.md` |
| **Exécution** | Par tours (Phase 2/4) | `.agents/workflows/` turbo |
| **Communication** | Messages `chatrooms/` | Messages `chatrooms/` |
| **Suivi des tâches** | `board.yaml` (lecture seule) | `board.yaml` (lecture seule) |

Les deux agents partagent le même `board.yaml` et `chatrooms/` -- ils suivent le même protocole par tours pour une collaboration sans conflit.

## Démarrage rapide

### 1. Installer les compétences

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. Créer des agents

**Option A : Utiliser le recruteur (recommandé)**

```bash
cd agents/recruiter && claude
# Puis saisir : /recruit
```

Le recruteur posera des questions sur le rôle, les compétences et les collaborateurs du nouvel agent, puis générera automatiquement tous les fichiers nécessaires.

**Option B : Copie manuelle**

```bash
cp -r agents/_example agents/MyAgent
```

Définissez le rôle dans `role.md` et les règles dans `CLAUDE.md`.

### 3. Exécuter un round

```bash
# Phase 1 : Bot
python bot/turn-bot.py

# Phase 2 : Chaque agent planifie (détection automatique de la phase)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 3 : Bot
python bot/turn-bot.py

# Phase 4 : Chaque agent exécute (détection automatique de la phase)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 5 : Bot
python bot/turn-bot.py
```

## Concepts clés

### Agents
- S'exécutent en tant que sessions Claude Code indépendantes
- Planifient en Phase 2, exécutent en Phase 4
- Accès en lecture seule à board.yaml — les modifications passent par les messages de discussion

### Salons de discussion
- Messagerie asynchrone basée sur des fichiers
- Les types de messages distinguent les conversations des commandes de tâches
- Prise en charge des pièces jointes

### Types de messages

| type | Objectif |
|------|----------|
| `message` | Conversation générale |
| `task-create` | Demander une nouvelle tâche |
| `task-update` | Modifier le statut/responsable |
| `task-done` | Signaler l'achèvement d'une tâche |
| `task-claim` | Réclamer une tâche (Phase 2) |
| `turn-end` | Terminer le tour |

### Bot
- Seul accès en écriture à board.yaml
- Analyse les messages du salon (task-*) et met à jour board.yaml
- Attribue des identifiants (T-001) lors d'un task-create et envoie une confirmation

### Compétences
- `/check-chatroom {room}` — Vérifier les messages non lus
- `/check-mentions` — Vérifier les messages vous mentionnant
- `/send-message {room}` — Envoyer un message (avec validation de type)
- `/end-turn` — Terminer votre tour
- `/report` — Partager automatiquement les résultats du travail dans les salons concernés

## Scénario : Déroulement d'un round

Alice (frontend) et Bob (backend) construisent un tableau de bord ensemble.

### Round 1

**Phase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```
> Premier round. Le tableau est vide.

**Phase 2 — Tour d'Alice (Plan)**
```
Alice : Vérification du salon... Pas de nouveaux messages.
        Vérification du tableau... Pas de tâches.
        Nous avons besoin de nouvelles tâches.
User  : Nous avons besoin d'un tableau de bord. Tu gères le frontend, Bob gère l'API.
Alice : Envoi de 2 messages task-create.
        → [general] task-create "Dashboard UI" assignee: alice
        → [general] task-create "Dashboard API" assignee: bob
        /end-turn
```

**Phase 2 — Tour de Bob (Plan)**
```
Bob   : Vérification du salon... Alice a créé 2 tâches.
        Le développement de l'API m'est assigné. Je réclamerai après que le bot ait attribué les identifiants.
        Rien à faire cette phase.
        /end-turn
```

**Phase 3 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 2 messages:
  [task-create] T-001 — Dashboard UI
  [task-create] T-002 — Dashboard API
```
> T-001, T-002 enregistrés dans board.yaml. Le bot notifie dans general.

**Phase 4 — Tour d'Alice (Exécution)**
```
Alice : Vérification du salon... Le bot a enregistré T-001, T-002.
        Vérification du tableau... T-001 (Dashboard UI) m'est assigné, statut : pending.
        Début de T-001.
        ... (écriture des composants React) ...
        Structure de base de l'interface terminée.
User  : Partage-le.
Alice : /report
        → [general] task-update T-001 status: in-progress "Basic layout done"
        → [alice-bob] message "Veuillez utiliser le format /api/stats pour l'endpoint"
        /end-turn
```

**Phase 4 — Tour de Bob (Exécution)**
```
Bob   : Vérification du salon... Alice travaille sur T-001, a demandé le format de l'API.
        Vérification du tableau... T-002 (Dashboard API) m'est assigné, statut : pending.
        Début de T-002 avec l'endpoint /api/stats.
        ... (écriture des endpoints FastAPI) ...
        API terminée.
        /report
        → [general] task-done T-002 "API complete, includes /api/stats"
        → [alice-bob] message "L'API est en ligne. Appelez /api/stats"
        /end-turn
```

**Phase 5 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 3 messages:
  [task-update] T-001 — in-progress
  [task-done] T-002 — done
```

### Round 2

**Phase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```

**Phase 2 — Tour d'Alice**
```
Alice : Vérification du salon... Bob a terminé l'API, /api/stats disponible.
        Vérification du tableau... T-001 (UI) in-progress, T-002 (API) done.
        Réclamation de T-001 pour continuer.
        → [general] task-claim T-001
        /end-turn
```

**Phase 2 — Tour de Bob**
```
Bob   : Vérification du salon... Pas de nouvelles tâches assignées.
        Rien à faire ce round.
        /end-turn
```

> Bob n'a rien à faire — il termine simplement son tour. Économie de tokens.

**Phase 3 — Bot** → Reflet de la réclamation.

**Phase 4 — Tour d'Alice**
```
Alice : Intégration de l'API pour terminer le tableau de bord.
        ... (fetch + rendu des graphiques) ...
        /report
        → [general] task-done T-001 "API integration complete, dashboard done"
        /end-turn
```

**Phase 4 — Tour de Bob**
```
Bob   : Rien à faire.
        /end-turn
```

**Phase 5 — Bot** → T-001 marqué comme terminé. Toutes les tâches sont complètes !

## Principes de conception

1. **Séparation des rôles** — Chaque agent a une responsabilité ciblée
2. **Communication par tours** — Planifier → Exécuter → Rapporter par round
3. **Mutation indirecte** — Les modifications de board.yaml passent uniquement par les messages de discussion
4. **Prévention des conflits** — Les agents n'ajoutent qu'en fin de fichier, seul le bot écrit dans board.yaml
5. **Exécution indépendante** — Chaque agent travaille sans dépendre des autres

## Support

Si vous trouvez ce projet utile, n'hésitez pas à laisser une étoile ! Cela aide les autres à le découvrir.

## Licence

Licence MIT. Utilisation libre.

## Historique des étoiles

<a href="https://star-history.com/#southglory/system-agents-template&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
 </picture>
</a>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=southglory/system-agents-template,southglory/system-agents-plugins&type=Date)](https://star-history.com/#southglory/system-agents-template&southglory/system-agents-plugins&Date)
