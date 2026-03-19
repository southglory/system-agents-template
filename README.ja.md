# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

Claude Code上に構築されたターンベースのマルチエージェントフレームワークです。

各エージェントは独立したClaude Codeセッションとして実行され、チャットルームを通じて通信し、ボットがタスクボードを自動管理します。

## 構成

```
system-agents/
├── agents/
│   ├── _example/              ← エージェントテンプレート
│   │   ├── CLAUDE.md          ← 動作ルール（フェーズごと）
│   │   └── role.md            ← 役割定義
│   └── {AgentName}/           ← あなたのエージェント
├── chatrooms/
│   ├── PROTOCOL.md            ← チャットプロトコル（メッセージタイプ）
│   ├── .read-status/          ← 既読ステータス追跡
│   └── general/               ← 共有チャンネル
├── tasks/
│   ├── PROTOCOL.md            ← タスク管理プロトコル
│   └── board.yaml             ← タスクボード（ボット書き込み専用）
├── bot/
│   ├── turn-bot.py            ← ターンボットスクリプト
│   └── requirements.txt
├── skills/
│   ├── check-chatroom/        ← 未読メッセージ確認
│   ├── check-mentions/        ← メンション確認
│   ├── send-message/          ← メッセージ送信（タイプ検証）
│   ├── end-turn/              ← ターン終了
│   └── report/                ← 作業結果の自動共有
└── README.md
```

## ターンベース運用

エージェントは自由に並行実行されません。**ラウンド**ごとに順次実行されます。

```
=== ラウンド N ===

[フェーズ 1: ボット]  board.yamlを更新（前ラウンドのメッセージを反映）

[フェーズ 2: 計画] （エージェントが順次実行）
  各エージェント → メッセージ確認 + タスク取得（task-claim）

[フェーズ 3: ボット]  board.yamlを更新（取得を反映）

[フェーズ 4: 実行] （エージェントが順次実行）
  各エージェント → 実作業 + 結果メッセージ送信

[フェーズ 5: ボット]  board.yamlを更新（結果を反映）

=== ラウンド N+1 ===
```

## クイックスタート

### 1. スキルのインストール

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. エージェントの作成

```bash
cp -r agents/_example agents/MyAgent
```

`role.md`で役割を定義し、`CLAUDE.md`でルールを定義します。

### 3. ラウンドの実行

```bash
# フェーズ 1: ボット
python bot/turn-bot.py

# フェーズ 2: 各エージェントが計画（フェーズ自動検出）
cd agents/AgentA && claude
cd agents/AgentB && claude

# フェーズ 3: ボット
python bot/turn-bot.py

# フェーズ 4: 各エージェントが実行（フェーズ自動検出）
cd agents/AgentA && claude
cd agents/AgentB && claude

# フェーズ 5: ボット
python bot/turn-bot.py
```

## コアコンセプト

### エージェント
- 独立したClaude Codeセッションとして実行
- フェーズ2で計画、フェーズ4で実行
- board.yamlは読み取り専用 — 変更はチャットメッセージを通じて行う

### チャットルーム
- ファイルベースの非同期メッセージング
- メッセージタイプで会話とタスクコマンドを区別
- 添付ファイルサポート

### メッセージタイプ

| type | 用途 |
|------|------|
| `message` | 一般的な会話 |
| `task-create` | 新規タスクのリクエスト |
| `task-update` | ステータス/担当者の変更 |
| `task-done` | タスク完了の報告 |
| `task-claim` | タスクの取得（フェーズ2） |
| `turn-end` | ターン終了 |

### ボット
- board.yamlへの唯一の書き込み権限を持つ
- チャットルームのメッセージ（task-*）をスキャンしてboard.yamlを更新
- task-create時にID（T-001）を割り当て、確認メッセージを送信

### スキル
- `/check-chatroom {room}` — 未読メッセージの確認
- `/check-mentions` — 自分へのメンションの確認
- `/send-message {room}` — メッセージ送信（タイプ検証付き）
- `/end-turn` — ターンの終了
- `/report` — 関連チャットルームへの作業結果の自動共有

## シナリオ：ラウンドプレイ

Alice（フロントエンド）とBob（バックエンド）が一緒にダッシュボードを構築します。

### ラウンド 1

