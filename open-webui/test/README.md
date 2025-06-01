# OpenWebUI Claude Code Function Tests

このディレクトリには、`claude-code.py` OpenWebUI関数のテストスイートが含まれています。

## 特定された問題

セッションログデータから以下の問題が特定されました：

1. **セッション管理の問題**: セッション更新時の処理 (`claude-code.py:57-60`)
2. **JSON解析の問題**: 非JSONライン処理 (`claude-code.py:124-234`) 
3. **バッファリング問題**: 不完全なJSONデータの処理 (`claude-code.py:123-132`)
4. **Thinking表示の問題**: タグの開閉処理

## テストファイル

- `test_claude_code.py`: 基本的な機能テスト
- `test_session_issues.py`: セッション管理に特化したテスト

## セットアップ

1. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

2. テストを実行:
```bash
# すべてのテストを実行
pytest

# 詳細出力でテスト実行
pytest -v

# 特定のテストファイルのみ実行
pytest test_claude_code.py
pytest test_session_issues.py

# 特定のテストケースのみ実行
pytest test_session_issues.py::TestSessionIssues::test_session_resume_scenario
```

## テストカバレッジ

### 基本機能テスト (`test_claude_code.py`)
- パイプの初期化
- 空メッセージ処理
- セッションID抽出
- 設定の継承
- JSON解析とバッファリング
- 非JSONライン処理
- Thinkingタグ管理
- エラーレスポンス処理
- コンテンツ切り詰め
- ツール使用表示

### セッション問題テスト (`test_session_issues.py`)
- セッション再開シナリオ
- ログからの実際の非JSONライン処理
- 部分JSON バッファリング
- ストリーミング中のエラー回復
- Thinking表示の破綻問題
- 複雑な設定継承
- Unicode文字処理

## ログデータから特定された具体的な問題

### 1. セッション更新
```
Updating session after resume: 17398555-6e9c-4b13-a0b9-345589f13dda -> 54281ff0-bffa-497e-9526-fa641fe91478
```

### 2. 非JSONライン処理
```
Non-JSON line: "💭 Thought for X seconds" panels
```

### 3. Thinking表示の問題
- `<thinking>`タグが正しく閉じられない
- UIでのデフォルト表示状態の問題

## 実行例

```bash
# テスト実行
cd /home/kohei/workspace/claude-code-server/open-webui/test
python -m pytest test_claude_code.py -v

# 特定の問題のテスト
python -m pytest test_session_issues.py::TestSessionIssues::test_non_json_line_from_logs -v
```

## 期待される結果

すべてのテストがパスすれば、`claude-code.py`の基本機能とエラーハンドリングが正常に動作していることが確認できます。失敗したテストは、実装の改善が必要な箇所を示します。