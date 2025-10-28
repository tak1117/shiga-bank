import os
import sys
import shutil
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
import tiktoken 
from langchain_text_splitters import RecursiveCharacterTextSplitter 

load_dotenv()                   

SYSTEM_PROMPT = """
あなたは、日本の規約文書やマニュアルのMarkdown構造を修正するエキスパートなテクニカルエディターです。
渡されたMarkdownテキストを読み、以下のルールに従って内容を厳密に修正・再構成してください。

**最優先ルール:**
1.  **絶対に本文を削除しない:** 元のテキストに含まれる情報を**絶対に削除しないでください**。
2.  **最小限の修正:** 修正は、Markdownの構造（見出しレベル、リスト）の修正のみに限定し、本文の内容は**原則としてそのまま保持**してください。文脈的におかしい部分のみを最小限で修正します。

**Markdown構造のルール:**
1.  **見出しの階層化 (重要):**
    * **このルールは、その行が明らかに「独立した見出し」である場合にのみ適用します。**
    * **本文中の文章（例: `...詳しくは第3章を参照。`）に「第X章」などの語句が登場しても、絶対に見出しに変更しないでください。**
    * `「第 X 章 ...」` で始まる**独立した見出し行**は、 `# 第 X 章` (H1) にします。
    * `「第 X 節 ...」` で始まる**独立した見出し行**は、 `## 第 X 節` (H2) にします。
    * `「第 X 項 ...」` で始まる**独立した見出し行**は、 `### 第 X 項` (H3) にします。
    * 上記（章・節・項）よりも下位の見出し（例: `1. 確認方法`、`(1) 顧客`、`ア.`など）は、AIが文脈的な階層構造を判断し、`####` (H4), `#####` (H5), `######` (H6) を使って適切に割り当ててください。

2.  **リストの修正:**
    * 不自然な改行で複数行に分割されているリスト項目（例: `2. ...` と次の行の `2. ...`）は、1つの項目に結合します。
    * 親リスト（例: `3. ...`）に続く `5.  ...` のような不適切な番号付けは、親リストのサブリスト（インデントした `*` または `-`）に修正します。`` は削除します。

3.  **禁止事項:**
    * 見出しの後に水平線（`---`）を**追加しないでください**。

4.  **その他のルール:**
    * 「( 注 )」や「※」で始まる行は、リストの一部ではなく、独立した注釈パラグラフとして扱ってください。
    * 修正後の完全なMarkdownテキストだけを応答してください。余計な挨拶や前置き、後書き、```markdown ブロックは一切不要です。
"""

CHUNK_SYSTEM_PROMPT = SYSTEM_PROMPT + """

重要:
あなたは今、非常に大きなドキュメントの一部（チャンク）を処理しています。
このチャンクは文書の途中で分割された可能性があるため、チャンクの先頭や末尾が不自然でも、それは無視してください。
あなたのタスクは、このチャンクの *内部* のMarkdown構造（見出し、リストなど）のみを、上記のルールに従って修正することです。
文書全体の構成を変更しようとしないでください（例: 勝手に「第1章」から始めるなど）。
"""

MD_FOLDER_NAME = "md_folder"

CREATE_BACKUP = True

TOKEN_LIMIT = 110000 

CHUNK_SIZE_CHARS = 50000
CHUNK_OVERLAP_CHARS = 1000 

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        print("Warning: cl100k_base encoding not found, defaulting to p50k_base.")
        encoding = tiktoken.get_encoding("p50k_base")
    
    num_tokens = len(encoding.encode(string))
    return num_tokens

def process_content_with_ai(client, deployment_name, system_prompt, content):
    """AIにテキスト処理を依頼し、結果を返す"""
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        max_tokens=4096, 
        temperature=0.2
    )
    return response.choices[0].message.content

def clean_ai_response(content: str) -> str:
    """AIが追加したコードブロックラッパーを削除する"""
    cleaned_content = content.strip()
    if cleaned_content.startswith("```") and cleaned_content.endswith("```"):
        cleaned_content = cleaned_content.split('\n', 1)[-1]
        
        last_newline_index = cleaned_content.rfind('\n')
        if last_newline_index != -1:
            cleaned_content = cleaned_content[:last_newline_index]
        
        cleaned_content = cleaned_content.strip()
    return cleaned_content

