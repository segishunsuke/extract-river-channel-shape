## 概要

このフォルダは，国土数値情報の河川データから，指定された河川コードに対応する河川の河道中心線を抽出し，シェープファイル形式にて保存するPythonプログラムを格納しています．
[extract_centerline.py](./extract_centerline.py)がプログラムの本体です．

このプログラムのアウトプットファイルは，河道縦横断データの抽出プログラムのインプットファイルとなります．

## 必要な外部データ

このプログラムを用いるには，国土数値情報の河川データ（XML形式）が必要です．国土数値情報の河川データは下記URLからダウンロードして下さい．

[https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html](https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html)

## インプットデータ

このプログラムを用いるには，extract_centerline.pyと同じディレクトリに以下のファイルを置く必要があります．

- W05-xx_xx.xml: 抽出対象の河川を含む，国土数値情報のxmlファイル
- input_extract_centerline.csv: 河川コードを指定するためのインプットファイル

このフォルダに格納されている[input_extract_centerline.csv](./input_extract_centerline.py)はインプットファイルのテンプレートです．
インプットファイルは2行2列のCSV形式であり，各行の意味は以下の通りです．

- Data file name: 抽出対象の河川を含む，国土数値情報のxmlファイルのファイル名
- River code: 抽出対象の河川の河川コード

テンプレートでは，北海道の河川データのxmlファイルと，石狩川の河川コードを指定しています．

河川コードは以下に示す，国土交通省のWebサイトで検索できます．

[https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)
