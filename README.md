このリポジトリでは，日本の数値標高モデルと国土数値情報の河川データから，氾濫解析用の河道縦横断データを自動抽出するPythonプログラムを公開しています．

このREADMEではプログラムの使用方法を段階に分けて説明します．

## 1. 必要なライブラリのインストール

このプログラムを用いるには，以下の2件のPythonライブラリが必要です．

- [PyShp](https://pypi.org/project/pyshp/)
- [Pyproj](https://github.com/pyproj4/pyproj)

お使いのPython環境にこれらのライブラリがインストールされていない場合は，プロンプト上で以下のコマンドを入力して下さい．
```
pip install pyshp
```
```
pip install pyproj
```

## 2. 河道中心線の抽出

国土数値情報の河川データから，縦横断データの抽出対象となる河川の河道中心線のデータを取得します．

### プログラムのダウンロード

"[extract-centerline](./extract-centerline)"に格納されている以下の2つのファイルをダウンロードし，同一のディレクトリに置いて下さい．

- [extract_centerline.py](./extract-centerline/extract_centerline.py)
- [input_extract_centerline.csv](./extract-centerline/input_extract_centerline.csv)

### 国土数値情報　河川データのダウンロード

下記URLから，縦横断データの抽出対象となる河川を含む都道府県のデータをダウンロードして下さい．

[https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html](https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html)

ダウンロードしたzipファイルを展開し，W05-XX-XX.xmlという名前のファイルを"extract_centerline.py"の置かれたディレクトリに置いて下さい．


