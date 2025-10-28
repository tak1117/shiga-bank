# import tiktoken
# import openai
# import logging
# import os
# from datetime import datetime
# import time
# import json
# import PyPDF2
# import copy
# import asyncio
# import pymupdf
# import re
# from io import BytesIO
# from dotenv import load_dotenv
# from pathlib import Path
# from types import SimpleNamespace as config

# # --- Azure OpenAI Service に必要なインポートを追加 ---
# from openai import AzureOpenAI, AsyncAzureOpenAI 

# # 環境変数の読み込み
# load_dotenv()

# # --- 1. 環境変数の設定 (AZURE OPEANAI を優先) ---
# AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
# AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
# AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# # ロギング設定
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# # --- 2. Azure OpenAI クライアントの初期化 ---
# def initialize_azure_openai_clients():
#     """Azure OpenAI Serviceのクライアントを初期化し、グローバル変数に設定する"""
#     if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT]):
#         logging.error("Azure OpenAI の設定 (API KEY, ENDPOINT, API VERSION, DEPLOYMENT) が不足しています。")
#         return None, None
    
#     try:
#         # 同期クライアント
#         sync_client = AzureOpenAI(
#             api_key=AZURE_OPENAI_API_KEY,
#             azure_endpoint=AZURE_OPENAI_ENDPOINT,
#             api_version=AZURE_OPENAI_API_VERSION
#         )
#         # 非同期クライアント
#         async_client = AsyncAzureOpenAI(
#             api_key=AZURE_OPENAI_API_KEY,
#             azure_endpoint=AZURE_OPENAI_ENDPOINT,
#             api_version=AZURE_OPENAI_API_VERSION
#         )
#         return sync_client, async_client
#     except Exception as e:
#         logging.error(f"AzureOpenAIクライアントの初期化中にエラーが発生しました: {e}")
#         return None, None

# AZURE_SYNC_CLIENT, AZURE_ASYNC_CLIENT = initialize_azure_openai_clients()


# # --- LLM ユーティリティ関数 ---

# def count_tokens(text, model=None):
#     if not text:
#         return 0
#     # Azure OpenAIではデプロイメント名ではなく、モデル名(gpt-4, gpt-3.5-turboなど)でエンコーディングを取得
#     model_for_tiktoken = 'gpt-4' 
#     try:
#         enc = tiktoken.encoding_for_model(model_for_tiktoken)
#     except KeyError:
#         enc = tiktoken.get_encoding("cl100k_base") 
#     tokens = enc.encode(text)
#     return len(tokens)

# def ChatGPT_API_with_finish_reason(model, prompt, chat_history=None):
#     """同期LLM呼び出し (finish_reason 付き) を Azure OpenAI Service に対応"""
#     if AZURE_SYNC_CLIENT is None:
#         return "Error: Azure client not initialized", "error"

#     max_retries = 10
#     client = AZURE_SYNC_CLIENT
#     deployment_name = AZURE_OPENAI_DEPLOYMENT
    
#     for i in range(max_retries):
#         try:
#             if chat_history:
#                 messages = chat_history.copy()
#                 messages.append({"role": "user", "content": prompt})
#             else:
#                 messages = [{"role": "user", "content": prompt}]
            
#             response = client.chat.completions.create(
#                 model=deployment_name, # デプロイメント名を使用
#                 messages=messages,
#                 temperature=0,
#             )
            
#             finish_reason = response.choices[0].finish_reason
#             content = response.choices[0].message.content
            
#             if finish_reason == "length":
#                 return content, "max_output_reached"
#             else:
#                 return content, "finished"

#         except Exception as e:
#             print('************* Retrying *************')
#             logging.error(f"Error in ChatGPT_API_with_finish_reason: {e}")
#             if i < max_retries - 1:
#                 time.sleep(1)
#             else:
#                 logging.error('Max retries reached for prompt: ' + prompt)
#                 return "Error", "error"


# def ChatGPT_API(model, prompt, chat_history=None):
#     """同期LLM呼び出しを Azure OpenAI Service に対応"""
#     if AZURE_SYNC_CLIENT is None:
#         return "Error: Azure client not initialized"
        
#     max_retries = 10
#     client = AZURE_SYNC_CLIENT
#     deployment_name = AZURE_OPENAI_DEPLOYMENT
    
#     for i in range(max_retries):
#         try:
#             if chat_history:
#                 messages = chat_history.copy()
#                 messages.append({"role": "user", "content": prompt})
#             else:
#                 messages = [{"role": "user", "content": prompt}]
            
#             response = client.chat.completions.create(
#                 model=deployment_name, # デプロイメント名を使用
#                 messages=messages,
#                 temperature=0,
#             )
   
#             return response.choices[0].message.content
#         except Exception as e:
#             print('************* Retrying *************')
#             logging.error(f"Error in ChatGPT_API: {e}")
#             if i < max_retries - 1:
#                 time.sleep(1)
#             else:
#                 logging.error('Max retries reached for prompt: ' + prompt)
#                 return "Error"
            

# async def ChatGPT_API_async(model, prompt):
#     """非同期LLM呼び出しを Azure OpenAI Service に対応"""
#     if AZURE_ASYNC_CLIENT is None:
#         return "Error: Azure client not initialized"

#     max_retries = 10
#     client = AZURE_ASYNC_CLIENT
#     deployment_name = AZURE_OPENAI_DEPLOYMENT
#     messages = [{"role": "user", "content": prompt}]
    
#     for i in range(max_retries):
#         try:
#             response = await client.chat.completions.create(
#                 model=deployment_name, # デプロイメント名を使用
#                 messages=messages,
#                 temperature=0,
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             print('************* Retrying *************')
#             logging.error(f"Error in ChatGPT_API_async: {e}")
#             if i < max_retries - 1:
#                 await asyncio.sleep(1)
#             else:
#                 logging.error('Max retries reached for prompt: ' + prompt)
#                 return "Error"  
            
            
# def get_json_content(response):
#     start_idx = response.find("```json")
#     if start_idx != -1:
#         start_idx += 7
#         response = response[start_idx:]
        
