import sys
from pathlib import Path

# --- 設定 ---
# 処理対象のサブフォルダ名
MD_FOLDER_NAME = "md_folder"

# 結合後の出力ファイル名
# （スクリプトと同じ階層に出力されます）
OUTPUT_FILENAME = "combined_markdown.md"
# ----------------

# 1. カレントディレクトリと対象フォルダのパスを特定
current_dir = Path.cwd()
target_dir = current_dir / MD_FOLDER_NAME

print(f"作業ディレクトリ: {current_dir}")
print(f"処理対象フォルダ: {target_dir}")
print("---")

# 2. 'md_folder' が存在するかチェック
if not target_dir.is_dir():
    print(f"❌ エラー: '{MD_FOLDER_NAME}' フォルダが見つかりません。")
    print("スクリプトを実行するディレクトリが正しいか確認してください。")
    sys.exit(1) # スクリプトを終了

# 3. 'md_folder' 内のすべての .md ファイルを再帰的に検索
#    (.rglob() を使うので、サブフォルダ内の .md も対象になります)
print(f"🔍 '{MD_FOLDER_NAME}' 内の .md ファイルを検索中...")
try:
    md_files = list(target_dir.rglob("*.md"))
except Exception as e:
    print(f"❌ エラー: ファイル検索中にエラーが発生しました: {e}")
    sys.exit(1)

# 4. 見つかったファイルを名前順 (フルパスの文字列順) にソート
sorted_md_files = sorted(md_files)

if not sorted_md_files:
    print(f"✅ 処理完了: '{MD_FOLDER_NAME}' 内に .md ファイルが見つかりませんでした。")
    sys.exit(0)

print(f"✅ {len(sorted_md_files)} 個の .md ファイルを発見。名前順に結合します...")

# 5. 出力ファイルを書き込みモード ( 'w' ) で開く
#    出力先はスクリプトと同じカレントディレクトリ
output_file_path = current_dir / OUTPUT_FILENAME

try:
    with output_file_path.open("w", encoding="utf-8") as outfile:
        
        for md_file in sorted_md_files:
            relative_path = md_file.relative_to(current_dir)
            print(f"  -> {relative_path} を追加中...")
            
            try:
                # 6. 各mdファイルを読み込み (元のファイルは変更しない)
                content = md_file.read_text(encoding="utf-8")
                
                # 7. 読み込んだ内容を結合先ファイルに書き込み
                outfile.write(content)
                
                # 8. ファイルとファイルの間に区切りとして改行を2つ追加
                #    (Markdownとして正しく段落が分かれるようにするため)
                outfile.write("\n\n")
                
            except UnicodeDecodeError:
                print(f"  ❌ 警告: {relative_path} は 'utf-8' で読み込めませんでした。スキップします。")
            except Exception as e:
                print(f"  ❌ 警告: {relative_path} の処理中に予期せぬエラーが発生しました: {e}")

    print("---")
    print(f"🎉 成功: {len(sorted_md_files)} 個のファイルを '{OUTPUT_FILENAME}' に結合しました。")
    print(f"（元の .md ファイルは {MD_FOLDER_NAME} に残っています）")

except Exception as e:
    print(f"❌ エラー: 出力ファイル '{output_file_path}' の書き込みに失敗しました: {e}")
    sys.exit(1)