**フェーズ 1 — ボット**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```
> 最初のラウンドです。ボードは空です。

**フェーズ 2 — Aliceのターン（計画）**
```
Alice : チャットルームを確認中... 新しいメッセージはありません。
        ボードを確認中... タスクはありません。
        新しいタスクが必要です。
User  : ダッシュボードが必要です。フロントエンドはあなた、APIはBobが担当してください。
Alice : task-createメッセージを2件送信します。
        → [general] task-create "Dashboard UI" assignee: alice
        → [general] task-create "Dashboard API" assignee: bob
        /end-turn
```

**フェーズ 2 — Bobのターン（計画）**
```
Bob   : チャットルームを確認中... Aliceが2つのタスクを作成しました。
        API開発は私に割り当てられています。ボットがIDを割り当てた後に取得します。
        このフェーズでやることはありません。
        /end-turn
```

**フェーズ 3 — ボット**
```bash
$ python bot/turn-bot.py
[bot] Processed 2 messages:
  [task-create] T-001 — Dashboard UI
  [task-create] T-002 — Dashboard API
```
> T-001、T-002がboard.yamlに登録されました。ボットがgeneralで通知します。

**フェーズ 4 — Aliceのターン（実行）**
```
Alice : チャットルームを確認中... ボットがT-001、T-002を登録しました。
        ボードを確認中... T-001（Dashboard UI）が私に割り当て、ステータス: pending。
        T-001を開始します。
        ...（Reactコンポーネントを作成中）...
        基本的なUI構造が完了しました。
User  : 共有してください。
Alice : /report
        → [general] task-update T-001 status: in-progress "基本レイアウト完了"
        → [alice-bob] message "エンドポイントは /api/stats 形式でお願いします"
        /end-turn
```

**フェーズ 4 — Bobのターン（実行）**
```
Bob   : チャットルームを確認中... AliceがT-001を作業中、APIフォーマットをリクエスト。
        ボードを確認中... T-002（Dashboard API）が私に割り当て、ステータス: pending。
        /api/statsエンドポイントでT-002を開始します。
        ...（FastAPIエンドポイントを作成中）...
        API完了。
        /report
        → [general] task-done T-002 "API完了、/api/stats含む"
        → [alice-bob] message "APIが稼働中です。/api/statsを呼び出してください"
        /end-turn
```

**フェーズ 5 — ボット**
```bash
$ python bot/turn-bot.py
[bot] Processed 3 messages:
  [task-update] T-001 — in-progress
  [task-done] T-002 — done
```

### ラウンド 2

**フェーズ 1 — ボット**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```

**フェーズ 2 — Aliceのターン**
```
Alice : チャットルームを確認中... BobがAPIを完了、/api/statsが利用可能。
        ボードを確認中... T-001（UI）in-progress、T-002（API）done。
        T-001を引き続き作業するため取得します。
        → [general] task-claim T-001
        /end-turn
```

**フェーズ 2 — Bobのターン**
```
Bob   : チャットルームを確認中... 新しく割り当てられたタスクはありません。
        今ラウンドはやることがありません。
        /end-turn
```

> Bobはやることがありません — ターンを終了するだけです。トークンの節約になります。

**フェーズ 3 — ボット** → 取得を反映。

**フェーズ 4 — Aliceのターン**
```
Alice : APIを統合してダッシュボードを完成させます。
        ...（fetch + チャートレンダリング）...
        /report
        → [general] task-done T-001 "API統合完了、ダッシュボード完成"
        /end-turn
```

**フェーズ 4 — Bobのターン**
```
Bob   : やることはありません。
        /end-turn
```

**フェーズ 5 — ボット** → T-001がdoneに。すべてのタスクが完了しました！

## 設計原則

1. **役割分離** — 各エージェントは明確な責任を持つ
2. **ターンベースのコミュニケーション** — ラウンドごとに計画 → 実行 → 報告
3. **間接的な変更** — board.yamlの変更はチャットメッセージを通じてのみ行う
4. **競合の防止** — エージェントは追記のみ、board.yamlへの書き込みはボットのみ
5. **独立した実行** — 各エージェントは他に依存せず動作する

## サポート

このプロジェクトが役に立ったら、ぜひスターを付けてください！他の方がプロジェクトを見つけやすくなります。

## ライセンス

MITライセンス。自由にご利用ください。

## Star History

<a href="https://star-history.com/#southglory/system-agents-template&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
 </picture>
</a>