#     end_idx = response.rfind("```")
#     if end_idx != -1:
#         response = response[:end_idx]
    
#     json_content = response.strip()
#     return json_content
         

# def extract_json(content):
#     try:
#         # First, try to extract JSON enclosed within ```json and ```
#         start_idx = content.find("```json")
#         if start_idx != -1:
#             start_idx += 7  # Adjust index to start after the delimiter
#             end_idx = content.rfind("```")
#             json_content = content[start_idx:end_idx].strip()
#         else:
#             # If no delimiters, assume entire content could be JSON
#             json_content = content.strip()

#         # Clean up common issues that might cause parsing errors
#         json_content = json_content.replace('None', 'null')  # Replace Python None with JSON null
#         json_content = json_content.replace('\n', ' ').replace('\r', ' ')  # Remove newlines
#         json_content = ' '.join(json_content.split())  # Normalize whitespace

#         # Attempt to parse and return the JSON object
#         return json.loads(json_content)
#     except json.JSONDecodeError as e:
#         logging.error(f"Failed to extract JSON: {e}")
#         # Try to clean up the content further if initial parsing fails
#         try:
#             # Remove any trailing commas before closing brackets/braces
#             json_content = json_content.replace(',]', ']').replace(',}', '}')
#             return json.loads(json_content)
#         except:
#             logging.error("Failed to parse JSON even after cleanup")
#             return {}
#     except Exception as e:
#         logging.error(f"Unexpected error while extracting JSON: {e}")
#         return {}

# # --- 以下の関数は LLM 呼び出しを含まないため、変更は不要です ---

# def write_node_id(data, node_id=0):
#     if isinstance(data, dict):
#         data['node_id'] = str(node_id).zfill(4)
#         node_id += 1
#         for key in list(data.keys()):
#             if 'nodes' in key:
#                 node_id = write_node_id(data[key], node_id)
#     elif isinstance(data, list):
#         for index in range(len(data)):
#             node_id = write_node_id(data[index], node_id)
#     return node_id

# def get_nodes(structure):
#     if isinstance(structure, dict):
#         structure_node = copy.deepcopy(structure)
#         structure_node.pop('nodes', None)
#         nodes = [structure_node]
#         for key in list(structure.keys()):
#             if 'nodes' in key:
#                 nodes.extend(get_nodes(structure[key]))
#         return nodes
#     elif isinstance(structure, list):
#         nodes = []
#         for item in structure:
#             nodes.extend(get_nodes(item))
#         return nodes
    
# def structure_to_list(structure):
#     if isinstance(structure, dict):
#         nodes = []
#         nodes.append(structure)
#         if 'nodes' in structure:
#             nodes.extend(structure_to_list(structure['nodes']))
#         return nodes
#     elif isinstance(structure, list):
#         nodes = []
#         for item in structure:
#             nodes.extend(structure_to_list(item))
#         return nodes

    
# def get_leaf_nodes(structure):
#     if isinstance(structure, dict):
#         if not structure.get('nodes'):
#             structure_node = copy.deepcopy(structure)
#             structure_node.pop('nodes', None)
#             return [structure_node]
#         else:
#             leaf_nodes = []
#             for key in list(structure.keys()):
#                 if 'nodes' in key:
#                     leaf_nodes.extend(get_leaf_nodes(structure[key]))
#             return leaf_nodes
#     elif isinstance(structure, list):
#         leaf_nodes = []
#         for item in structure:
#             leaf_nodes.extend(get_leaf_nodes(item))
#         return leaf_nodes

# def is_leaf_node(data, node_id):
#     # Helper function to find the node by its node_id
#     def find_node(data, node_id):
#         if isinstance(data, dict):
#             if data.get('node_id') == node_id:
#                 return data
#             for key in data.keys():
#                 if 'nodes' in key:
#                     result = find_node(data[key], node_id)
#                     if result:
#                         return result
#         elif isinstance(data, list):
#             for item in data:
#                 result = find_node(item, node_id)
#                 if result:
#                     return result
#         return None

#     # Find the node with the given node_id
#     node = find_node(data, node_id)

#     # Check if the node is a leaf node
#     if node and not node.get('nodes'):
#         return True
#     return False

# def get_last_node(structure):
#     return structure[-1]


# def extract_text_from_pdf(pdf_path):
#     pdf_reader = PyPDF2.PdfReader(pdf_path)
#     text=""
#     for page_num in range(len(pdf_reader.pages)):
#         page = pdf_reader.pages[page_num]
#         text+=page.extract_text()
#     return text

# def get_pdf_title(pdf_path):
#     pdf_reader = PyPDF2.PdfReader(pdf_path)
#     meta = pdf_reader.metadata
#     title = meta.title if meta and meta.title else 'Untitled'
#     return title

# def get_text_of_pages(pdf_path, start_page, end_page, tag=True):
#     pdf_reader = PyPDF2.PdfReader(pdf_path)
#     text = ""
#     for page_num in range(start_page-1, end_page):
#         page = pdf_reader.pages[page_num]
#         page_text = page.extract_text()
#         if tag:
#             text += f"<start_index_{page_num+1}>\n{page_text}\n<end_index_{page_num+1}>\n"
#         else:
#             text += page_text
#     return text

# def get_first_start_page_from_text(text):
#     start_page = -1
#     start_page_match = re.search(r'<start_index_(\d+)>', text)
#     if start_page_match:
#         start_page = int(start_page_match.group(1))
#     return start_page

# def get_last_start_page_from_text(text):
#     start_page = -1
#     start_page_matches = re.finditer(r'<start_index_(\d+)>', text)
#     matches_list = list(start_page_matches)
#     if matches_list:
#         start_page = int(matches_list[-1].group(1))
#     return start_page


# def sanitize_filename(filename, replacement='-'):
#     return filename.replace('/', replacement)

