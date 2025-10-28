import pandas as pd
import openpyxl # pandasがExcelの書き込みに内部で使用するため

# --- 設定 ---
FILE_PATH = 'answer_evaluated.xlsx'
START_ROW_READ = 3  # 0起点の行番号 (4行目 = 3)
N_ROWS_READ = 230   # 読み込む行数 (4行目から233行目まで = 230行)
USE_COLS = [0, 1, 8] # A列(0), B列(1), I列(8)
WRITE_START_ROW = 3 # 0起点の行番号 (L4セル = 3)
WRITE_START_COL = 11 # 0起点の列番号 (L列 = 11)
# ---

try:
    # 1. Excelファイルの指定範囲を読み込み
    # header=None: 1行目をヘッダーとして扱わない
    # skiprows: 指定した行数分スキップ (4行目から読み込むため3行スキップ)
    # usecols: 読み込む列を0始まりで指定
    # nrows: 読み込む行数を指定
    df = pd.read_excel(
        FILE_PATH,
        header=None,
        skiprows=START_ROW_READ,
        usecols=USE_COLS,
        nrows=N_ROWS_READ
    )
    
    # 列名を分かりやすいものに変更 (元の列番号に対応)
    df.columns = ['A', 'B', 'I']

    # 2. データの集計 (クロス集計)
    # A列とB列の全ての組み合わせをインデックス（行）とし、
    # I列の値（'正解', '不正解'）をカラム（列）として、それぞれの出現回数をカウント
    crosstab_result = pd.crosstab(
        index=[df['A'], df['B']],  # 行: A列とB列の組み合わせ
        columns=df['I'],            # 列: I列の値
        dropna=False                # NaNの組み合わせも集計対象に含める
    )

    # 3. 既存のExcelファイルに集計結果を書き込み
    
    # 既存のワークブックを読み込み、書き込み対象のシート名を取得
    # (pandasのExcelWriterで 'overlay' を使うため)
    try:
        wb = openpyxl.load_workbook(FILE_PATH)
        # 基本的に最初のシートを対象とする
        sheet_name = wb.sheetnames[0]
    except Exception as e:
        print(f"シート名の取得に失敗しました: {e}。デフォルトの 'Sheet1' を試します。")
        sheet_name = 'Sheet1'

    # ExcelWriterを '追記(append)' モードで開く
    # if_sheet_exists='overlay' で既存のシートに上書き（追記）
    with pd.ExcelWriter(
        FILE_PATH,
        mode='a',
        engine='openpyxl',
        if_sheet_exists='overlay'
    ) as writer:
        
        # 集計結果(DataFrame)をL4セルから書き出す
        # startrow, startcol は 0 始まり (L4 = 3行目, 11列目)
        crosstab_result.to_excel(
            writer,
            sheet_name=sheet_name,
            startrow=WRITE_START_ROW,
            startcol=WRITE_START_COL,
            index=True,  # A, B列の組み合わせ（MultiIndex）も書き出す
            header=True  # '正解', '不正解' のヘッダーも書き出す
        )

    print(f"集計が完了し、結果を '{FILE_PATH}' のシート '{sheet_name}' の L4 セルから書き込みました。")
    print("\n--- 集計結果のプレビュー ---")
    print(crosstab_result)
    print("----------------------------")

except FileNotFoundError:
    print(f"エラー: ファイル '{FILE_PATH}' が見つかりませんでした。")
except ImportError:
    print("エラー: 'pandas' または 'openpyxl' ライブラリがインストールされていません。")
    print("pip install pandas openpyxl")
except PermissionError:
    print(f"エラー: ファイル '{FILE_PATH}' への書き込み権限がありません。ファイルが開かれていないか確認してください。")
except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")
    print("指定した列番号や行範囲が正しいか、Excelファイルの内容を確認してください。")