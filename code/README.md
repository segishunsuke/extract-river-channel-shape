## 概要

このフォルダは，氾濫解析用の河道縦横断データを自動抽出するPythonプログラムを格納しています．

格納されているファイルの内容は以下の通りです．

- [gui_main.py](./gui_main.py): プログラムの本体を操作するためのGUI
- [river_extractor.py](./river_extractor.py): プログラムの本体
- [basic_parameters.csv](./basic_parameters.csv): river_extractor.pyで用いられるパラメータの設定ファイル
- [dem.py](./dem.py): 基盤地図情報5mメッシュDEM（DEM5A, DEM5B, DEM5C）から標高を読み取るサブプログラム
- [dem1a.py](./dem1a.py): 基盤地図情報1mメッシュDEM（DEM1A）から標高を読み取るサブプログラム
- [open_channel.py](./open_channel.py): 開水路の不等流計算の基礎式を用いて水深を計算するサブプログラム
- [rotation.py](./rotation.py): 交差している横断面の判定と，横断面の回転による交差の解消を担うサブプログラム
- [flow_accumulation_area.py](./flow_accumulation_area.py): [日本域表面流向マップ](https://hydro.iis.u-tokyo.ac.jp/~yamadai/JapanDir/)を用いて，横断面別の上流集水面積を計算するサブプログラム

以上の8つのファイルは全て同一のディレクトリに置かれる必要があります．

プログラムの使用方法については，親フォルダの[README](../README.md)を見て下さい．