# def get_pdf_name(pdf_path):
#     if isinstance(pdf_path, str):
#         pdf_name = os.path.basename(pdf_path)
#     elif isinstance(pdf_path, BytesIO):
#         pdf_reader = PyPDF2.PdfReader(pdf_path)
#         meta = pdf_reader.metadata
#         pdf_name = meta.title if meta and meta.title else 'Untitled'
#         pdf_name = sanitize_filename(pdf_name)
#     return pdf_name


# class JsonLogger:
#     def __init__(self, file_path):
#         pdf_name = get_pdf_name(file_path)
#         current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
#         self.filename = f"{pdf_name}_{current_time}.json"
#         os.makedirs("./logs", exist_ok=True)
#         self.log_data = []

#     def log(self, level, message, **kwargs):
#         if isinstance(message, dict):
#             self.log_data.append(message)
#         else:
#             self.log_data.append({'message': message})
        
#         with open(self._filepath(), "w") as f:
#             json.dump(self.log_data, f, indent=2)

#     def info(self, message, **kwargs):
#         self.log("INFO", message, **kwargs)

#     def error(self, message, **kwargs):
#         self.log("ERROR", message, **kwargs)

#     def debug(self, message, **kwargs):
#         self.log("DEBUG", message, **kwargs)

#     def exception(self, message, **kwargs):
#         kwargs["exception"] = True
#         self.log("ERROR", message, **kwargs)

#     def _filepath(self):
#         return os.path.join("logs", self.filename)
    


# def list_to_tree(data):
#     def get_parent_structure(structure):
#         if not structure:
#             return None
#         parts = str(structure).split('.')
#         return '.'.join(parts[:-1]) if len(parts) > 1 else None
    
#     nodes = {}
#     root_nodes = []
    
#     for item in data:
#         structure = item.get('structure')
#         node = {
#             'title': item.get('title'),
#             'start_index': item.get('start_index'),
#             'end_index': item.get('end_index'),
#             'nodes': []
#         }
        
#         nodes[structure] = node
        
#         parent_structure = get_parent_structure(structure)
        
#         if parent_structure:
#             if parent_structure in nodes:
#                 nodes[parent_structure]['nodes'].append(node)
#             else:
#                 root_nodes.append(node)
#         else:
#             root_nodes.append(node)
    
#     def clean_node(node):
#         if not node['nodes']:
#             del node['nodes']
#         else:
#             for child in node['nodes']:
#                 clean_node(child)
#         return node
    
#     return [clean_node(node) for node in root_nodes]

# def add_preface_if_needed(data):
#     if not isinstance(data, list) or not data:
#         return data

#     if data[0]['physical_index'] is not None and data[0]['physical_index'] > 1:
#         preface_node = {
#             "structure": "0",
#             "title": "Preface",
#             "physical_index": 1,
#         }
#         data.insert(0, preface_node)
#     return data



# def get_page_tokens(pdf_path, model="gpt-4o-2024-11-20", pdf_parser="PyPDF2"):
#     model_for_tiktoken = 'gpt-4' 
#     try:
#         enc = tiktoken.encoding_for_model(model_for_tiktoken)
#     except KeyError:
#         enc = tiktoken.get_encoding("cl100k_base") 
        
#     if pdf_parser == "PyPDF2":
#         pdf_reader = PyPDF2.PdfReader(pdf_path)
#         page_list = []
#         for page_num in range(len(pdf_reader.pages)):
#             page = pdf_reader.pages[page_num]
#             page_text = page.extract_text()
#             token_length = len(enc.encode(page_text))
#             page_list.append((page_text, token_length))
#         return page_list
#     elif pdf_parser == "PyMuPDF":
#         if isinstance(pdf_path, BytesIO):
#             pdf_stream = pdf_path
#             doc = pymupdf.open(stream=pdf_stream, filetype="pdf")
#         elif isinstance(pdf_path, str) and os.path.isfile(pdf_path) and pdf_path.lower().endswith(".pdf"):
#             doc = pymupdf.open(pdf_path)
#         page_list = []
#         for page in doc:
#             page_text = page.get_text()
#             token_length = len(enc.encode(page_text))
#             page_list.append((page_text, token_length))
#         return page_list
#     else:
#         raise ValueError(f"Unsupported PDF parser: {pdf_parser}")

        

# def get_text_of_pdf_pages(pdf_pages, start_page, end_page):
#     text = ""
#     for page_num in range(start_page-1, end_page):
#         text += pdf_pages[page_num][0]
#     return text

# def get_text_of_pdf_pages_with_labels(pdf_pages, start_page, end_page):
#     text = ""
#     for page_num in range(start_page-1, end_page):
#         text += f"<physical_index_{page_num+1}>\n{pdf_pages[page_num][0]}\n<physical_index_{page_num+1}>\n"
#     return text

# def get_number_of_pages(pdf_path):
#     pdf_reader = PyPDF2.PdfReader(pdf_path)
#     num = len(pdf_reader.pages)
#     return num



# def post_processing(structure, end_physical_index):
#     for i, item in enumerate(structure):
#         item['start_index'] = item.get('physical_index')
#         if i < len(structure) - 1:
#             if structure[i + 1].get('appear_start') == 'yes':
#                 item['end_index'] = structure[i + 1]['physical_index']-1
#             else:
#                 item['end_index'] = structure[i + 1]['physical_index']
#         else:
#             item['end_index'] = end_physical_index
#     tree = list_to_tree(structure)
#     if len(tree)!=0:
#         return tree
#     else:
#         for node in structure:
#             node.pop('appear_start', None)
#             node.pop('physical_index', None)
#         return structure

# def clean_structure_post(data):
#     if isinstance(data, dict):
#         data.pop('page_number', None)
#         data.pop('start_index', None)
#         data.pop('end_index', None)
#         if 'nodes' in data:
#             clean_structure_post(data['nodes'])
#     elif isinstance(data, list):
#         for section in data:
#             clean_structure_post(section)
#     return data

