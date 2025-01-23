## 概要

このフォルダは，国土数値情報の河川データから，指定された河川コードに対応する河川の河道中心線を抽出し，シェープファイル形式にて保存するPythonプログラムを格納しています．
プログラム名は"[extract_centerline.py](./extract_centerline.py)"です．

このプログラムのアウトプットファイルである，"river.shp"とその支援ファイルは，河道縦横断データの抽出プログラムのインプットファイルとなります．

## 必要なPythonライブラリ

このプログラムを用いるには，PythonのライブラリであるPyShpが必要です．

[https://pypi.org/project/pyshp/](https://pypi.org/project/pyshp/)

PyShpをインストールするには，プロンプト上で以下のコマンドを入力して下さい．
```
pip install pyshp
```

## 必要な外部データ

このプログラムを用いるには，国土数値情報の河川データ（XML形式）が必要です．国土数値情報の河川データは下記URLからダウンロードして下さい．

[https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html](https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html)

## インプットデータ

このプログラムを用いるには，"extract_centerline.py"と同じディレクトリに以下のファイルを置く必要があります．

- W05-xx_xx.xml: 抽出対象の河川を含む，国土数値情報のxmlファイル
- input_extract_centerline.csv: 河川コードを指定するためのインプットファイル

このフォルダに格納されている"[input_extract_centerline.csv](./input_extract_centerline.py)"はインプットファイルのテンプレートです．
インプットファイルは2行2列のCSV形式であり，各行の意味は以下の通りです．

- Data file name: 抽出対象の河川を含む，国土数値情報のxmlファイルのファイル名
- River code: 抽出対象の河川の河川コード

テンプレートでは，北海道の河川データのxmlファイルと，石狩川の河川コードを指定しています．

河川コードは以下に示す，国土交通省のWebサイトで検索できます．

[https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)

## アウトプットデータ

[extract_centerline.py](./extract-centerline/extract_centerline.py)を実行すると，以下の2種類のシェープファイル（およびその支援ファイル）が出力されます．

- river.shp: 指定された河川の河道中心線のラインデータを格納したファイル
- river_points.shp: 抽出対象の河川の河川コード

