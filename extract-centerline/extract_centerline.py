# -*- coding: utf-8 -*-

import csv
import xml.etree.ElementTree as et
import geopandas as gpd
from shapely.geometry import Point

ksj = "http://nlftp.mlit.go.jp/ksj/schemas/ksj-app"
jps = "http://www.gsi.go.jp/GIS/jpgis/standardSchemas"

with open ("input_extract_centerline.csv", "r") as fin:
    reader = csv.reader(fin)
    data = [row for row in reader]
file_name = data[0][1]
river_code = data[1][1]

tree = et.parse(file_name)
root = tree.getroot()

GM_Points = {}
for GM_Point in root.iter("{"+jps+"}GM_Point"):
    index = GM_Point.get("id")
    for coordinate in GM_Point.iter("DirectPosition.coordinate"):
        coordinate = coordinate.text.split()
        coordinate = (float(coordinate[1]), float(coordinate[0]))
    GM_Points[index] = coordinate

GM_Curves = {}
for GM_Curve in root.iter("{"+jps+"}GM_Curve"):
    index = GM_Curve.get("id")
    coordinates = []
    for GM_PointArray in GM_Curve.iter("GM_PointArray.column"):
        for point in GM_PointArray.iter("GM_PointRef.point"):
            idref = point.get("idref")
            coordinates.append(GM_Points[idref])
        for coordinate in GM_PointArray.iter("DirectPosition.coordinate"):
            coordinate = coordinate.text.split()
            coordinate = (float(coordinate[1]), float(coordinate[0]))
            coordinates.append(coordinate)
    GM_Curves[index] = coordinates

GB03s = {}
for GB03 in root.iter("{"+ksj+"}GB03"):
    index = GB03.get("id")
    POS = GB03.find("{"+ksj+"}POS")
    idref = POS.get("idref")
    GB03s[index] = idref

GB02s = {}
for GB02 in root.iter("{"+ksj+"}GB02"):
    index = GB02.get("id")
    LOC = GB02.find("{"+ksj+"}LOC").get("idref")
    RIC = GB02.find("{"+ksj+"}RIC").text
    SOS = GB02.find("{"+ksj+"}SOS").get("idref")
    EOS = GB02.find("{"+ksj+"}EOS").get("idref")
    SOR = GB02.find("{"+ksj+"}SOR").get("idref")
    EOR = GB02.find("{"+ksj+"}EOR").get("idref")
    GB02s[index] = {"LOC":LOC, "RIC":RIC, "SOS":SOS, "EOS":EOS, "SOR":SOR, "EOR":EOR}

sections = []
for GB02 in GB02s.values():
    if GB02["RIC"] == river_code:
        SOR = GB02["SOR"]
        EOR = GB02["EOR"]
        sections.append({"LOC":GB02["LOC"], "SOS":GB02["SOS"], "EOS":GB02["EOS"]})

# 1. データ内のすべてのSOS（始点）とEOS（終点）を集める
all_sos = set(s["SOS"] for s in sections)
all_eos = set(s["EOS"] for s in sections)
all_nodes = all_sos | all_eos

# 2. SOR（元の開始ノード）が現在のファイルに存在するか確認し、なければ最上流を探す
if SOR in all_nodes:
    point = SOR
else:
    # 他の区間の終点(EOS)になっていない始点(SOS)を最上流ノードとみなす
    start_candidates = all_sos - all_eos
    if start_candidates:
        point = start_candidates.pop() # 見つかった候補をスタートにする
        print(f"SORがファイル内にないため、最上流候補 {point} からスタートします。")
    else:
        # 念のため、全て逆向きでデジタイズされていた場合の考慮
        end_candidates = all_eos - all_sos
        if end_candidates:
            point = end_candidates.pop()
            print(f"SORがファイル内にないため、上流候補 {point} からスタートします。")
        else:
            raise RuntimeError("スタート地点の候補が見つかりません。")

curves = []
visited = set()

# 3. 途切れるまで繋ぎ続ける（無限ループにして、途切れたらbreakで抜ける）
while True:
    # EOR（元の終了ノード）に到達したら終了
    if point == EOR:
        break
        
    next_section = None
    next_point = None
    is_forward = True
    
    for i, section in enumerate(sections):
        if i in visited:
            continue
            
        if section["SOS"] == point:
            next_section = section
            next_point = section["EOS"]
            is_forward = True
            visited.add(i)
            break
        elif section["EOS"] == point:
            next_section = section
            next_point = section["SOS"]
            is_forward = False # 線が逆向き
            visited.add(i)
            break
            
    # 次の接続先が見つからなかったら、終端（県境など）に達したとみなしてループを終了する
    if next_section is None:
        print(f"ノード {point} で川が途切れました。接続を終了します。")
        break
        
    curves.append({
        "LOC": next_section["LOC"], 
        "is_forward": is_forward
    })
    point = next_point

# 4. 座標を一本のラインとして結合する
river = []
river_curve = []
for curve_info in curves:
    curve = curve_info["LOC"]
    is_forward = curve_info["is_forward"]
    
    coordinates = GM_Curves[curve]
    
    if not is_forward:
        coordinates = list(reversed(coordinates))
        
    for coordinate in coordinates:
        if len(river) == 0:
            river.append(coordinate)
            river_curve.append(curve)
        elif river[-1] != coordinate:
            river.append(coordinate)
            river_curve.append(curve)

# ==========================================
# GeoPackage (GPKG) 出力部分
# ==========================================

# 1. ShapelyのPointオブジェクトのリストを作成
geometry = [Point(lon, lat) for lon, lat in river]

# 2. 属性データ（curveのみ）とジオメトリを持つGeoDataFrameを作成
# crs="EPSG:4326" でWGS84（元の.prjファイルと同等）を指定
gdf = gpd.GeoDataFrame(
    {'curve': river_curve}, 
    geometry=geometry, 
    crs="EPSG:4326"
)

# 3. GeoPackageとして保存
# engine="pyogrio" を指定すると、大規模データでも非常に高速に書き出し可能
gdf.to_file("river_centerline.gpkg", driver="GPKG", engine="pyogrio")
