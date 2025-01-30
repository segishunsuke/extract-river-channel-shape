このリポジトリでは，日本の数値標高モデル（Degital Elevation Model, DEM）と国土数値情報の河川データから，氾濫解析用の河道縦横断データを自動抽出するPythonプログラムを公開しています．

このREADMEではプログラムの使用方法を段階に分けて説明します．

## 1. 必要なライブラリのインストール

このプログラムを用いるには，以下の2件のPythonライブラリが必要です．

- [PyShp](https://pypi.org/project/pyshp/)
- [Pyproj](https://github.com/pyproj4/pyproj)

お使いのPython環境にこれらのライブラリがインストールされていない場合は，プロンプト上で以下のコマンドを入力してインストールを行って下さい．
```
pip install pyshp
```
```
pip install pyproj
```

## 2. 河道中心線の抽出<a name="2"></a>

国土数値情報の河川データから，縦横断データの抽出対象となる河川の河道中心線のデータを取得します．

### 2-1. 河道中心線の抽出を行うプログラムの準備

"[extract-centerline](./extract-centerline)"に格納されている以下の2つのファイルをダウンロードし，同一のディレクトリに置いて下さい．

- [extract_centerline.py](./extract-centerline/extract_centerline.py)
- [input_extract_centerline.csv](./extract-centerline/input_extract_centerline.csv)

### 2-2. 国土数値情報・河川データの準備

下記URLから，対象の河川を含む都道府県のデータをダウンロードして下さい．

[https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html](https://nlftp.mlit.go.jp/ksj/jpgis/datalist/KsjTmplt-W05.html)

ダウンロードしたzipファイルに含まれている，W05-XX-XX.xmlという名前のファイルを"extract_centerline.py"の置かれたディレクトリに置いて下さい．

### 2-3. 河川コードの指定

"input_extract_centerline.csv"を開き，二つの項目の設定を行ってから上書き保存して下さい．

各項目の意味は以下の通りです．

- Data file name: 国土数値情報のxmlファイルの名前（W05-XX-XX.xml）
- River code: 対象の河川の河川コード

河川コードは以下に示す，国土交通省のWebサイトで検索できます．

[https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)

このリポジトリに置かれている"[input_extract_centerline.csv](./extract-centerline/input_extract_centerline.csv)"では，北海道の河川データのxmlファイルと，石狩川の河川コードが指定されています．

### 2-4. プログラムの実行<a name="2-4"></a>

"[extract_centerline.py](./extract-centerline/extract_centerline.py)"を実行して下さい．

```
python extract_centerline.py
```

プログラムが終了すると，以下のシェープファイル（およびその支援ファイル）が出力されます．

- river_centerline.shp: 指定された河川の河道中心線を構成するポイントのデータを格納したファイル

## 3. 河道縦横断データの抽出範囲の決定<a name="3"></a>

[2-4](#2-4)で取得した"river_centerline.shp"をGISソフトウェアで開いて下さい．

例として，石狩川の"river_centerline.shp"をQGISで開き，石狩川河川敷公園（座標：43.130921N, 141.533418E）付近を拡大表示したものを以下の図に示します．

<img src="./assets/images/river_points.png" width="400px">

"river_centerline.shp"に格納されているポイントデータは，属性として"id"という識別番号を持ちます．

識別番号は上流から下流に向けて昇順に並んでいます．

上の図に示した石狩川の例では，2つのポイントデータの識別番号が表示されています．図の左（下流側）のポイントの識別番号は5981，右（上流側）のポイントの識別番号は5967です．

"river_centerline.shp"のデータをGISソフトウェア上で閲覧しながら，河道縦横断データの抽出範囲を決めて下さい．

抽出範囲を決めたら，その範囲の上流端のポイントの識別番号と，下流端のポイントの識別番号をメモして下さい．これらの識別番号は，河道縦横断データの抽出を行うプログラムに対して，抽出範囲を指示するために用いられます．

上流端のポイントは，抽出したい範囲から1kmほど上流に設定して下さい．これは，河道縦横断データの抽出を行うプログラムが，下流端のポイントから標高の読み取りを開始し，上流端のポイントの直前で標高の読み取りを終了するためです．そのため，上流端のポイントの標高は読み取られません．

## 4. 河道縦横断データの抽出

### 4-1. プログラムの準備

"[code](./code)"に格納されている以下の4つのファイルをダウンロードし，同一のディレクトリに置いて下さい．

- [extract_river_channel_shape.py](./code/extract_river_channel_shape.py)
- [dem.py](./code/dem.py)
- [open_channel.py](./code/open_channel.py)
- [basic_parameters.csv](./code/basic_parameters.csv)

### 4-2. 河道中心線のデータの準備

[2-4](#2-4)で取得した"river_centerline.shp"とその支援ファイルを"extract_river_channel_shape.py"の置かれたディレクトリに置いて下さい．

### 4-3. DEMデータの準備

下記URLから，河道縦横断データの抽出範囲を含む，5mメッシュDEMデータ（DEM5A, DEM5B, DEM5C）をダウンロードして下さい．

[https://fgd.gsi.go.jp/download/menu.php](https://fgd.gsi.go.jp/download/menu.php)

ダウンロードの手順は以下の通りです．

1. 「基盤地図情報　数値標高モデル」の「ファイル選択へ」をクリックする
2. 地図上で対象範囲の2次メッシュをクリックして全て選択する
3. 「ダウンロードファイル確認へ」をクリックする
4. 「このページをまとめてダウンロード」をクリックする
   - ファイルのダウンロードには基盤地図情報のサイトへのログインが必要です．アカウントは誰でも無料で作成できます．
   - ダウンロードするファイル数が多い場合には，ダウンロードファイルリストが複数ページに渡ることがあります．その場合には，ページごとに「このページをまとめてダウンロード」をクリックしなければいけません．

ダウンロードしたzipファイルには，"FG-GML-XXXX-XX-DEM5X.zip"という名前のファイルが含まれています．これらのzipファイルを全て展開し，中に含まれている"FG-GML-XXXX-XX-XX-DEM5X-XXXXXXXX.xml"という名前のファイルを全て同一のフォルダに置いて下さい．Windows PCをお使いの場合は，zipファイルの展開に[7-zip](https://7-zip.opensource.jp/)の「ここに展開」機能を使うことにより，複数のzipファイルの展開を効率的に行えます．

DEMのxmlファイルを置いたフォルダの名前を"elevation"とし，"extract_river_channel_shape.py"の置かれたディレクトリに置いて下さい．

ここまでの作業が完了し，"extract_river_channel_shape.py"の置かれたディレクトリの内容が以下の図のようになっていれば，プログラムを実行するための準備が整ったことになります．

<img src="./assets/images/files.png">

### 4-4. 基本パラメータの設定

"basic_parameters.csv"を開き，プログラムが使用する基本パラメータの設定を行って下さい．

csvファイルは18行2列のファイルで，各行が一つのパラメータに対応しています．1列目がパラメータ名，2列目がパラメータの設定値です．

18個のパラメータのうち，対象の河道に応じて設定値を変えなければいけないのは，最初の4つです．その他のパラメータについては，"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"の設定値をそのまま用いても構いません．"[code](./code)"に格納されているファイルでは，石狩川の河道の，夕張川との合流部から河口までの範囲を想定してパラメータ設定が行われています．

以下では，各パラメータの設定方法を整理します．

#### 4-4-1. Plane rectangular coordinate system

このパラメータは，対象の河道をカバーする平面直角座標系のEPSGコードです．

このプログラムは，デフォルトでは河道中心線に直交するように横断線を設定します．この設定において，地図上の角度の計算に平面直角座標系が利用されます．

EPSGコードは"epsg:6680"のように記載して下さい．

対象の河道をカバーする平面直角座標系のEPSGコードは，以下のURLから調べて下さい．

[https://lemulus.me/column/epsg-list-gis#2011JGD2011](https://lemulus.me/column/epsg-list-gis#2011JGD2011)

#### 4-4-2. Initial point ID, Terminal point ID

これらのパラメータはそれぞれ，[3](#3)で決定した上流端のポイントの識別番号と，下流端のポイントの識別番号です．

[3](#3)でも述べたように，上流端のポイントは，抽出したい範囲から1kmほど上流に設定して下さい．

#### 4-4-3. Flow

このパラメータは，対象の河道の代表地点の平水流量（単位：m3/s）です．

このデータは水深の計算に利用されます．

主要な河川であれば，平水流量のデータは[水文水質データベース](http://www1.river.go.jp/)から得られます．データの取得方法は以下の通りです．

1. 「観測所諸元からの検索」をクリックします
2. 「観測項目」に「水位流量」を，「河川名」に対象の河川を指定し，「検索」をクリックします
3. 観測所の検索リストが表示されますので，対象の河道内の，もしくは，その近辺の観測所を選択します
4. 「流況表検索」をクリックします
5. 「検索開始」をクリックします
6. 観測所の年別平水流量が表示されます

"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"のFlowには，石狩大橋観測所の1973年～2022年の平水流量の中央値が設定されています．

対象の河道の平水流量のデータが入手できない場合には，平水流量と流域面積の比流量を仮定してFlowを設定して下さい．

後に[5](./README.md#5)で述べるように，Flowの設定値は横断面ごとにカスタマイズできます．

#### 4-4-4. tol1-5, adjust1-3

これらのパラメータは横断線の範囲設定に利用されます．

このプログラムは，横断線の範囲設定を右岸側と左岸側に分けて行います．以下の図を用いて，右岸側の横断線の範囲設定の方法を述べます．左岸側の横断線の範囲設定も同様に行われます．

<img src="./assets/images/tol.png" width="400px">

このプログラムは，河道中心線から右岸側に向けて一定間隔で進みながら，現在地点の標高の読み取りを行う作業を繰り返します．以下の3つの条件が全て満たされたとき，標高の読み取りが停止します．

1. 横断面内の最高の標高が，最低の標高よりもtol1(m)以上高い
2. 現在地点の標高が，横断面内の最高の標高よりもtol2(m)以上低い
3. 現在地点の勾配が，tol3以下である

標高読み取りの停止後，横断面内で最高の標高を有する地点が右岸端となります．

以上の横断線の範囲設定方法から確認できるように，tol1-3は対象の河道周辺の地形に応じて設定されることが望ましいです．tol1は河道の平均的な堤防の高さに設定されることが望ましいです．台形型の堤防が存在しない区間においては，tol2は0に設定されることが望ましいです．堤内地の地形の起伏が激しい区間においては，tol3が大きく設定されることが望ましいです．

ただし，このプログラムはtol1-3の値を自動調整するため，tol1-3の設定値が不適切でも，ある程度は対応することが可能です．

tol1-3の自動調整に用いられるのが，tol4-5とadjust1-3です．tol1-3の設定値が不適切だと，標高の読み取りが永久に終わらない可能性があります．そこで，以下の2つの条件のいずれかが満たされたときには，tol1-3の設定値を調整したうえで，標高の読み取りを河道中心線からやり直します．

1. 現在地点が河道中心線からtol4(m)以上離れている
2. 現在地点の標高が，最低の標高よりもtol5(m)以上高い

tol1, tol2, tol3の設定値の調整は，それぞれadjust1, adjust2, adjust3を掛け算することによって行われます．adjust1とadjust2には0より大きく1未満の定数を，adjust3には1よりも大きい定数を指定します．

"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"では，以下の設定値を用いています：tol1 = 8m, tol2 = 2m, tol3 = 0.05, tol4 = 1,000m, tol5 = 30m, adjust1 = 0.9, adjust2 = 0.5, adjust3 = 1.1．

後に[5](./README.md#5)で述べるように，tol1-5の設定値は横断面ごとにカスタマイズできます．

#### 4-4-5. Distance between sections

このパラメータは，河道中心線に沿った，横断面の取得間隔（単位：m）です．

"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"では，200mに設定されています．

#### 4-4-6. Transverse interval

このパラメータは，横断方向の標高取得間隔（単位：m）です．

"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"では，1mに設定されています．

#### 4-4-7. Margin

横断線を設定する際に，河道（右岸端・左岸端）の外側に取るマージンの上限（単位：m）です．

上限値であるため，横断面によっては，この設定値よりも短いマージンしか取られないこともあります．

"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"では，30mに設定されています．

#### 4-4-8. iRIC style

河道縦横断データの出力形式を設定します．

1の場合は，無償の河川シミュレーションソフトウェアである，iRICが読める形式になります．

0の場合は，日立パワーソリューションズが開発した有償の洪水シミュレータである，DioVISTA/Floodが読める形式になります．

"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"では，1に設定されています．

#### 4-4-9. 水深の計算に利用されるパラメータ<a name="4-4-7"></a>

以下の4つのパラメータは，DEMからは取得できない，水面下の地形の平均的な標高を推測するのに利用されます．

- Difference in differential equation
- Roughness coefficient
- Minimum water surface slope
- Number of samples for median calculation

これらのパラメータには，"[code](./code)"に格納されている"[basic_parameters.csv](./code/basic_parameters.csv)"の設定値を用いて下さい．

これらのパラメータの意味については，"[code](./code)"の[README](./code/README.md)を見て下さい．

### 4-5. プログラムの実行<a name="4-5"></a>

"[extract_river_channel_shape.py](./code/extract_river_channel_shape.py)"を実行して下さい．

```
python extract_river_channel_shape.py
```

初回のプログラムの実行時間は非常に長いです．これは，DEMから標高を読み取るコードの遅さによるものです．

プログラムが終了すると，以下のcsvファイルが出力されます．

- intermediate_result.csv: DEMから読み取った標高の生データを横断面ごとに記録したファイル，編集しないで下さい
- setting.csv: 横断面別に平水流量やtol1-5を設定するためのファイル
- oudan.csv, kui.csv: 河道縦横断データ
- elevation.csv: 河床，水面，左岸端，右岸端の標高を縦断方向に記録したファイル

"oudan.csv", "kui.csv"は国土交通省の河川定期縦横断データのフォーマットに従っています．

### 4-6. 河道縦横断データの確認

河道縦横断データの表示には，日立パワーソリューションズが開発した洪水シミュレータである，DioVISTA/Floodを推奨します．

[https://www.hitachi-power-solutions.com/service/digital/diovista/flood/index.html](https://www.hitachi-power-solutions.com/service/digital/diovista/flood/index.html)

このソフトウェアは，読み込んだ河道縦横断データを地図上に表示する機能を有しています．

この地図は地形や堤防の位置を表示しているため，抽出された河道縦横断データの妥当性を容易に確認できます．

このソフトウェアは有償ですが，河道縦横断データの表示機能は，無償のFree Editionでも使用できます．

## 5. 河道縦横断データの調整<a name="5"></a>

[4-5](./README.md#4-5)で抽出された河道縦横断データは，通常，不完全な状態です．

完全な状態にするには，プログラムの出力ファイルである"setting.csv"を用いた調整が必要です．

### 5-1. setting.csvの


### 4-6. 河道縦横断データの確認


