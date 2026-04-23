# 基本パラメータ詳細解説 (basic_parameters.csv)

`basic_parameters.csv` の全25項目の詳細な設定方法およびアルゴリズムの仕様を整理します．

#### Plane rectangular coordinate system
対象の河道をカバーする平面直角座標系のEPSGコードを "epsg:6680" のように記載して下さい．コードは以下のURLから検索できます．
[https://lemulus.me/column/epsg-list-gis#2011JGD2011](https://lemulus.me/column/epsg-list-gis#2011JGD2011)

#### Initial point ID, Terminal point ID
上流端および下流端のポイント識別番号です．上流端は抽出範囲より1kmほど上流に設定することを推奨します．

#### Flow
対象河川の代表地点の平水流量（m3/s）です．[水文水質データベース](http://www1.river.go.jp/)等から取得して下さい．
データが入手できない場合は，[J-FlwDir](https://hydro.iis.u-tokyo.ac.jp/~yamadai/JapanDir/)の集水面積から比流量を用いて設定して下さい．

#### Estimate water depth
DEMから得られない水面下の水深を推定するかどうか（0：しない，1：する）の設定です．

#### Clear crossings
横断面の交差を自動で解消するかどうか（0：しない，1：する）の設定です．

#### tol1-3（境界探索しきい値）
横断面の左右岸端の位置設定に利用されます．河道中心線から外側へ進みながら，以下の3条件が満たされた地点で標高読み取りが停止し，最高地点を岸端とします．
1. 最低標高と最高標高の差が `tol1`(m)以上
2. 現在地点の標高と最高標高の差が `tol2`(m)以上
3. 現在地点の勾配が `tol3`以下
<img src="./assets/images/tol.png" width="400px">

#### tol4-5, adjust1-3（自動調整）
探索が永久に終わらないのを防ぐため，中心線から `tol4`(m)以上離れるか，最低標高より `tol5`(m)以上高くなった場合，`tol1-3` に `adjust1-3` を乗じて再探索します．

#### DEM type
- 5mメッシュDEM: `A`（5A→5B→5Cの順に自動選択）
- 1mメッシュDEM: `1A`

#### Distance between sections
河道中心線に沿った，横断面の取得間隔（m）です．

#### Transverse interval
横断方向の標高取得間隔（m）です．

#### Margin
岸端の外側に取るマージンの上限（m）です．0mに設定すると河道外を切り捨てます．

#### iRIC format
- 1: iRIC（無償ソフトウェア）形式
- 0: DioVISTA/Flood（有償ソフトウェア）形式

#### 水深推定用パラメータ
以下のパラメータは水深推定に利用されます．
- `Water surface tolerance`
- `Difference in differential equation`
- `Roughness coefficient`
- `Minimum water surface slope`
- `Number of samples for median water surface`
- `Number of samples for median riverbed`
