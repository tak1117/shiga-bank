ragに必要なjson作成

```
python PageIndex\run_pageindex.py --pdf_path <pdfのパス>
```
rag実行(現在質問はxlsxの特定のセルを繰り返し読む形)

```
python PageIndex\pageindex\rag.py 
```

評価

```
python PageIndex\pageindex\evaluate.py
python PageIndex\pageindex\accuracy.py                   
```
