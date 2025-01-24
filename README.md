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

### 2-1. 河道中心線の抽出を行うプログラムの準備

"[extract-centerline](./extract-centerline)"に格納されている以下の2つのファイルをダウンロードし，同一のディレクトリに置いて下さい．

- [extract_centerline.py](./extract-centerline/extract_centerline.py)
- [input_extract_centerline.csv](./extract-centerline/input_extract_centerline.csv)

### 2-2. 国土数値情報・河川データの準備

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

[2-4](#2-4)で取得した"river_points.shp"をGISソフトウェアで開いて下さい．

例として，石狩川の"river_points.shp"をQGISで開き，石狩川河川敷公園（座標：43.130921N, 141.533418E）付近を拡大表示したものを以下の図に示します．

<img src="./assets/images/river_points.png" width="400px">

"river_points.shp"に格納されているポイントデータは，属性として"id"という識別番号を持ちます．

識別番号は上流から下流に向けて昇順に並んでいます．

上の図に示した石狩川の例では，2つのポイントデータの識別番号が表示されています．図の左（下流側）のポイントの識別番号は5981，右（上流側）のポイントの識別番号は5967です．

"river_points.shp"のデータをGISソフトウェア上で閲覧しながら，河道縦横断データの抽出範囲を決めて下さい．

抽出範囲を決めたら，その範囲の上流端のポイントの識別番号と，下流端のポイントの識別番号をメモして下さい．これらの識別番号は，河道縦横断データの抽出を行うプログラムに対して，抽出範囲を指示するために用いられます．

上流端のポイントについては，抽出したい範囲から1kmほど上流に設定して下さい．これは，河道縦横断データの抽出を行うプログラムが，下流端のポイントから標高の読み取りを開始し，上流端のポイントの直前で標高の読み取りを終了するためです．そのため，上流端のポイントの標高は読み取られません．

なお，"river_points.shp"は，利用者が河道縦横断データの抽出範囲を決定するために用いるファイルであり，河道縦横断データの抽出を行うプログラムには利用されません．

## 4. 河道縦横断データの抽出（初回）

### 4-1. 河道中心線の抽出を行うプログラムの準備

"[extract-centerline](./extract-centerline)"に格納されている以下の2つのファイルをダウンロードし，同一のディレクトリに置いて下さい．

- [extract_centerline.py](./extract-centerline/extract_centerline.py)
- [input_extract_centerline.csv](./extract-centerline/input_extract_centerline.csv)


