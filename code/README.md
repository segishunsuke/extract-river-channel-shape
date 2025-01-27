## 概要

このフォルダは，氾濫解析用の河道縦横断データを自動抽出するPythonプログラムを格納しています．

格納されているファイルの内容は以下の通りです．

- [extract_river_channel_shape.py](./extract_river_channel_shape.py): プログラムの本体
- [dem.py](./dem.py): 数値標高モデルから標高を読み取るサブプログラム
- [open_channel.py](./open_channel.py): 開水路の不等流計算の基礎式を用いて水深を逆算するサブプログラム
- [basic_parameters.csv](./basic_parameters.csv): "extract_river_channel_shape.py"で用いられるパラメータの設定ファイル

以上の4つのファイルは全て同一のディレクトリに置かれる必要があります．

プログラムの使用方法については，親フォルダの[README](../README.md)を見て下さい．

### 水深の逆算方法

ここでは，"[open_channel.py](./open_channel.py)"に実装されている，水深の逆算方法を述べます．このプログラムは，広矩形単断面を持つ水路の不等流計算の基礎式である，
```math
\frac{dH}{dx} + \frac{1}{2g} \frac{d}{dx} \left( \frac{Q}{Bh} \right)^2 + \frac{\mu^2 Q^2}{B^2 h^{10/3}} = 0
```
を用いています．
