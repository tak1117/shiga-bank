from pageindex import PageIndexClient
import time
import json
import os
from dotenv import load_dotenv 
load_dotenv()

API_KEY = os.getenv("PAGEINDEX_API_KEY")
pi = PageIndexClient(api_key=API_KEY)


submit_result = pi.submit_document("./merged.pdf")
doc_id = submit_result["doc_id"]
print(f"Document submitted. doc_id = {doc_id}")

# === 2. OCR 処理待ち ===
while True:
    ocr_status = pi.get_ocr(doc_id)
    print("OCR status:", ocr_status.get("status"))
    if ocr_status.get("status") == "completed":
        break
    time.sleep(5)

ocr_result = pi.get_ocr(doc_id)["result"]
# OCR結果が空でないことを確認
if ocr_result:
    print("OCR Result sample:", json.dumps(ocr_result[0], indent=2, ensure_ascii=False))
else:
    print("OCR Result is empty.")

while True:
    tree_status = pi.get_tree(doc_id)
    print("Tree generation status:", tree_status.get("status"))
    if tree_status.get("status") == "completed":
        break
    time.sleep(5)

tree_result = pi.get_tree(doc_id)["result"]
print("Tree:", json.dumps(tree_result, indent=2, ensure_ascii=False))

if not tree_result:
    print("Tree is empty. Retrieval cannot be used, fallback to OCR search.")

    query = "マネー" # ★検索したい文字列に変更してください
    found_count = 0
    if ocr_result: 
        for page in ocr_result:
            if query in page["markdown"]:
                print("Found on page", page["page_index"])
                print(page["markdown"][:200])
                found_count += 1
    if found_count == 0:
        print(f"Query '{query}' not found in OCR results.")
else:
    # === 4. Retrieval ===
    # ★検索したい質問（クエリ）に変更してください
    retrieval = pi.submit_query(doc_id, "マネーロンダリングとは何ですか？")
    retrieval_id = retrieval["retrieval_id"]
    print(f"Query submitted. retrieval_id = {retrieval_id}")

    # ステータス待ち
    while True:
        retrieval_status = pi.get_retrieval(retrieval_id)
        print("Retrieval status:", retrieval_status.get("status"))
        if retrieval_status.get("status") == "completed":
            break
        time.sleep(5)

    retrieval_result = pi.get_retrieval(retrieval_id)["retrieved_nodes"]

    # === 5. 結果出力 ===
    print("Retrieved Nodes:")
    for node in retrieval_result:
        print(" - Title:", node.get("title"))
        print("   Page:", node.get("page_index"))

        # relevant_contents の安全な処理
        contents = node.get("relevant_contents", [])
        if contents and isinstance(contents, list):
            if isinstance(contents[0], dict):
                snippet = contents[0].get("relevant_content", "(なし)")
            else:
                snippet = str(contents[0])
        else:
            snippet = "(なし)"

        print("   Content snippet:", snippet[:200])