# def remove_fields(data, fields=['text']):
#     if isinstance(data, dict):
#         return {k: remove_fields(v, fields)
#             for k, v in data.items() if k not in fields}
#     elif isinstance(data, list):
#         return [remove_fields(item, fields) for item in data]
#     return data

# def print_toc(tree, indent=0):
#     for node in tree:
#         print('  ' * indent + node['title'])
#         if node.get('nodes'):
#             print_toc(node['nodes'], indent + 1)

# def print_json(data, max_len=40, indent=2):
#     def simplify_data(obj):
#         if isinstance(obj, dict):
#             return {k: simplify_data(v) for k, v in obj.items()}
#         elif isinstance(obj, list):
#             return [simplify_data(item) for item in obj]
#         elif isinstance(obj, str) and len(obj) > max_len:
#             return obj[:max_len] + '...'
#         else:
#             return obj
    
#     simplified = simplify_data(data)
#     print(json.dumps(simplified, indent=indent, ensure_ascii=False))


# def remove_structure_text(data):
#     if isinstance(data, dict):
#         data.pop('text', None)
#         if 'nodes' in data:
#             remove_structure_text(data['nodes'])
#     elif isinstance(data, list):
#         for item in data:
#             remove_structure_text(item)
#     return data


# def check_token_limit(structure, limit=110000):
#     list = structure_to_list(structure)
#     for node in list:
#         num_tokens = count_tokens(node['text'], model='gpt-4o')
#         if num_tokens > limit:
#             print(f"Node ID: {node['node_id']} has {num_tokens} tokens")
#             print("Start Index:", node['start_index'])
#             print("End Index:", node['end_index'])
#             print("Title:", node['title'])
#             print("\n")


# def convert_physical_index_to_int(data):
#     if isinstance(data, list):
#         for i in range(len(data)):
#             if isinstance(data[i], dict) and 'physical_index' in data[i]:
#                 if isinstance(data[i]['physical_index'], str):
#                     if data[i]['physical_index'].startswith('<physical_index_'):
#                         data[i]['physical_index'] = int(data[i]['physical_index'].split('_')[-1].rstrip('>').strip())
#                     elif data[i]['physical_index'].startswith('physical_index_'):
#                         data[i]['physical_index'] = int(data[i]['physical_index'].split('_')[-1].strip())
#     elif isinstance(data, str):
#         if data.startswith('<physical_index_'):
#             data = int(data.split('_')[-1].rstrip('>').strip())
#         elif data.startswith('physical_index_'):
#             data = int(data.split('_')[-1].strip())
#         if isinstance(data, int):
#             return data
#         else:
#             return None
#     return data


# def convert_page_to_int(data):
#     for item in data:
#         if 'page' in item and isinstance(item['page'], str):
#             try:
#                 item['page'] = int(item['page'])
#             except ValueError:
#                 pass
#     return data


# def add_node_text(node, pdf_pages):
#     if isinstance(node, dict):
#         start_page = node.get('start_index')
#         end_page = node.get('end_index')
#         node['text'] = get_text_of_pdf_pages(pdf_pages, start_page, end_page)
#         if 'nodes' in node:
#             add_node_text(node['nodes'], pdf_pages)
#     elif isinstance(node, list):
#         for index in range(len(node)):
#             add_node_text(node[index], pdf_pages)
#     return


# def add_node_text_with_labels(node, pdf_pages):
#     if isinstance(node, dict):
#         start_page = node.get('start_index')
#         end_page = node.get('end_index')
#         node['text'] = get_text_of_pdf_pages_with_labels(pdf_pages, start_page, end_page)
#         if 'nodes' in node:
#             add_node_text_with_labels(node['nodes'], pdf_pages)
#     elif isinstance(node, list):
#         for index in range(len(node)):
#             add_node_text_with_labels(node[index], pdf_pages)
#     return


# async def generate_node_summary(node, model=None):
#     prompt = f"""You are given a part of a document, your task is to generate a description of the partial document about what are main points covered in the partial document.

#     Partial Document Text: {node['text']}
    
#     Directly return the description, do not include any other text.
#     """
#     response = await ChatGPT_API_async(model, prompt)
#     return response


# async def generate_summaries_for_structure(structure, model=None):
#     nodes = structure_to_list(structure)
#     tasks = [generate_node_summary(node, model=model) for node in nodes]
#     summaries = await asyncio.gather(*tasks)
    
#     for node, summary in zip(nodes, summaries):
#         node['summary'] = summary
#     return structure


# def create_clean_structure_for_description(structure):
#     if isinstance(structure, dict):
#         clean_node = {}
#         for key in ['title', 'node_id', 'summary', 'prefix_summary']:
#             if key in structure:
#                 clean_node[key] = structure[key]
        
#         if 'nodes' in structure and structure['nodes']:
#             clean_node['nodes'] = create_clean_structure_for_description(structure['nodes'])
        
#         return clean_node
#     elif isinstance(structure, list):
#         return [create_clean_structure_for_description(item) for item in structure]
#     else:
#         return structure


# def generate_doc_description(structure, model=None):
#     prompt = f"""Your are an expert in generating descriptions for a document.
#     You are given a structure of a document. Your task is to generate a one-sentence description for the document, which makes it easy to distinguish the document from other documents.
        
#     Document Structure: {structure}
    
#     Directly return the description, do not include any other text.
#     """
#     response = ChatGPT_API(model, prompt)
#     return response


# def reorder_dict(data, key_order):
#     if not key_order:
#         return data
#     return {key: data[key] for key in key_order if key in data}


# def format_structure(structure, order=None):
#     if not order:
#         return structure
#     if isinstance(structure, dict):
#         if 'nodes' in structure:
#             structure['nodes'] = format_structure(structure['nodes'], order)
#         if not structure.get('nodes'):
#             structure.pop('nodes', None)
#         structure = reorder_dict(structure, order)
#     elif isinstance(structure, list):
#         structure = [format_structure(item, order) for item in structure]
#     return structure


