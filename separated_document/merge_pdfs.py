import os
from PyPDF2 import PdfMerger

# --- 設定項目 ---

# 1. PDFファイルが保存されているディレクトリのパスを指定
# (例: "C:/Users/Taku/Documents/MyPDFs" や "pdfs_to_merge")
pdf_directory = "test" 

# 2. 結合後に保存するファイル名を指定
output_filename = "merged_document.pdf"

# --- ここから処理 ---

# 指定したディレクトリが存在するかチェック
if not os.path.isdir(pdf_directory):
    print(f"エラー: ディレクトリ '{pdf_directory}' が見つかりません。")
    print("pdf_directory のパスを正しく設定してください。")
else:
    # 3. ディレクトリ内のPDFファイルを取得し、名前順にソート
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    pdf_files.sort()

    if not pdf_files:
        print(f"ディレクトリ '{pdf_directory}' にPDFファイルが見つかりませんでした。")
    else:
        # 4. PdfMergerオブジェクトを作成
        merger = PdfMerger()

        print("以下のファイルをこの順序で結合します:")
        
        # 5. ソートされたファイルを順番に結合オブジェクトに追加
        for filename in pdf_files:
            filepath = os.path.join(pdf_directory, filename)
            print(f"  -> {filename}")
            
            # 各PDFファイルを読み込んでmergerに追加
            merger.append(filepath) 

        # 6. 結合した内容を新しいファイルに書き出し
        #    （この時点で元のファイルは一切変更されていません）
        try:
            merger.write(output_filename)
            print(f"\n✅ 結合が完了しました！")
            print(f"'{output_filename}' として保存されました。")
            print("（元のPDFファイルは全て残されています）")

        except Exception as e:
            print(f"\n❌ エラー: ファイルの書き込みに失敗しました。")
            print(f"詳細: {e}")

        finally:
            # 7. オブジェクトを閉じる
            merger.close()