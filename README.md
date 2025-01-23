# Overview
日本の数値標高モデルと国土数値情報の河川データから，氾濫解析用の河道縦横断データを自動抽出するプログラムを公開しています．

## リポジトリの構成

### [extract-centerline](./extract-centerline/)

国土数値情報の河川データから，指定された河川コードに対応する河川の河道中心線を抽出し，シェープファイル形式にて保存するPythonプログラムを格納しています．
[extract_centerline.py](./extract-centerline/extract_centerline.py)がプログラムの本体です．

#### 必要な外部データ

このプログラムを用いるには，国土数値情報の河川データ（XML形式）が必要です．国土数値情報の河川データは下記URLからダウンロードして下さい．

[https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html](https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html)



#### インプットデータ

このプログラムを用いるには，extract_centerline.pyと同じディレクトリに以下のファイルを置く必要があります．
- George Washington

### extract-river-coordinates