# class ConfigLoader:
#     def __init__(self, default_path: str = None):
#         if default_path is None:
#             # config.yamlが存在しない場合を考慮し、デフォルト値を空の辞書にするか、例外処理が必要
#             default_path = Path(__file__).parent / "config.yaml"
#         self._default_dict = self._load_yaml(default_path)

#     @staticmethod
#     def _load_yaml(path):
#         try:
#             with open(path, "r", encoding="utf-8") as f:
#                 return yaml.safe_load(f) or {}
#         except FileNotFoundError:
#             # config.yaml が見つからない場合は空の辞書を返す
#             return {}

#     def _validate_keys(self, user_dict):
#         unknown_keys = set(user_dict) - set(self._default_dict)
#         if unknown_keys:
#             raise ValueError(f"Unknown config keys: {unknown_keys}")

#     def load(self, user_opt=None) -> config:
#         if user_opt is None:
#             user_dict = {}
#         elif isinstance(user_opt, config):
#             user_dict = vars(user_opt)
#         elif isinstance(user_opt, dict):
#             user_dict = user_opt
#         else:
#             raise TypeError("user_opt must be dict, config(SimpleNamespace) or None")

#         self._validate_keys(user_dict)
#         merged = {**self._default_dict, **user_dict}
#         return config(**merged)

import tiktoken
import openai
import logging
import os
from datetime import datetime
import time
import json
import PyPDF2
import copy
import asyncio
import pymupdf
import re
from io import BytesIO
from dotenv import load_dotenv
from pathlib import Path
from types import SimpleNamespace as config

# --- Azure OpenAI Service に必要なインポートを追加 ---
from openai import AzureOpenAI, AsyncAzureOpenAI 

# 環境変数の読み込み
load_dotenv()

# --- 1. 環境変数の設定 (AZURE OPEANAI を優先) ---
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- 2. Azure OpenAI クライアントの初期化 ---
def initialize_azure_openai_clients():
    """Azure OpenAI Serviceのクライアントを初期化し、グローバル変数に設定する"""
    if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT]):
        logging.error("Azure OpenAI の設定 (API KEY, ENDPOINT, API VERSION, DEPLOYMENT) が不足しています。")
        return None, None
    
    try:
        # 同期クライアント
        sync_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION
        )
        # 非同期クライアント
        async_client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION
        )
        return sync_client, async_client
    except Exception as e:
        logging.error(f"AzureOpenAIクライアントの初期化中にエラーが発生しました: {e}")
        return None, None

AZURE_SYNC_CLIENT, AZURE_ASYNC_CLIENT = initialize_azure_openai_clients()


# --- LLM ユーティリティ関数 ---

def count_tokens(text, model=None):
    if not text:
        return 0
    # Azure OpenAIではデプロイメント名ではなく、モデル名(gpt-4, gpt-3.5-turboなど)でエンコーディングを取得
    model_for_tiktoken = 'gpt-4' 
    try:
        enc = tiktoken.encoding_for_model(model_for_tiktoken)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base") 
    tokens = enc.encode(text)
    return len(tokens)

def ChatGPT_API_with_finish_reason(model, prompt, chat_history=None):
    """同期LLM呼び出し (finish_reason 付き) を Azure OpenAI Service に対応"""
    if AZURE_SYNC_CLIENT is None:
        return "Error: Azure client not initialized", "error"

    max_retries = 10
    client = AZURE_SYNC_CLIENT
    deployment_name = AZURE_OPENAI_DEPLOYMENT
    
    for i in range(max_retries):
        try:
            if chat_history:
                messages = chat_history.copy()
                messages.append({"role": "user", "content": prompt})
            else:
                messages = [{"role": "user", "content": prompt}]
            
            response = client.chat.completions.create(
                model=deployment_name, # デプロイメント名を使用
                messages=messages,
                temperature=0,
            )
            
            finish_reason = response.choices[0].finish_reason
            content = response.choices[0].message.content
            
            if finish_reason == "length":
                return content, "max_output_reached"
            else:
                return content, "finished"

        except Exception as e:
            print('************* Retrying *************')
            logging.error(f"Error in ChatGPT_API_with_finish_reason: {e}")
            if i < max_retries - 1:
                time.sleep(1)
            else:
                logging.error('Max retries reached for prompt: ' + prompt)
                return "Error", "error"


def ChatGPT_API(model, prompt, chat_history=None):
    """同期LLM呼び出しを Azure OpenAI Service に対応"""
    if AZURE_SYNC_CLIENT is None:
        return "Error: Azure client not initialized"
        
    max_retries = 10
    client = AZURE_SYNC_CLIENT
    deployment_name = AZURE_OPENAI_DEPLOYMENT
    
    for i in range(max_retries):
        try:
            if chat_history:
                messages = chat_history.copy()
                messages.append({"role": "user", "content": prompt})
            else:
                messages = [{"role": "user", "content": prompt}]
            
            response = client.chat.completions.create(
                model=deployment_name, # デプロイメント名を使用
                messages=messages,
                temperature=0,
            )
   
            return response.choices[0].message.content
        except Exception as e:
            print('************* Retrying *************')
            logging.error(f"Error in ChatGPT_API: {e}")
            if i < max_retries - 1:
                time.sleep(1)
            else:
                logging.error('Max retries reached for prompt: ' + prompt)
                return "Error"
            

async def ChatGPT_API_async(model, prompt):
    """非同期LLM呼び出しを Azure OpenAI Service に対応"""
    if AZURE_ASYNC_CLIENT is None:
        return "Error: Azure client not initialized"

    max_retries = 10
    client = AZURE_ASYNC_CLIENT
    deployment_name = AZURE_OPENAI_DEPLOYMENT
    messages = [{"role": "user", "content": prompt}]
    
    for i in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=deployment_name, # デプロイメント名を使用
                messages=messages,
                temperature=0,
            )
            return response.choices[0].message.content
        except Exception as e:
            print('************* Retrying *************')
            logging.error(f"Error in ChatGPT_API_async: {e}")
            if i < max_retries - 1:
                await asyncio.sleep(1)
            else:
                logging.error('Max retries reached for prompt: ' + prompt)
                return "Error" 
            
            
            
