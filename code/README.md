## 概要

このフォルダは，氾濫解析用の河道縦横断データを自動抽出するPythonプログラムを格納しています．

格納されているPythonプログラムの内容は以下の通りです．

- [extract_river_channel_shape.py](./extract_river_channel_shape.py): プログラムの本体
- [dem.py](./dem.py): 数値標高モデルから標高を読み取るサブプログラム
- [open_channel.py](./open_channel.py): 開水路の不等流計算の基礎式を用いて水深を逆算するサブプログラム

以上の3つのファイルは全て同一のディレクトリに置かれる必要があります．

プログラムの使用方法については，親フォルダの[README](../README.md)を見て下さい．

以下には，各プログラムの技術的な内容を記載します．

## dem.py


