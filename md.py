import os
import time
from dotenv import load_dotenv
from pageindex import PageIndexClient
from openai import AzureOpenAI # Azure OpenAI Serviceを使用

# .envファイルから環境変数を読み込む
load_dotenv()

# 🔑 APIキーなどの設定
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
PDF_PATH = "path/to/your/document.pdf" # 処理したいPDFのパスに置き換えてください

# PageIndexクライアントの初期化
pi_client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

# Azure OpenAIクライアントの初期化
# APIキー、エンドポイント、APIバージョンを指定して初期化します
aoai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION
)

def pageindex_rag_pipeline_with_azure_openai(pdf_path: str, query: str):
    """
    PageIndexで検索し、Azure OpenAI Serviceで回答を生成するRAGを実行する関数。
    """
    if not all([PAGEINDEX_API_KEY, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT]):
        print("❌ エラー: 必要なAPIキーまたはエンドポイント、デプロイ名が設定されていません。")
        return

    # --- 1. ドキュメントの送信とインデックス生成の開始 ---
    print("--- 1. ドキュメントの送信とインデックス生成の開始 ---")
    try:
        # PDFを送信 (PageIndexの内部OCR/解析機能が使用されます)
        submit_result = pi_client.submit_document(pdf_path)
        doc_id = submit_result["doc_id"]
        print(f"✅ ドキュメント送信完了。 doc_id: {doc_id}")
    except Exception as e:
        print(f"❌ ドキュメント送信エラー: {e}")
        return

    # --- 2. PageIndex Tree 生成の完了を待機 ---
    print("\n--- 2. PageIndex Tree 生成の待機 ---")
    while True:
        tree_status = pi_client.get_tree(doc_id)
        status = tree_status.get("status")
        print(f"   現在のステータス: {status}")
        
        if status == "completed":
            print("✅ Tree 生成完了。リトリーバルに進みます。")
            break
        elif status in ("failed", "error"):
            print(f"❌ Tree 生成失敗。ステータス: {status}")
            return
            
        time.sleep(10) # 10秒待機して再チェック

    # --- 3. 質問を送信し、関連ノードを検索 (リトリーバル) ---
    print(f"\n--- 3. 質問の送信とリトリーバル（検索）---")
    try:
        retrieval = pi_client.submit_query(doc_id, query)
        retrieval_id = retrieval["retrieval_id"]
    except Exception as e:
        print(f"❌ クエリ送信エラー: {e}")
        return

    # リトリーバル結果の取得完了を待機
    while True:
        retrieval_status = pi_client.get_retrieval(retrieval_id)
        if retrieval_status.get("status") == "completed":
            retrieved_nodes = retrieval_status.get("retrieved_nodes", [])
            print(f"✅ リトリーバル完了。{len(retrieved_nodes)}個の関連ノードを取得。")
            break
        time.sleep(5) 

    # --- 4. 取得したノードからLLMに渡す文脈（コンテキスト）を作成 ---
    context = ""
    citations = []
    
    for i, node in enumerate(retrieved_nodes):
        title = node.get("title", "不明なセクション")
        page_index = node.get("page_index", "N/A")
        
        # 関連性の高いコンテンツを取得
        relevant_contents = node.get("relevant_contents", [])
        snippet = ""
        if relevant_contents and isinstance(relevant_contents[0], dict):
             snippet = relevant_contents[0].get("relevant_content", "")
        
        # コンテキストと引用情報に追加
        citation_tag = f"[{i+1}]"
        context += f"【参照{citation_tag}：{title} (p.{page_index})】\n{snippet}\n\n"
        citations.append(f"{citation_tag}: {title} (p.{page_index})")

    # --- 5. Azure OpenAI LLMによる回答生成 ---
    print("\n--- 5. Azure OpenAIによる回答生成 ---")
    
    # プロンプトの構築
    system_prompt = (
        "あなたはプロフェッショナルなAIアシスタントです。提供された文脈（コンテキスト）のみを根拠にして、"
        "ユーザーの質問に正確に回答してください。回答には、参照した文脈を示す引用タグを文末に含めてください。"
    )
    user_prompt = f"質問:\n{query}\n\nコンテキスト:\n{context}"
    
    try:
        response = aoai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT, # デプロイ名を指定
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        final_answer = response.choices[0].message.content.strip()
        
        # --- 6. 結果出力 ---
        print("\n====================================")
        print(f"📝 質問:\n{query}")
        print("\n🤖 AIの回答:")
        print(final_answer)
        print("\n📚 参照元:")
        for citation in citations:
            print(f"- {citation}")
        print("====================================")

    except Exception as e:
        print(f"❌ Azure OpenAI呼び出しエラー: {e}")

# 実行例
if __name__ == "__main__":
    test_query = "取締役会の構成に関する規定はどこに記載されていますか？"
    
    # 🚨 実行する際は、上記で設定したAPIキーとPDF_PATHを適切に設定し、以下のコメントアウトを外してください。
    # pageindex_rag_pipeline_with_azure_openai(PDF_PATH, test_query)
    print("デモコードです。実行するには、APIキーとPDF_PATHを適切に設定し、実行部分のコメントアウトを外してください。")