def get_json_content(response):
    start_idx = response.find("```json")
    if start_idx != -1:
        start_idx += 7
        response = response[start_idx:]
        
    end_idx = response.rfind("```")
    if end_idx != -1:
        response = response[:end_idx]
    
    json_content = response.strip()
    return json_content
            
            
def extract_json(content):
    try:
        # First, try to extract JSON enclosed within ```json and ```
        start_idx = content.find("```json")
        if start_idx != -1:
            start_idx += 7  # Adjust index to start after the delimiter
            end_idx = content.rfind("```")
            json_content = content[start_idx:end_idx].strip()
        else:
            # If no delimiters, assume entire content could be JSON
            json_content = content.strip()

        # Clean up common issues that might cause parsing errors
        json_content = json_content.replace('None', 'null')  # Replace Python None with JSON null
        json_content = json_content.replace('\n', ' ').replace('\r', ' ')  # Remove newlines
        json_content = ' '.join(json_content.split())  # Normalize whitespace

        # Attempt to parse and return the JSON object
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to extract JSON: {e}")
        # Try to clean up the content further if initial parsing fails
        try:
            # Remove any trailing commas before closing brackets/braces
            json_content = json_content.replace(',]', ']').replace(',}', '}')
            return json.loads(json_content)
        except:
            logging.error("Failed to parse JSON even after cleanup")
            return {}
    except Exception as e:
        logging.error(f"Unexpected error while extracting JSON: {e}")
        return {}

# --- 以下の関数は LLM 呼び出しを含まないため、変更は不要です ---

def write_node_id(data, node_id=0):
    if isinstance(data, dict):
        data['node_id'] = str(node_id).zfill(4)
        node_id += 1
        for key in list(data.keys()):
            if 'nodes' in key:
                node_id = write_node_id(data[key], node_id)
    elif isinstance(data, list):
        for index in range(len(data)):
            node_id = write_node_id(data[index], node_id)
    return node_id

def get_nodes(structure):
    if isinstance(structure, dict):
        structure_node = copy.deepcopy(structure)
        structure_node.pop('nodes', None)
        nodes = [structure_node]
        for key in list(structure.keys()):
            if 'nodes' in key:
                nodes.extend(get_nodes(structure[key]))
        return nodes
    elif isinstance(structure, list):
        nodes = []
        for item in structure:
            nodes.extend(get_nodes(item))
        return nodes
    
def structure_to_list(structure):
    if isinstance(structure, dict):
        nodes = []
        nodes.append(structure)
        if 'nodes' in structure:
            nodes.extend(structure_to_list(structure['nodes']))
        return nodes
    elif isinstance(structure, list):
        nodes = []
        for item in structure:
            nodes.extend(structure_to_list(item))
        return nodes

    
def get_leaf_nodes(structure):
    if isinstance(structure, dict):
        if not structure.get('nodes'):
            structure_node = copy.deepcopy(structure)
            structure_node.pop('nodes', None)
            return [structure_node]
        else:
            leaf_nodes = []
            for key in list(structure.keys()):
                if 'nodes' in key:
                    leaf_nodes.extend(get_leaf_nodes(structure[key]))
            return leaf_nodes
    elif isinstance(structure, list):
        leaf_nodes = []
        for item in structure:
            leaf_nodes.extend(get_leaf_nodes(item))
        return leaf_nodes

def is_leaf_node(data, node_id):
    # Helper function to find the node by its node_id
    def find_node(data, node_id):
        if isinstance(data, dict):
            if data.get('node_id') == node_id:
                return data
            for key in data.keys():
                if 'nodes' in key:
                    result = find_node(data[key], node_id)
                    if result:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = find_node(item, node_id)
                if result:
                    return result
        return None

    # Find the node with the given node_id
    node = find_node(data, node_id)

    # Check if the node is a leaf node
    if node and not node.get('nodes'):
        return True
    return False

def get_last_node(structure):
    return structure[-1]


def extract_text_from_pdf(pdf_path):
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    text=""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text+=page.extract_text()
    return text

def get_pdf_title(pdf_path):
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    meta = pdf_reader.metadata
    title = meta.title if meta and meta.title else 'Untitled'
    return title

def get_text_of_pages(pdf_path, start_page, end_page, tag=True):
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    text = ""
    for page_num in range(start_page-1, end_page):
        page = pdf_reader.pages[page_num]
        page_text = page.extract_text()
        if tag:
            text += f"<start_index_{page_num+1}>\n{page_text}\n<end_index_{page_num+1}>\n"
        else:
            text += page_text
    return text

def get_first_start_page_from_text(text):
    start_page = -1
    start_page_match = re.search(r'<start_index_(\d+)>', text)
    if start_page_match:
        start_page = int(start_page_match.group(1))
    return start_page

def get_last_start_page_from_text(text):
    start_page = -1
    start_page_matches = re.finditer(r'<start_index_(\d+)>', text)
    matches_list = list(start_page_matches)
    if matches_list:
        start_page = int(matches_list[-1].group(1))
    return start_page


def sanitize_filename(filename, replacement='-'):
    return filename.replace('/', replacement)

def get_pdf_name(pdf_path):
    if isinstance(pdf_path, str):
        pdf_name = os.path.basename(pdf_path)
    elif isinstance(pdf_path, BytesIO):
        pdf_reader = PyPDF2.PdfReader(pdf_path)
        meta = pdf_reader.metadata
        pdf_name = meta.title if meta and meta.title else 'Untitled'
        pdf_name = sanitize_filename(pdf_name)
    return pdf_name


