import os
import json
import sys
import time # スリープ処理
import openpyxl # Excel操作用
from dotenv import load_dotenv # .env ファイル読み込み
from utils import (
    ChatGPT_API,      # LLM呼び出し
    extract_json      # JSON抽出用
)

# --- 0. 準備 (環境変数の読み込み) ---
load_dotenv()

# --- ▼▼▼ ユーザー設定 ▼▼▼ ---

# 1. 評価対象のExcelファイル
# (G列: 模範解答, H列: 生成回答 が入力済みのファイル)
EVALUATION_EXCEL_PATH = './answer_evaluated.xlsx'

# 2. 評価に使用するLLMモデル名 (Azure Deployment名など)
MODEL_NAME = "gpt-4o" 

# 3. レートリミット対策: 各評価間の待機時間（秒）
SLEEP_BETWEEN_QUERIES = 2

# 4. 処理対象の行範囲 (Excelの行番号)
START_ROW = 4
END_ROW = 233

# --- ▲▲▲ ユーザー設定 ▲▲▲ ---


def evaluate_answer(generated_answer, model_answer, model):
    """
    AIを使って生成回答と模範解答を比較評価する
    
    Args:
        generated_answer (str): RAGパイプラインが生成した回答
        model_answer (str): 人間が用意した模範解答
        model (str): 評価に使用するLLMモデル名
        
    Returns:
        tuple: (binary_score, consistency_score)
               例: ("正解", 0.9) または ("評価エラー", 0.0)
    """
    print(f"\n--- 回答評価 開始 ---")
    
    # どちらかが空の場合は評価不能
    if not generated_answer or not model_answer:
        print("生成回答または模範解答が空のため、評価をスキップします。")
        return "評価不能", 0.0

    print(f"生成回答 (H列): {generated_answer[:100]}...") # 長すぎる場合があるので冒頭のみ表示
    print(f"模範回答 (G列): {model_answer[:100]}...")

    # 「情報が見つかりません」系の回答の場合は、AI評価をスキップ
    # (ただし、模範解答も「情報なし」の場合は正解とする必要があるかもしれないが、
    #  元のコードのロジックに基づき、生成回答が「情報なし」なら「不正解」とする)
    not_found_keywords = ["情報が見つかりません", "関連情報がありません", "コンテキストに記載がありません", "関連ノードは特定できませんでした"]
    if any(keyword in generated_answer for keyword in not_found_keywords):
        print("生成回答が「情報なし」のため、「不正解」として扱います。")
        return "不正解", 0.0 # 不正解、一致率0とする

    prompt = f"""
    以下の「模範解答」と「生成された回答」を比較し、評価してください。

    ## 模範解答:
    {model_answer}

    ## 生成された回答:
    {generated_answer}

    ## 評価基準:
    1.  **正誤判定 (binary_score):** 「生成された回答」が「模範解答」の意図や主要な情報を正しく捉え、実質的に同じ結論に至っているか。完全に一致する必要はないが、重要な情報が欠けていたり、誤った情報が含まれていれば「不正解」。
        - "正解" または "不正解" で回答してください。
    2.  **一致率 (consistency_score):** 「生成された回答」が「模範解答」とどの程度内容的に一致しているかを示す0.0から1.0の間の数値。表現の違いは許容するが、情報の網羅性や正確性を考慮してください。ちょっと甘めに評価して。つまり、模範解答の部分が少しでもあれば、0.6以上としていい。
        - 例: 完全に一致なら1.0、半分程度なら0.5、全く異なるなら0.0

    ## 回答フォーマット:
    評価結果を以下のJSON形式で返してください。

    {{
      "binary_score": "<"正解" または "不正解">",
      "consistency_score": <0.0から1.0の数値>
    }}
    """
    
    try:
        response_str = ChatGPT_API(model=model, prompt=prompt)
        print(f"評価AI応答: {response_str}")
        evaluation = extract_json(response_str) # utilsの関数を利用
        
        binary_score = evaluation.get("binary_score", "評価エラー")
        consistency_score = evaluation.get("consistency_score", 0.0)

        # スコアの型と範囲を念のためチェック
        if not isinstance(consistency_score, (int, float)):
            consistency_score = 0.0
        
        # 0.0-1.0の範囲に収める
        consistency_score = max(0.0, min(1.0, float(consistency_score))) 

        return binary_score, consistency_score

    except Exception as e:
        print(f"エラー: 回答評価中にエラーが発生しました。 {e}")
        return "評価エラー", 0.0


def main():
    """
    Excelを読み込み、G列とH列を比較評価し、I列とJ列に書き込む
    """

    print("--- AIによる回答評価モジュール開始 ---")
    print(f"評価対象Excel: {EVALUATION_EXCEL_PATH}")
    print(f"使用モデル: {MODEL_NAME}")
    
    # --- Excel準備 ---
    try:
        workbook = openpyxl.load_workbook(EVALUATION_EXCEL_PATH)
        sheet = workbook.active # 最初のシートを対象とする
        print(f"Excelファイル '{EVALUATION_EXCEL_PATH}' を読み込みました。")
    except FileNotFoundError:
        print(f"エラー: Excelファイルが見つかりません: {EVALUATION_EXCEL_PATH}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: Excelファイルの読み込み中にエラーが発生しました。 {e}")
        sys.exit(1)

    # --- 評価ループ実行 ---
    print(f"\n--- 評価実行ループ開始 ({START_ROW}行目から{END_ROW}行目まで) ---")

    for row_index in range(START_ROW, END_ROW + 1):
        
        # G列（模範解答）と H列（生成回答）を読み込む
        model_answer = sheet[f'G{row_index}'].value
        generated_answer = sheet[f'H{row_index}'].value

        print("\n" + "="*50)
        print(f"評価中: {row_index}行目")
        print("="*50)

        # AIによる評価を実行
        binary_score, consistency_score = evaluate_answer(
            generated_answer, 
            model_answer, 
            MODEL_NAME
        )

        # 結果をExcel (I列, J列) に書き込み
        sheet[f'I{row_index}'] = binary_score
        sheet[f'J{row_index}'] = consistency_score
        print(f"評価結果を I{row_index}='{binary_score}', J{row_index}={consistency_score} に書き込みました。")

        # レートリミット対策のスリープ (評価API用)
        print(f"{SLEEP_BETWEEN_QUERIES}秒待機します...")
        time.sleep(SLEEP_BETWEEN_QUERIES)

    # --- Excelファイルを保存 ---
    try:
        # 読み込んだファイルに上書き保存
        workbook.save(EVALUATION_EXCEL_PATH)
        print("\n" + "="*50)
        print(f"評価結果を '{EVALUATION_EXCEL_PATH}' に上書き保存しました。")
        print("="*50)
    except PermissionError:
        print(f"エラー: ファイル '{EVALUATION_EXCEL_PATH}' に書き込めません。ファイルが開かれていないか確認してください。")
    except Exception as e:
        print(f"エラー: Excelファイルの保存中にエラーが発生しました。 {e}")


if __name__ == "__main__":
    main()