ragに必要なjson作成

```
python Page_Index\run_pageindex.py --pdf_path <pdfのパス>
```
rag実行(現在質問はxlsxの特定のセルを繰り返し読む形)

```
python Page_Index\pageindex\rag.py 
```

評価

```
python Page_Index\pageindex\evaluate.py
python Page_Index\pageindex\accuracy.py                   
```
