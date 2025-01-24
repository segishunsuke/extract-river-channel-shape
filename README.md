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

### 2-1. 河道中心線の抽出を行うプログラムのダウンロード

"[extract-centerline](./extract-centerline)"に格納されている以下の2つのファイルをダウンロードし，同一のディレクトリに置いて下さい．

- [extract_centerline.py](./extract-centerline/extract_centerline.py)
- [input_extract_centerline.csv](./extract-centerline/input_extract_centerline.csv)

### 2-2. 国土数値情報　河川データのダウンロード

下記URLから，対象の河川を含む都道府県のデータをダウンロードして下さい．

[https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html](https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html)

ダウンロードしたzipファイルに含まれている，W05-XX-XX.xmlという名前のファイルを"extract_centerline.py"の置かれたディレクトリに置いて下さい．

### 2-3. 河川コードの指定

"input_extract_centerline.csv"を開き，1行2列に国土数値情報のxmlファイルの名前（W05-XX-XX.xml）を，2行2列に対象の河川の河川コードを記載して上書き保存して下さい．

河川コードは以下に示す，国土交通省のWebサイトで検索できます．

[https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)

このリポジトリに置かれている"[input_extract_centerline.csv](./extract-centerline/input_extract_centerline.csv)"では，北海道の河川データのxmlファイルと，石狩川の河川コードが指定されています．

### 2-4. プログラムの実行<a name="2-4"></a>

"[extract_centerline.py](./extract-centerline/extract_centerline.py)"を実行して下さい．

```
python extract_centerline.py
```

プログラムが終了すると，以下の2種類のシェープファイル（およびその支援ファイル）が出力されます．

- river.shp: 指定された河川の河道中心線のラインデータを格納したファイル
- river_points.shp: "river.shp"のラインデータを構成するポイントのデータを格納したファイル

## 3. 河道縦横断データの抽出範囲の決定

[2-4](#2-4)

"river_points.shp"は，ユーザーが河道縦横断データの抽出範囲を指定する際に利用します．このシェープファイルに格納されている各ポイントは，属性として"id"という識別番号を持ちます．この識別番号で始点と終点を指示することにより，"river.shp"のラインデータのうち，どの範囲を用いるのかを指定します．

