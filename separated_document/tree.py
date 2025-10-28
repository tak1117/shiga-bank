from pageindex import PageIndexClient
import time
import json
from dotenv import load_dotenv
import os

load_dotenv()                   

API_KEY = os.getenv("PAGEINDEX_API_KEY")
pi = PageIndexClient(api_key=API_KEY)

md_filepath = "merged_document.pdf"
print(f"Submitting document: {md_filepath}")

try:
    submit_result = pi.submit_document(md_filepath)
except FileNotFoundError:
    print(f"エラー: {md_filepath} が見つかりません。パスを確認してください。")
    exit()
    
doc_id = submit_result["doc_id"]
print(f"Document submitted. doc_id = {doc_id}")

print("Waiting for Tree generation...")
while True:
    tree_status = pi.get_tree(doc_id)
    status = tree_status.get("status")
    print(f"Tree generation status: {status}")
    
    if status == "completed":
        break
    elif status == "failed":
        print("Tree generation failed.")
        print("Error details:", tree_status.get("error"))
        break
        
    time.sleep(5)

if status == "completed":
    tree_result = pi.get_tree(doc_id).get("result")
    
    if not tree_result:
        print("Tree generation completed, but the resulting Tree is empty.")
    else:
        print("\n=== Tree Generation Completed Successfully: ===")
        tree_json_sample = json.dumps(tree_result, indent=2, ensure_ascii=False)
        print(tree_json_sample[:500] + "\n...")
        
        with open(f"tree_{doc_id}.json", "w", encoding="utf-8") as f:
            json.dump(tree_result, f, indent=2, ensure_ascii=False)
        print(f"Full tree saved to tree_{doc_id}.json")

elif status == "failed":
    print("Tree generation failed. Cannot proceed.")