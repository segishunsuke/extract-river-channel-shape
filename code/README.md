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

ここでは，"[open_channel.py](./open_channel.py)"に実装されている，水深の逆算方法を述べます．このプログラムは，広矩形単断面を持つ開水路の不等流計算の基礎式である，
```math
\frac{dH}{dx} + \frac{1}{2g} \frac{d}{dx} \left( \frac{Q}{Bh} \right)^2 + \frac{n^2 Q^2}{B^2 h^{10/3}} = 0
```
を用いています．ここで，$`H`$は水面の標高(m)を，$`x`$は河道の縦断距離(m)（上流側を正に取る）を，$`g`$は重力加速度(m/s$`^2`$)を，$`Q`$は流量(m$`^3`$/s)を，$`B`$は横断方向の水面の幅(m)を，$`h`$は水深(m)を，$`n`$は粗度係数(m$`^{-1/3}`$s)を表します．各横断面における水面の幅$`B`$と，水面の標高$`H`$は，DEMから推測することができます．よって，各横断面における平水流量$`Q`$を与えれば，この微分方程式を用いて，各横断面における未知の水深$`h`$を計算できます．

親フォルダの[READMEの4-4-7](../README.md#4-4-7)にて挙げられている4つのパラメータは，この微分方程式に関するものです．

- Difference in differential equation: 上記微分方程式を$`x`$軸方向に離散化する際の差分間隔(m)
- Roughness coefficient: 粗度係数$`n`$
- Minimum water surface slope: DEMから水面の標高$`H`$を推測する際に利用
- Number of samples for median calculation: DEMから水面の標高$`H`$を推測する際に利用

[extract_river_channel_shape.py](./extract_river_channel_shape.py)は，以下の手順に従い，DEMから水面の標高$`H`$を推測します．

まず，各横断面$`i`$について，堤外地の最小の標高値を水面の標高の近似値と見なし，$\tilde{H}_i$とする．そのうえで，複数の横断面について，$\tilde{H}_i$の中央値を取ることにより，近似誤差の影響を抑える．
```math
\hat{H}_i = \mathrm{median} \left[ \tilde{H}_{i-r_s(i)}, \tilde{H}_{i-r_s(i)+1}, \cdots, \tilde{H}_{i+r_s(i)} \right] \label{eq7}
```
```math
r_s(i) = \min \left[ m \div 2 , n - i, i - 1 \right]
```
