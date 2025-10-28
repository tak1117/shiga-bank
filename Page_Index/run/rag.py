import os
import json  # JSONファイルを読み込むために追加
import time
from openai import AzureOpenAI  # OpenAI から AzureOpenAI に変更
from dotenv import load_dotenv  # .env ファイル読み込みのため追加

# .envファイルから環境変数を読み込む
load_dotenv()

# === APIキー設定 ===
# PageIndexClient は不要になったためコメントアウト
# PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY")
# pi = PageIndexClient(api_key=PAGEINDEX_API_KEY)

# Azure OpenAI クライアントの設定
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")  # モデル名（デプロイ名）

# AzureOpenAI クライアントを初期化
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_VERSION
)

# === 共通: ステータス待ち ===
# PageIndexClient を使用しないため、この関数は不要になりました
# def wait_for_status(get_status_func, doc_id, status_key="status", target="completed", interval=5):
#     ...

# === RAG 実装 ===
# doc_path は不要になったため、引数から削除
def vectorless_rag_query(user_query: str):
    
    # 1-4. PageIndex API 呼び出しの代わりに、ローカルJSONファイルを読み込む
    try:
        with open("merged_structure.json", "r", encoding="utf-8") as f:
            resp = json.load(f)
        print("Loaded retrieval data from merged_structure.json")
    except FileNotFoundError:
        print("エラー: merged_structure.json が見つかりません。")
        return "エラー: 参照ファイル (merged_structure.json) が見つかりません。"
    except json.JSONDecodeError:
        print("エラー: merged_structure.json の解析に失敗しました。")
        return "エラー: 参照ファイル (merged_structure.json) の形式が正しくありません。"

    retrieved_nodes = resp.get("retrieved_nodes", [])
    print("Retrieved nodes count:", len(retrieved_nodes))

    # 5. コンテキスト組み立て (元のコードをそのまま利用)
    context_texts = []
    for node in retrieved_nodes:
        title = node.get("title", "")
        text = node.get("text", "")
        relevant = node.get("relevant_contents", [])
        snippet = ""
        if relevant and isinstance(relevant, list):
            first = relevant[0]
            if isinstance(first, dict):
                snippet = first.get("relevant_content", "")
            else:
                snippet = str(first)
        context_texts.append(f"### {title}\n{text}\n{snippet}")

    # 6. プロンプト作成 (元のコードをそのまま利用)
    prompt = (
        "次のドキュメントの情報に基づいて質問に答えてください。\n\n"
        + "\n\n".join(context_texts)
        + "\n\n質問：" + user_query + "\n回答："
    )

    # 7. Azure OpenAI Chat API 呼び出し
    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,  # model にはデプロイ名を指定
            messages=[
                {"role": "system", "content": "あなたは有能な研究アシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Azure OpenAI API 呼び出し中にエラーが発生しました: {e}")
        return f"エラー: Azure OpenAI API への接続に失敗しました。({e})"


if __name__ == "__main__":
    # ユーザーから質問を受け取るように変更
    user_query = input("質問を入力してください: ")
    
    # doc_path は不要になったため削除
    result = vectorless_rag_query(user_query)
    
    print("\n=== LLM回答 ===\n")
    print(result)