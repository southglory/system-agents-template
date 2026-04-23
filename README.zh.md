# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

基于 Claude Code 构建的回合制多智能体框架。

每个智能体作为独立的 Claude Code 会话运行，通过聊天室进行通信，由机器人自动管理任务看板。

## 🚀 一行安装

```bash
curl -sSL https://raw.githubusercontent.com/southglory/system-agents-template/main/install.sh -o install.sh
bash install.sh
```

**最多只问两个问题** — 安装位置和要从 [`system-agents-plugins`](https://github.com/southglory/system-agents-plugins) 中选择安装的插件。脚本会一次性设置好模板本体、`recruiter` 智能体、所选插件、Claude Code 全局技能、`.env` 模板以及供未来更新工具使用的清单文件。

想手动安装或查看全部参数，请参阅 [`docs/INSTALL.md`](docs/INSTALL.md)。

## 结构

```
system-agents/
├── agents/
│   ├── _example/              ← 智能体模板（手动复制）
│   ├── recruiter/             ← 智能体招募员（/recruit）
│   │   ├── CLAUDE.md          ← 行为规则（按阶段）
│   │   └── role.md            ← 角色定义
│   ├── antigravity/           ← Antigravity 智能体模板
│   │   └── role.md
│   └── {AgentName}/           ← 你的智能体
├── .agents/
│   └── workflows/             ← Antigravity 涡轮工作流
├── chatrooms/
│   ├── PROTOCOL.md            ← 聊天协议（消息类型）
│   ├── .read-status/          ← 已读状态追踪
│   └── general/               ← 公共频道
├── tasks/
│   ├── PROTOCOL.md            ← 任务管理协议
│   └── board.yaml             ← 任务看板（仅机器人可写）
├── bot/
│   ├── turn-bot.py            ← 回合机器人脚本
│   └── requirements.txt
├── skills/
│   ├── check-chatroom/        ← 检查未读消息
│   ├── check-mentions/        ← 检查提及
│   ├── send-message/          ← 发送消息（类型验证）
│   ├── end-turn/              ← 结束回合
│   └── report/                ← 自动分享工作成果
└── README.md
```

## 回合制运行

智能体不会自由并行运行，而是按**回合**顺序执行。

```
=== Round N ===

[Phase 1: Bot]  更新 board.yaml（反映上一回合的消息）

[Phase 2: Plan]（智能体顺序执行）
  每个智能体 → 读取消息 + 认领任务（task-claim）

[Phase 3: Bot]  更新 board.yaml（反映认领）

[Phase 4: Execute]（智能体顺序执行）
  每个智能体 → 执行实际工作 + 发送结果消息

[Phase 5: Bot]  更新 board.yaml（反映结果）

=== Round N+1 ===
```

## 多智能体兼容性

此模板支持 **Claude Code** 和 **Antigravity**（Google）智能体协同工作。

| | Claude Code | Antigravity |
|---|---|---|
| **配置** | `agents/{name}/CLAUDE.md` | `agents/antigravity/role.md` |
| **执行** | 回合制（Phase 2/4） | `.agents/workflows/` 涡轮 |
| **通信** | `chatrooms/` 消息 | `chatrooms/` 消息 |
| **任务追踪** | `board.yaml`（只读） | `board.yaml`（只读） |

两个智能体共享相同的 `board.yaml` 和 `chatrooms/`——它们遵循相同的回合制协议，实现无冲突协作。

## 快速开始

### 1. 安装技能

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. 创建智能体

**方式 A：使用 recruiter（推荐）**

```bash
cd agents/recruiter && claude
# 输入：/recruit
```

recruiter 会通过问答形式定义新智能体的角色、技能和协作关系，并自动生成所需文件。

**方式 B：手动复制**

```bash
cp -r agents/_example agents/MyAgent
```

在 `role.md` 中定义角色，在 `CLAUDE.md` 中定义规则。

### 3. 运行一个回合

```bash
# Phase 1: Bot
python bot/turn-bot.py

# Phase 2: 每个智能体进行规划（自动检测阶段）
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 3: Bot
python bot/turn-bot.py

# Phase 4: 每个智能体执行任务（自动检测阶段）
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 5: Bot
python bot/turn-bot.py
```

## 核心概念

### 智能体
- 作为独立的 Claude Code 会话运行
- Phase 2 进行规划，Phase 4 执行任务
- 对 board.yaml 只有只读权限——变更通过聊天消息进行

### 聊天室
- 基于文件的异步消息传递
- 消息类型区分对话和任务命令
- 支持附件

### 消息类型

| type | 用途 |
|------|------|
| `message` | 普通对话 |
| `task-create` | 请求创建新任务 |
| `task-update` | 变更状态/负责人 |
| `task-done` | 报告任务完成 |
| `task-claim` | 认领任务（Phase 2） |
| `turn-end` | 结束回合 |

### 机器人
- 对 board.yaml 拥有唯一写权限
- 扫描聊天室消息（task-*）并更新 board.yaml
- 在 task-create 时分配 ID（T-001）并发送确认

### 技能
- `/check-chatroom {room}` — 检查未读消息
- `/check-mentions` — 检查提及你的消息
- `/send-message {room}` — 发送消息（带类型验证）
- `/end-turn` — 结束你的回合
- `/report` — 自动将工作成果分享到相关聊天室

## 场景：回合运行

Alice（前端）和 Bob（后端）一起构建仪表盘。

### 第 1 回合

**Phase 1 — 机器人**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```
> 第一回合。看板为空。

**Phase 2 — Alice 的回合（规划）**
```
Alice : 检查聊天室... 没有新消息。
        检查看板... 没有任务。
        我们需要创建新任务。
User  : 我们需要一个仪表盘。你负责前端，Bob 负责 API。
Alice : 发送 2 条 task-create 消息。
        → [general] task-create "Dashboard UI" assignee: alice
        → [general] task-create "Dashboard API" assignee: bob
        /end-turn
```

**Phase 2 — Bob 的回合（规划）**
```
Bob   : 检查聊天室... Alice 创建了 2 个任务。
        API 开发分配给了我。等机器人分配 ID 后再认领。
        这个阶段没有需要做的事情。
        /end-turn
```

**Phase 3 — 机器人**
```bash
$ python bot/turn-bot.py
[bot] Processed 2 messages:
  [task-create] T-001 — Dashboard UI
  [task-create] T-002 — Dashboard API
```
> T-001、T-002 已注册到 board.yaml。机器人在 general 中发送通知。

**Phase 4 — Alice 的回合（执行）**
```
Alice : 检查聊天室... 机器人注册了 T-001、T-002。
        检查看板... T-001（Dashboard UI）分配给我，状态：pending。
        开始 T-001。
        ...（编写 React 组件）...
        基本 UI 结构完成。
User  : 分享一下。
Alice : /report
        → [general] task-update T-001 status: in-progress "Basic layout done"
        → [alice-bob] message "请使用 /api/stats 格式的端点"
        /end-turn
```

**Phase 4 — Bob 的回合（执行）**
```
Bob   : 检查聊天室... Alice 正在处理 T-001，请求了 API 格式。
        检查看板... T-002（Dashboard API）分配给我，状态：pending。
        使用 /api/stats 端点开始 T-002。
        ...（编写 FastAPI 端点）...
        API 完成。
        /report
        → [general] task-done T-002 "API complete, includes /api/stats"
        → [alice-bob] message "API 已就绪。请调用 /api/stats"
        /end-turn
```

**Phase 5 — 机器人**
```bash
$ python bot/turn-bot.py
[bot] Processed 3 messages:
  [task-update] T-001 — in-progress
  [task-done] T-002 — done
```

### 第 2 回合

**Phase 1 — 机器人**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```

**Phase 2 — Alice 的回合**
```
Alice : 检查聊天室... Bob 完成了 API，/api/stats 可用。
        检查看板... T-001（UI）in-progress，T-002（API）done。
        认领 T-001 继续工作。
        → [general] task-claim T-001
        /end-turn
```

**Phase 2 — Bob 的回合**
```
Bob   : 检查聊天室... 没有新分配的任务。
        这一回合没有需要做的事情。
        /end-turn
```

> Bob 没有需要做的事情——直接结束回合。节省 token。

**Phase 3 — 机器人** → 反映认领。

**Phase 4 — Alice 的回合**
```
Alice : 集成 API 完成仪表盘。
        ...（fetch + 图表渲染）...
        /report
        → [general] task-done T-001 "API integration complete, dashboard done"
        /end-turn
```

**Phase 4 — Bob 的回合**
```
Bob   : 没有需要做的事情。
        /end-turn
```

**Phase 5 — 机器人** → T-001 标记为完成。所有任务完成！

## 设计原则

1. **角色分离** — 每个智能体有明确的职责
2. **回合制通信** — 每个回合按 规划 → 执行 → 报告 进行
3. **间接变更** — board.yaml 的变更仅通过聊天消息进行
4. **冲突预防** — 智能体只能追加写入，只有机器人可以写入 board.yaml
5. **独立执行** — 每个智能体独立工作，不依赖其他智能体

## 支持

如果你觉得这个项目有用，请给一个 star！这有助于更多人发现它。

## 许可证

MIT 许可证。自由使用。

## Star 历史

<a href="https://star-history.com/#southglory/system-agents-template&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
 </picture>
</a>