class JsonLogger:
    def __init__(self, file_path):
        pdf_name = get_pdf_name(file_path)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f"{pdf_name}_{current_time}.json"
        os.makedirs("./logs", exist_ok=True)
        self.log_data = []

    def log(self, level, message, **kwargs):
        if isinstance(message, dict):
            self.log_data.append(message)
        else:
            self.log_data.append({'message': message})
        
        with open(self._filepath(), "w") as f:
            json.dump(self.log_data, f, indent=2)

    def info(self, message, **kwargs):
        self.log("INFO", message, **kwargs)

    def error(self, message, **kwargs):
        self.log("ERROR", message, **kwargs)

    def debug(self, message, **kwargs):
        self.log("DEBUG", message, **kwargs)

    def exception(self, message, **kwargs):
        kwargs["exception"] = True
        self.log("ERROR", message, **kwargs)

    def _filepath(self):
        return os.path.join("logs", self.filename)
    


def list_to_tree(data):
    def get_parent_structure(structure):
        if not structure:
            return None
        parts = str(structure).split('.')
        return '.'.join(parts[:-1]) if len(parts) > 1 else None
    
    nodes = {}
    root_nodes = []
    
    for item in data:
        structure = item.get('structure')
        node = {
            'title': item.get('title'),
            'start_index': item.get('start_index'),
            'end_index': item.get('end_index'),
            'nodes': []
        }
        
        nodes[structure] = node
        
        parent_structure = get_parent_structure(structure)
        
        if parent_structure:
            if parent_structure in nodes:
                nodes[parent_structure]['nodes'].append(node)
            else:
                root_nodes.append(node)
        else:
            root_nodes.append(node)
    
    def clean_node(node):
        if not node['nodes']:
            del node['nodes']
        else:
            for child in node['nodes']:
                clean_node(child)
        return node
    
    return [clean_node(node) for node in root_nodes]

def add_preface_if_needed(data):
    if not isinstance(data, list) or not data:
        return data

    if data[0]['physical_index'] is not None and data[0]['physical_index'] > 1:
        preface_node = {
            "structure": "0",
            "title": "Preface",
            "physical_index": 1,
        }
        data.insert(0, preface_node)
    return data



def get_page_tokens(pdf_path, model="gpt-4o-2024-11-20", pdf_parser="PyPDF2"):
    model_for_tiktoken = 'gpt-4' 
    try:
        enc = tiktoken.encoding_for_model(model_for_tiktoken)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base") 
        
    if pdf_parser == "PyPDF2":
        pdf_reader = PyPDF2.PdfReader(pdf_path)
        page_list = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            token_length = len(enc.encode(page_text))
            page_list.append((page_text, token_length))
        return page_list
    elif pdf_parser == "PyMuPDF":
        if isinstance(pdf_path, BytesIO):
            pdf_stream = pdf_path
            doc = pymupdf.open(stream=pdf_stream, filetype="pdf")
        elif isinstance(pdf_path, str) and os.path.isfile(pdf_path) and pdf_path.lower().endswith(".pdf"):
            doc = pymupdf.open(pdf_path)
        page_list = []
        for page in doc:
            page_text = page.get_text()
            token_length = len(enc.encode(page_text))
            page_list.append((page_text, token_length))
        return page_list
    else:
        raise ValueError(f"Unsupported PDF parser: {pdf_parser}")

        

def get_text_of_pdf_pages(pdf_pages, start_page, end_page):
    text = ""
    for page_num in range(start_page-1, end_page):
        text += pdf_pages[page_num][0]
    return text

def get_text_of_pdf_pages_with_labels(pdf_pages, start_page, end_page):
    text = ""
    for page_num in range(start_page-1, end_page):
        text += f"<physical_index_{page_num+1}>\n{pdf_pages[page_num][0]}\n<physical_index_{page_num+1}>\n"
    return text

def get_number_of_pages(pdf_path):
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    num = len(pdf_reader.pages)
    return num



def post_processing(structure, end_physical_index):
    for i, item in enumerate(structure):
        item['start_index'] = item.get('physical_index')
        if i < len(structure) - 1:
            if structure[i + 1].get('appear_start') == 'yes':
                item['end_index'] = structure[i + 1]['physical_index']-1
            else:
                item['end_index'] = structure[i + 1]['physical_index']
        else:
            item['end_index'] = end_physical_index
    tree = list_to_tree(structure)
    if len(tree)!=0:
        return tree
    else:
        for node in structure:
            node.pop('appear_start', None)
            node.pop('physical_index', None)
        return structure

def clean_structure_post(data):
    if isinstance(data, dict):
        data.pop('page_number', None)
        data.pop('start_index', None)
        data.pop('end_index', None)
        if 'nodes' in data:
            clean_structure_post(data['nodes'])
    elif isinstance(data, list):
        for section in data:
            clean_structure_post(section)
    return data

def remove_fields(data, fields=['text']):
    if isinstance(data, dict):
        return {k: remove_fields(v, fields)
            for k, v in data.items() if k not in fields}
    elif isinstance(data, list):
        return [remove_fields(item, fields) for item in data]
    return data

def print_toc(tree, indent=0):
    for node in tree:
        print('  ' * indent + node['title'])
        if node.get('nodes'):
            print_toc(node['nodes'], indent + 1)

