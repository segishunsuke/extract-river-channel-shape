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

親フォルダの[READMEの4-4-7](../README.md#4-4-7)にて挙げられている，"[basic_parameters.csv](./basic_parameters.csv)"の4つのパラメータは，この微分方程式に関するものです．

- Difference in differential equation: 上記微分方程式を$`x`$軸方向に離散化する際の差分間隔(m)
- Roughness coefficient: 粗度係数$`n`$
- Minimum water surface slope: DEMから水面の標高$`H`$を推測する際に利用
- Number of samples for median calculation: DEMから水面の標高$`H`$を推測する際に利用

[extract_river_channel_shape.py](./extract_river_channel_shape.py)は，以下の手順に従い，DEMから水面の標高$`H`$を推測します．

まず，各横断面$`i`$について，堤外地の最小の標高値を水面の標高の近似値と見なし，$`\tilde{H}_i`$とします．そのうえで，複数の横断面について，$`\tilde{H}_i`$の中央値を取ることにより，近似誤差の影響を抑えます．
```math
\hat{H}_i = \mathrm{median} \left[ \tilde{H}_{i-r_s(i)}, \tilde{H}_{i-r_s(i)+1}, \cdots, \tilde{H}_{i+r_s(i)} \right]
```
```math
r_s(i) = \min \left[ m \div 2 , N - i, i - 1 \right]
```
ここで，$`r_s(i)`$は，中央値の計算に用いる横断面を，横断面$`i`$の前後それぞれにいくつ設けるのかを表します．$`m \ge 1`$は分析者により設定される奇数の定数です．$`N`$は横断面の総数です．横断面1は最下流の横断面，横断面$`N`$は最上流の横断面とします．対象の河道の上流端と下流端では，横断面$`i`$の前後に$`m \div 2`$個の横断面を設けられないため，それよりも少ない個数の横断面を用いて中央値が計算されます．

$`\hat{H}_i`$を用いても，下流側の水面標高が上流側の水面標高よりも高くなることがあります．そこで，水面の標高が河道を下るのに伴い単調に減少するように，
```math
H_N = \hat{H}_N
```
```math
H_i = \min \left[ \hat{H}_i, H_{i+1} - \eta_\mathrm{min} D \right] \quad (1 \le i < N)
```
と設定します．ここで，$`\eta_\mathrm{min}>0`$は分析者により設定される定数であり，水面勾配の最小値を表します．こうして得られた$`H_i`$を，開水路の不等流計算の基礎式に代入して水深を計算します．

"[basic_parameters.csv](./basic_parameters.csv)"のパラメータ，"Minimum water surface slope"は$`m`$を，"Number of samples for median calculation"は$`\eta_\mathrm{min}`$を指します．

このフォルダに置かれている"[basic_parameters.csv](./basic_parameters.csv)"では，$`m`$に1000001（事実上∞）を，$`\eta_\mathrm{min}`$に10万分の1を設定しています．$`m`$と$`\eta_\mathrm{min}`$にはこれらのデフォルト値を用いることを推奨します．$`\eta_\mathrm{min}`$の設定値を変える場合，ゼロにはできないことに注意して下さい．ゼロにすると∞の水深が発生して計算が停止することがあります．

粗度係数$`n`$の設定値には0.05を推奨します．この値を大きくすると，一般に水深は深くなります．