def main():
    try:
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
        azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        deployment_name = os.environ["AZURE_OPENAI_DEPLOYMENT"]
        
        if not all([api_key, azure_endpoint, deployment_name]):
            raise KeyError

    except KeyError:
        print("❌ エラー: .env ファイルに環境変数が設定されていません。", file=sys.stderr)
        sys.exit(1)

    try:
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version="2024-02-01"
        )
    except Exception as e:
        print(f"❌ Azureクライアントの初期化に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    current_dir = Path.cwd()
    target_dir = current_dir / MD_FOLDER_NAME

    if not target_dir.is_dir():
        print(f"エラー: フォルダ '{MD_FOLDER_NAME}' が見つかりません。", file=sys.stderr)
        sys.exit(1)

    print(f"処理対象フォルダ: {target_dir}")
    print(f"AIデプロイメント: {deployment_name}")
    print(f"トークン上限: {TOKEN_LIMIT}, チャンク文字サイズ: {CHUNK_SIZE_CHARS}")
    print("---")

    md_files = list(target_dir.rglob("*.md"))

    if not md_files:
        print(f"処理完了: '{MD_FOLDER_NAME}' 内に .md ファイルが見つかりませんでした。")
        sys.exit(0)

    print(f"Found {len(md_files)} 個の .md ファイルを処理します...")

    for md_file in md_files:
        relative_path = md_file.relative_to(current_dir)
        print(f"\n--- 処理中: {relative_path} ---")

        try:
            if CREATE_BACKUP:
                backup_file = md_file.with_suffix(md_file.suffix + ".bak")
                shutil.copy2(md_file, backup_file)
                print(f"  -> バックアップを作成: {backup_file.name}")

            original_content = md_file.read_text(encoding="utf-8")
            if not original_content.strip():
                print("  -> ファイルが空のためスキップします。")
                continue

            system_prompt_tokens = num_tokens_from_string(SYSTEM_PROMPT)
            total_tokens = num_tokens_from_string(original_content)

            new_content = ""

            if (total_tokens + system_prompt_tokens) <= TOKEN_LIMIT:
                print(f"  -> AIにリクエスト中 (フルファイル: {total_tokens} トークン)...")
                new_content = process_content_with_ai(
                    client, deployment_name, SYSTEM_PROMPT, original_content
                )

            else:
                print(f"ファイルが大きすぎます ({total_tokens} トークン)。チャンクに分割します...")
                
                text_splitter = RecursiveCharacterTextSplitter(
                    separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""],
                    chunk_size=CHUNK_SIZE_CHARS,
                    chunk_overlap=CHUNK_OVERLAP_CHARS,
                    length_function=len 
                )
                
                chunks = text_splitter.split_text(original_content)
                print(f"    -> ファイルを {len(chunks)} 個のチャンクに分割しました。")
                
                processed_chunks = []
                for i, chunk in enumerate(chunks):
                    print(f"    -> チャンク {i+1}/{len(chunks)} を処理中...")
                    
                    processed_chunk = process_content_with_ai(
                        client, deployment_name, CHUNK_SYSTEM_PROMPT, chunk
                    )
                    processed_chunks.append(processed_chunk)
                
                new_content = "\n\n".join(processed_chunks)

            if not new_content:
                print("  警告: AIから空の応答が返されました。ファイルは変更されません。")
                continue

            cleaned_content = clean_ai_response(new_content)
            
            md_file.write_text(cleaned_content, encoding="utf-8")
            print(f"  完了: {relative_path} をAIの応答で上書きしました。")

        except FileNotFoundError:
            print(f"  エラー: ファイルが見つかりません (処理中に移動された？): {relative_path}", file=sys.stderr)
        except UnicodeDecodeError:
            print(f"  エラー: {relative_path} は 'utf-8' で読み込めませんでした。スキップします。", file=sys.stderr)
        except Exception as e:
            print(f"  予期せぬエラーが発生しました: {e}", file=sys.stderr)
            print(f"    ファイル: {relative_path}", file=sys.stderr)

    print("\n---")
    print("すべての処理が完了しました。")

if __name__ == "__main__":
    main()