def print_json(data, max_len=40, indent=2):
    def simplify_data(obj):
        if isinstance(obj, dict):
            return {k: simplify_data(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [simplify_data(item) for item in obj]
        elif isinstance(obj, str) and len(obj) > max_len:
            return obj[:max_len] + '...'
        else:
            return obj
    
    simplified = simplify_data(data)
    print(json.dumps(simplified, indent=indent, ensure_ascii=False))


def remove_structure_text(data):
    if isinstance(data, dict):
        data.pop('text', None)
        if 'nodes' in data:
            remove_structure_text(data['nodes'])
    elif isinstance(data, list):
        for item in data:
            remove_structure_text(item)
    return data


def check_token_limit(structure, limit=110000):
    list = structure_to_list(structure)
    for node in list:
        num_tokens = count_tokens(node['text'], model='gpt-4o')
        if num_tokens > limit:
            print(f"Node ID: {node['node_id']} has {num_tokens} tokens")
            print("Start Index:", node['start_index'])
            print("End Index:", node['end_index'])
            print("Title:", node['title'])
            print("\n")


def convert_physical_index_to_int(data):
    if isinstance(data, list):
        for i in range(len(data)):
            if isinstance(data[i], dict) and 'physical_index' in data[i]:
                if isinstance(data[i]['physical_index'], str):
                    if data[i]['physical_index'].startswith('<physical_index_'):
                        data[i]['physical_index'] = int(data[i]['physical_index'].split('_')[-1].rstrip('>').strip())
                    elif data[i]['physical_index'].startswith('physical_index_'):
                        data[i]['physical_index'] = int(data[i]['physical_index'].split('_')[-1].strip())
    elif isinstance(data, str):
        if data.startswith('<physical_index_'):
            data = int(data.split('_')[-1].rstrip('>').strip())
        elif data.startswith('physical_index_'):
            data = int(data.split('_')[-1].strip())
        if isinstance(data, int):
            return data
        else:
            return None
    return data


def convert_page_to_int(data):
    for item in data:
        if 'page' in item and isinstance(item['page'], str):
            try:
                item['page'] = int(item['page'])
            except ValueError:
                pass
    return data


def add_node_text(node, pdf_pages):
    if isinstance(node, dict):
        start_page = node.get('start_index')
        end_page = node.get('end_index')
        node['text'] = get_text_of_pdf_pages(pdf_pages, start_page, end_page)
        if 'nodes' in node:
            add_node_text(node['nodes'], pdf_pages)
    elif isinstance(node, list):
        for index in range(len(node)):
            add_node_text(node[index], pdf_pages)
    return


def add_node_text_with_labels(node, pdf_pages):
    if isinstance(node, dict):
        start_page = node.get('start_index')
        end_page = node.get('end_index')
        node['text'] = get_text_of_pdf_pages_with_labels(pdf_pages, start_page, end_page)
        if 'nodes' in node:
            add_node_text_with_labels(node['nodes'], pdf_pages)
    elif isinstance(node, list):
        for index in range(len(node)):
            add_node_text_with_labels(node[index], pdf_pages)
    return


async def generate_node_summary(node, model=None):
    # --- ここを日本語化 ---
    prompt = f"""あなたは文書の一部を与えられます。あなたのタスクは、その部分的な文書でカバーされている主要なポイントについての説明を生成することです。

    部分的な文書のテキスト: {node['text']}
    
    説明文だけを直接返してください。他のテキストは含めないでください。
    """
    response = await ChatGPT_API_async(model, prompt)
    return response


async def generate_summaries_for_structure(structure, model=None):
    nodes = structure_to_list(structure)
    tasks = [generate_node_summary(node, model=model) for node in nodes]
    summaries = await asyncio.gather(*tasks)
    
    for node, summary in zip(nodes, summaries):
        node['summary'] = summary
    return structure


def create_clean_structure_for_description(structure):
    if isinstance(structure, dict):
        clean_node = {}
        for key in ['title', 'node_id', 'summary', 'prefix_summary']:
            if key in structure:
                clean_node[key] = structure[key]
        
        if 'nodes' in structure and structure['nodes']:
            clean_node['nodes'] = create_clean_structure_for_description(structure['nodes'])
        
        return clean_node
    elif isinstance(structure, list):
        return [create_clean_structure_for_description(item) for item in structure]
    else:
        return structure


def generate_doc_description(structure, model=None):
    # --- ここを日本語化 ---
    prompt = f"""あなたは文書の説明を生成する専門家です。
    文書の構造が与えられます。あなたのタスクは、他の文書と区別しやすくするために、その文書についての一文の説明を生成することです。
    
    文書の構造: {structure}
    
    説明文だけを直接返してください。他のテキストは含めないでください。
    """
    response = ChatGPT_API(model, prompt)
    return response


def reorder_dict(data, key_order):
    if not key_order:
        return data
    return {key: data[key] for key in key_order if key in data}


def format_structure(structure, order=None):
    if not order:
        return structure
    if isinstance(structure, dict):
        if 'nodes' in structure:
            structure['nodes'] = format_structure(structure['nodes'], order)
        if not structure.get('nodes'):
            structure.pop('nodes', None)
        structure = reorder_dict(structure, order)
    elif isinstance(structure, list):
        structure = [format_structure(item, order) for item in structure]
    return structure


class ConfigLoader:
    def __init__(self, default_path: str = None):
        if default_path is None:
            # config.yamlが存在しない場合を考慮し、デフォルト値を空の辞書にするか、例外処理が必要
            # __file__ はスクリプトファイルが保存されている場所を指すため、
            # このコードが直接実行されるか、適切にインポートされる必要があります。
            # ここでは仮にカレントディレクトリを基準にします。
            # default_path = Path(__file__).parent / "config.yaml"
            default_path = Path.cwd() / "config.yaml" # より安全な代替案
        
        # yamlをインポートする必要があります
        try:
            import yaml
        except ImportError:
            logging.error("PyYAMLがインストールされていません。 `pip install PyYAML` を実行してください。")
            raise
            
        self._default_dict = self._load_yaml(default_path)

    @staticmethod
    def _load_yaml(path):
        # yamlをインポートする必要があります
        try:
            import yaml
        except ImportError:
            logging.error("PyYAMLがインストールされていません。 `pip install PyYAML` を実行してください。")
            raise
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            # config.yaml が見つからない場合は空の辞書を返す
            logging.warning(f"Config file not found at {path}. Using empty defaults.")
            return {}

    def _validate_keys(self, user_dict):
        unknown_keys = set(user_dict) - set(self._default_dict)
        if unknown_keys:
            raise ValueError(f"Unknown config keys: {unknown_keys}")

    def load(self, user_opt=None) -> config:
        if user_opt is None:
            user_dict = {}
        elif isinstance(user_opt, config):
            user_dict = vars(user_opt)
        elif isinstance(user_opt, dict):
            user_dict = user_opt
        else:
            raise TypeError("user_opt must be dict, config(SimpleNamespace) or None")

        self._validate_keys(user_dict)
        merged = {**self._default_dict, **user_dict}
        return config(**merged)