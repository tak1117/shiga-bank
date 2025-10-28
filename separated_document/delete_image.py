import sys
from pathlib import Path

# --- 設定 ---
# 処理対象のサブフォルダ名
MD_FOLDER_NAME = "md_folder"

# 削除する行の「始まりの文字列」
# この文字列で始まる行は、ファイルから削除されます
BAD_LINE_PREFIX = "![Image](data:image/"
# -------------

# 1. スクリプトを実行したカレントディレクトリを取得
current_dir = Path.cwd()

# 2. 処理対象の 'md_folder' のパスを特定
target_dir = current_dir / MD_FOLDER_NAME

print(f"作業ディレクトリ: {current_dir}")
print(f"処理対象フォルダ: {target_dir}")
print("---")

# 3. 'md_folder' が存在するかチェック
if not target_dir.is_dir():
    print(f"❌ エラー: '{MD_FOLDER_NAME}' フォルダが見つかりません。")
    print("スクリプトを実行するディレクトリが正しいか確認してください。")
    sys.exit(1) # スクリプトを終了

# 4. 'md_folder' 内のすべての .md ファイルを再帰的に検索
#    (.rglob を使うので、サブフォルダ内の .md も対象になります)
try:
    md_files = list(target_dir.rglob("*.md"))
except Exception as e:
    print(f"❌ エラー: ファイル検索中にエラーが発生しました: {e}")
    sys.exit(1)

if not md_files:
    print(f"✅ 処理完了: '{MD_FOLDER_NAME}' 内に .md ファイルが見つかりませんでした。")
    sys.exit(0)

print(f"🔍 {len(md_files)} 個の .md ファイルを発見しました。各ファイルをチェックします...")
print("---")

modified_file_count = 0

# 5. 各 .md ファイルを処理
for md_file in md_files:
    # ファイルパスをカレントディレクトリからの相対パスで表示
    relative_path = md_file.relative_to(current_dir)
    
    try:
        # 6. ファイルを行ごとに読み込む (改行コードも保持)
        #    エンコーディングは 'utf-8' を仮定 (Markdownでは一般的)
        with md_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        # 7. 削除対象の行を除外した新しい行リストを作成
        new_lines = []
        file_was_modified = False
        
        for line in lines:
            # strip() で行頭の空白を無視し、startswith で判定
            if line.strip().startswith(BAD_LINE_PREFIX):
                file_was_modified = True
                # この行は new_lines に追加しない (＝削除)
            else:
                new_lines.append(line)

        # 8. もし変更があった場合のみ、ファイルを上書き保存
        if file_was_modified:
            with md_file.open("w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"✏️  変更あり: {relative_path} から該当行を削除しました。")
            modified_file_count += 1
        else:
            # 詳細ログが不要な場合はこの行をコメントアウトしてください
            print(f"✓  変更なし: {relative_path} には該当行はありませんでした。")

    except UnicodeDecodeError:
        print(f"❌ エラー: {relative_path} は 'utf-8' で読み込めませんでした。スキップします。")
    except Exception as e:
        print(f"❌ エラー: {relative_path} の処理中に予期せぬエラーが発生しました: {e}")

print("---")
print(f"🎉 処理完了: 合計 {modified_file_count} 個のファイルを変更しました。")