import os
import json
import sys
import math
import time 
import openpyxl 
from dotenv import load_dotenv
from utils import (
    ChatGPT_API,
    get_page_tokens,        
    get_text_of_pdf_pages, 
    structure_to_list,
    count_tokens,           
    print_json,             
    extract_json            
)

# --- 0. 準備 (環境変数の読み込み) ---
load_dotenv()

JSON_STRUCTURE_PATH = '../results/merged_structure.json' 
ORIGINAL_PDF_PATH = './merged.pdf'
EXCEL_PATH = './answer.xlsx'
MODEL_NAME = "gpt-4o"
MAX_TOKENS_PER_CHUNK = 100000
SLEEP_BETWEEN_QUERIES = 2


def load_json_structure(path):
    """生成済みのJSON構造ファイルを読み込む"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"エラー: JSONファイルが見つかりません: {path}")
        print("先に `run_pageindex.py --pdf_path ...` を実行して、JSON構造ファイルを生成してください。")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"エラー: JSONファイルの形式が正しくありません: {path}")
        sys.exit(1)

def find_node_by_id(structure_list, node_id):
    """フラットリストから指定されたnode_idのノードを検索する"""
    for node in structure_list:
        if node.get('node_id') == node_id:
            return node
    return None

def create_searchable_toc(structure_list):
    """LLMが検索しやすいように、ツリー構造を簡略化（TOC化）する"""
    toc = []
    for node in structure_list:
        toc_entry = {
            "node_id": node.get("node_id"),
            "title": node.get("title"),
            "summary": node.get("summary", node.get("prefix_summary"))
        }
        entry_str = json.dumps(toc_entry, ensure_ascii=False)
        toc_entry['_tokens'] = count_tokens(entry_str, model=MODEL_NAME)
        toc.append(toc_entry)
    return toc

# ステップ1は「全チャンク走査版」をそのまま利用
def step1_tree_search_retrieval(toc, query, model, max_tokens_per_chunk):
    """
    ステップ1: Reasoning-based Retrieval (Tree Search)
    TOCが巨大な場合、チャンクに分割し、関連する可能性のある全てのnode_idを収集する
    """
    print(f"\n--- ステップ1: Tree Search (Retrieval) 開始 ---")
    toc_chunks = []
    current_chunk = []
    current_tokens = 0
    for entry in toc:
        entry_tokens = entry.get('_tokens', 0)
        if current_tokens + entry_tokens > max_tokens_per_chunk and current_chunk:
            toc_chunks.append(current_chunk)
            current_chunk = [entry]
            current_tokens = entry_tokens
        else:
            current_chunk.append(entry)
            current_tokens += entry_tokens
    if current_chunk:
        toc_chunks.append(current_chunk)

    if len(toc_chunks) > 1:
        print(f"TOCが{len(toc_chunks)}個のチャンクに分割されました。")
    else:
        print("TOCを1つのチャンクとして検索します。")

    retrieved_node_ids = []
    base_prompt_template = f"""
    あなたは、文書構造（目次）を理解し、ユーザーの質問に答えるために必要な箇所を特定する専門家です。
    以下の文書構造（簡略化された目次の一部）とユーザーの質問を読み、質問に答えるために最も関連性が高いと思われるセクションの `node_id` を1つだけ特定してください。
    もし関連するセクションがこのチャンク（目次の一部）に **含まれていない場合は、"NA" とだけ回答してください。**

    ## 文書構造 (TOCチャンク):
    {{toc_chunk_json}}

    ## ユーザーの質問:
    {query}

    ## 回答フォーマット:
    関連する `node_id`（例: "0123"）を1つだけ返すか、見つからなければ "NA" とだけ返してください。
    余計な思考プロセスやJSON形式は不要です。 node_idは4桁の数字です。
    """

    for i, chunk in enumerate(toc_chunks):
        print(f"\nチャンク {i+1}/{len(toc_chunks)} を検索中...")
        clean_chunk = [{k: v for k, v in entry.items() if k != '_tokens'} for entry in chunk]
        chunk_json = json.dumps(clean_chunk, indent=2, ensure_ascii=False)
        prompt = base_prompt_template.format(toc_chunk_json=chunk_json)

        response_str = ChatGPT_API(model=model, prompt=prompt)
        print(f"LLM応答: {response_str}")

        response_str = response_str.strip().replace('"', '').replace('node_id_', '')
        if response_str != "NA" and response_str.isdigit() and len(response_str) == 4:
            print(f"関連ノード候補発見: {response_str}")
            if response_str not in retrieved_node_ids:
                 retrieved_node_ids.append(response_str)
        else:
            print("このチャンクに関連ノードは見つかりませんでした。")

    if not retrieved_node_ids:
        print("エラー: 全てのTOCチャンクを検索しましたが、関連するノードが見つかりませんでした。")
        return []
    else:
        print(f"\n関連する可能性のあるノードID: {retrieved_node_ids}")
        return retrieved_node_ids


def step2_generation(context, query, model):
    """
    ステップ2: Augmentation & Generation
    取得した「コンテキスト（文脈）」と「質問」をLLMに渡し、最終的な回答を生成させる
    """
    print(f"\n--- ステップ2: Generation (回答生成) 開始 ---")
    prompt = f"""
    あなたは非常に優秀で厳密なテキスト解析エージェントです。以下のルールに従い、与えられた「コンテキスト（文書からの抜粋）」を精密に読み取り、ユーザーの「質問」に対してできる限り具体的かつ正確な回答を生成してください。

    【重要なルール】
    1. 回答は必ず「以下のコンテキスト」に含まれる情報のみに基づいて行ってください。推測、一般常識、外部知識、他の文書、モデルの訓練知識などに基づいて補完してはいけません。
    2. コンテキストに明示的な情報が存在しない場合、もしくは回答を導くのに十分な根拠がない場合は、必ず「情報が見つかりません」と回答してください。
    3. 回答の内容は、曖昧な表現（「おそらく」「〜と思われる」「〜かもしれない」など）を避け、可能な限り断定的かつ明確に記述してください。ただし、断定できない場合は「情報が見つかりません」と明示してください。
    4. 回答文中では、文体を丁寧で自然な日本語に統一し、余分な装飾語や説明を付け加えないでください。
    5. もしコンテキストに複数の情報が含まれており、それらが矛盾している場合は、最も信頼性が高い・明示的な情報を優先し、それを根拠として回答してください。
    6. コンテキストに日付、人物名、数値、箇条書き、表、引用などが含まれている場合は、該当部分を正確に読み取り、誤記なく回答に反映してください。
    7. 回答には、原文の意味を忠実に保ったうえで、必要に応じて文を整えたり、要約したりしても構いません。ただし、削除や改ざんは行わないでください。
    8. 「質問」に複数の意図が含まれている場合は、それぞれの要素に対して分かりやすく順序立てて回答してください。

    【目的】
    このプロンプトの目的は、入力された文書抜粋（コンテキスト）から、完全に根拠のある情報だけを抽出・整理し、ユーザーの質問に対して精緻で論理的な回答を行うことです。
    あなたの役割は、質問応答AIとしてではなく、文書理解の専門家・ファクトチェッカー・情報抽出エンジンとしての厳密な姿勢を保つことです。

    【出力フォーマット】
    出力は以下の形式を厳守してください。

    ---
    【回答】
    （質問に対する具体的な答えを1つの段落で述べる）

    【根拠】
    （回答の根拠となるコンテキスト中の該当箇所を引用または要約して明示する）
    ---

    以下に解析対象の情報を示します。

    ▼ コンテキスト（文書からの抜粋）:
    {context}

    ▼ ユーザーの質問:
    {query}
    """

    answer = ChatGPT_API(model=model, prompt=prompt)
    return answer

def evaluate_answer(generated_answer, model_answer, model):
    """AIを使って生成回答と模範解答を比較評価する"""
    print(f"\n--- 回答評価 開始 ---")
    print(f"生成回答: {generated_answer[:100]}...") # 長すぎる場合があるので冒頭のみ表示
    print(f"模範回答: {model_answer[:100]}...")

    # 「情報が見つかりません」系の回答の場合は、AI評価をスキップ
    not_found_keywords = ["情報が見つかりません", "関連情報がありません", "コンテキストに記載がありません"]
    if any(keyword in generated_answer for keyword in not_found_keywords):
        print("生成回答が「情報なし」のため、評価をスキップします。")
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
    2.  **一致率 (consistency_score):** 「生成された回答」が「模範解答」とどの程度内容的に一致しているかを示す0.0から1.0の間の数値。表現の違いは許容するが、情報の網羅性や正確性を考慮してください。
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
        consistency_score = max(0.0, min(1.0, float(consistency_score))) # 0.0-1.0の範囲に収める

        return binary_score, consistency_score

    except Exception as e:
        print(f"エラー: 回答評価中にエラーが発生しました。 {e}")
        return "評価エラー", 0.0


def run_rag_pipeline(query, structure_list, pdf_page_list):
    """単一の質問に対してRAGパイプラインを実行し、回答を返す"""

    # --- ステップ1: Retrieval ---
    searchable_toc = create_searchable_toc(structure_list)
    retrieved_node_ids = step1_tree_search_retrieval(
        toc=searchable_toc,
        query=query,
        model=MODEL_NAME,
        max_tokens_per_chunk=MAX_TOKENS_PER_CHUNK
    )

    if not retrieved_node_ids:
        return "関連情報が見つかりませんでした。" # ステップ1で見つからない場合の回答

    # --- ステップ2: Augmentation & Generation ---
    all_contexts = []
    print("\n--- 関連ノードのコンテキストを取得中 ---")
    for node_id in retrieved_node_ids:
        target_node = find_node_by_id(structure_list, node_id)
        if not target_node:
            print(f"警告: 取得した node_id '{node_id}' が見つかりません。スキップ。")
            continue

        start_page = target_node.get('start_index')
        end_page = target_node.get('end_index')

        if start_page is None or end_page is None:
            print(f"  エラー: ノード {node_id} にページ範囲がありません。スキップ。")
            continue
        else:
            print(f"  Node ID: {node_id}, ページ範囲: {start_page}-{end_page}")
            context = get_text_of_pdf_pages(
                pdf_pages=pdf_page_list,
                start_page=start_page,
                end_page=end_page
            )
            all_contexts.append(context)

    if not all_contexts:
        return "関連ノードは特定できましたが、コンテキストの取得に失敗しました。"

    combined_context = "\n\n---\n\n".join(all_contexts)
    combined_context_tokens = count_tokens(combined_context, model=MODEL_NAME)
    print(f"\n--- 全コンテキスト結合完了 (合計 {combined_context_tokens} トークン) ---")

    generation_token_limit = MAX_TOKENS_PER_CHUNK
    if combined_context_tokens > generation_token_limit:
        print(f"警告: 結合コンテキスト({combined_context_tokens} トークン)が上限超えの可能性。")
        # TODO: コンテキストの要約/切り捨て処理が必要な場合

    final_answer = step2_generation(
        context=combined_context,
        query=query,
        model=MODEL_NAME
    )
    return final_answer


def main():
    """Excelを読み込み、RAG実行と評価を行うメイン処理"""

    print("--- PageIndex RAG 評価パイプライン開始 ---")
    print(f"Excel: {EXCEL_PATH}")
    print(f"PDF: {ORIGINAL_PDF_PATH}")
    print(f"JSON Structure: {JSON_STRUCTURE_PATH}")

    structure_json = load_json_structure(JSON_STRUCTURE_PATH)
    doc_structure = structure_json.get('structure', [])
    structure_list = structure_to_list(doc_structure)

    print("\n元のPDFを読み込んでいます...")
    try:
        pdf_page_list = get_page_tokens(ORIGINAL_PDF_PATH, model=MODEL_NAME)
        print(f"PDF読み込み完了。 (全{len(pdf_page_list)}ページ)")
    except Exception as e:
        print(f"エラー: PDFファイルの読み込みに失敗しました。 {e}")
        sys.exit(1)

    try:
        workbook = openpyxl.load_workbook(EXCEL_PATH)
        sheet = workbook.active # 最初のシートを対象とする
        print(f"\nExcelファイル '{EXCEL_PATH}' を読み込みました。")
    except FileNotFoundError:
        print(f"エラー: Excelファイルが見つかりません: {EXCEL_PATH}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: Excelファイルの読み込み中にエラーが発生しました。 {e}")
        sys.exit(1)

    # --- 質問ごとにRAG実行 & Excel書き込み ---
    # F列: 質問 (USER_QUERY)
    # G列: 模範解答
    # H列: 生成回答 (書き込み先)
    # I列: 正誤判定 (書き込み先)
    # J列: 一致率 (書き込み先)
    start_row = 4
    end_row = 233

    print(f"\n--- RAG実行ループ開始 ({start_row}行目から{end_row}行目まで) ---")
    results_for_evaluation = []

    for row_index in range(start_row, end_row + 1):
        question = sheet[f'F{row_index}'].value
        model_answer = sheet[f'G{row_index}'].value

        print("\n" + "="*50)
        print(f"処理中: {row_index}行目")
        print(f"質問(F{row_index}): {question}")
        print("="*50)

        if not question:
            print("質問が空のためスキップします。")
            sheet[f'H{row_index}'] = "質問なし"
            results_for_evaluation.append({
                "row": row_index,
                "generated": "質問なし",
                "model": model_answer
            })
            continue 

        generated_answer = run_rag_pipeline(question, structure_list, pdf_page_list)

        # 結果をExcel (H列) に書き込み
        sheet[f'H{row_index}'] = generated_answer
        print(f"\n生成回答を H{row_index} に書き込みました。")

        # 評価用のデータを保存
        results_for_evaluation.append({
            "row": row_index,
            "generated": generated_answer,
            "model": model_answer
        })

        print(f"{SLEEP_BETWEEN_QUERIES}秒待機します...")
        time.sleep(SLEEP_BETWEEN_QUERIES)

    print("\n" + "="*50)
    print("--- 回答評価ループ開始 ---")
    print("="*50)

    for result in results_for_evaluation:
        row_idx = result["row"]
        gen_ans = result["generated"]
        mod_ans = result["model"]

        print(f"\n評価中: {row_idx}行目")

        if not gen_ans or not mod_ans:
             print("生成回答または模範解答が空のため、評価をスキップします。")
             sheet[f'I{row_idx}'] = "評価不能"
             sheet[f'J{row_idx}'] = 0.0
             continue

        # AIによる評価を実行
        binary_score, consistency_score = evaluate_answer(gen_ans, mod_ans, MODEL_NAME)

        # 結果をExcel (I列, J列) に書き込み
        sheet[f'I{row_idx}'] = binary_score
        sheet[f'J{row_idx}'] = consistency_score
        print(f"評価結果を I{row_idx}='{binary_score}', J{row_idx}={consistency_score} に書き込みました。")

        print(f"{SLEEP_BETWEEN_QUERIES}秒待機します...")
        time.sleep(SLEEP_BETWEEN_QUERIES)

    try:
        output_filename = os.path.splitext(EXCEL_PATH)[0] + "_evaluated.xlsx"
        workbook.save(output_filename)
        print("\n" + "="*50)
        print(f"評価結果を '{output_filename}' に保存しました。")
        print("="*50)
    except Exception as e:
        print(f"エラー: Excelファイルの保存中にエラーが発生しました。 {e}")


if __name__ == "__main__":
    main()