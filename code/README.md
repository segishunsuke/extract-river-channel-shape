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

### 河床標高の設定方法

このプログラムが用いる，河床標高の設定方法を述べます．このプログラムは，広矩形単断面を持つ開水路の不等流計算の基礎式である，
```math
\frac{dH}{dx} + \frac{1}{2g} \frac{d}{dx} \left( \frac{Q}{Bh} \right)^2 + \frac{n^2 Q^2}{B^2 h^{10/3}} = 0
```
を用いています．ここで，$`H`$は水面標高(m)を，$`x`$は河道の縦断距離(m)（上流側を正に取る）を，$`g`$は重力加速度(m/s$`^2`$)を，$`Q`$は流量(m$`^3`$/s)を，$`B`$は横断方向の水面の幅(m)を，$`h`$は水深(m)を，$`n`$は粗度係数(m$`^{-1/3}`$s)を表します．各横断面における水面の幅$`B`$と，水面標高$`H`$は，DEMから推定することができます．よって，各横断面における平水流量$`Q`$を与えれば，この微分方程式を用いて，各横断面における未知の水深$`h`$を計算できます．

親フォルダの[READMEの4-6-13](../README.md#4-6-13)にて挙げられている，[basic_parameters.csv](./basic_parameters.csv)の6つのパラメータは，この微分方程式に関するものです．

- Water surface tolerance: 最小標高から何mまでの範囲を水面と見なすか
- Difference in differential equation: 上記微分方程式を$`x`$軸方向に離散化する際の差分間隔(m)
- Roughness coefficient: 粗度係数$`n`$
- Minimum water surface slope: 水面標高の勾配の最小値$`\eta_\mathrm{min}`$
- Number of samples for median water surface: 水面標高を平滑化する際に利用する横断面数$`M_1`$
- Number of samples for median riverbed: 河床標高を平滑化する際に利用$する横断面数`M_2`$

[river_extractor.py](./river_extractor.py)は，以下の手順に従い，DEMから水面の標高$`H`$を推定します．

まず，各横断面$`i`$について，堤外地の最小標高を水面標高と見なし，$`\tilde{H}_i`$とします．そのうえで，複数の横断面について，$`\tilde{H}_i`$の中央値を取ることにより，平滑化を行います．
```math
\hat{H}_i = \mathrm{median} \left[ \tilde{H}_{i-r_1(i)}, \cdots, \tilde{H}_{i+r_1(i)} \right]
```
```math
r_1(i) = \min \left[ M_1 \div 2 , N - i, i - 1 \right]
```
ここで，$`r_1(i)`$は，中央値の計算に用いる横断面を，横断面$`i`$の前後それぞれにいくつ設けるのかを表します．$`M_1 \ge 1`$はユーザーにより設定される奇数の定数です．$`N`$は横断面の総数です．横断面1は最下流の横断面，横断面$`N`$は最上流の横断面とします．対象の河道の上流端と下流端では，横断面$`i`$の前後に$`M_1 \div 2`$個の横断面を設けられないため，それよりも少ない個数の横断面を用いて中央値が計算されます．

$`\hat{H}_i`$を用いても，下流側の水面標高が上流側の水面標高よりも高くなることがあります．そこで，水面の標高が河道を下るのに伴い単調に減少するように，
```math
H_N = \hat{H}_N
```
```math
H_i = \min \left[ \hat{H}_i, H_{i+1} - \eta_\mathrm{min} D \right] \quad (1 \le i < N)
```
と設定します．ここで，$`D`$(m)は隣り合う横断面間の距離です．$`\eta_\mathrm{min}>0`$はユーザーにより設定される定数であり，水面勾配の最小値を表します．

次に，各横断面$`i`$について，水面の幅$`B_i`$を求めます．2025年3月以降に更新されたDEMと，それ以前のDEMでは求め方が異なります．

- 2025年3月以降に更新されたDEM: 堤外地の最小標高から$`\Delta_i`$(m)以内の範囲の標高を有する区間を水面と見なす．
- それ以前のDEM: 標高データが欠測している区間を水面と見なす．

$`\Delta_i`$のデフォルト値はWater surface toleranceです．以上の対応の違いはDEMにおける水域の扱いに由来します．2025年3月以降に更新されたDEMでは，水域の標高として水面の標高が記録されているのに対して，それ以前のDEMでは，水域の標高が欠測しています．

以上により得られた$`H_i`$, $`B_i`$を，開水路の不等流計算の基礎式に代入して水深$`h_i`$を計算します．河床標高は$`H_i - h_i`$として評価できますが，この評価値は縦断方向に大きく変動します．そこで，$`H_i - h_i`$の中央値を取ることにより，平滑化処理をします．
```math
\underline{z}_i = \mathrm{median} \big[ H_{i-r_2(i)} - h_{i-r_2(i)}, \cdots, H_{i+r_2(i)} - h_{i+r_2(i)} \big]
```
```math
r_2(i) = \min \left[ M_2 \div 2 , N - i, i - 1 \right]
```
$`\underline{z}_i`$が河床標高の設定値となります．$`M_2 \ge 1`$はユーザーにより設定される奇数の定数です．

このフォルダに置かれている[basic_parameters.csv](./basic_parameters.csv)では，$`\Delta_i`$のデフォルト値に1mを，粗度係数$`n`$に0.03を，$`\eta_\mathrm{min}`$に10万分の1を，$`M_1`$に11を，$`M_2`$に100万1（可能な限り多くの横断面を利用）を設定しています．$`\eta_\mathrm{min}`$の設定値を変える場合，ゼロにはできないことに注意して下さい．ゼロにすると∞の水深が発生して計算が停止することがあります．
