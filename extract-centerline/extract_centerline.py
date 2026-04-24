# -*- coding: utf-8 -*-

import csv
import xml.etree.ElementTree as et
import geopandas as gpd
from shapely.geometry import Point
from collections import defaultdict

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

# 1. 双方向グラフの構築（矢印の向きを無視して全区間を繋ぐ）
adj = defaultdict(list)
for sec in sections:
    sos = sec["SOS"]
    eos = sec["EOS"]
    loc = sec["LOC"]
    # 順方向（SOS -> EOS）
    adj[sos].append({"loc": loc, "next_node": eos, "is_forward": True})
    # 逆方向（EOS -> SOS）として辿れる道も作っておく
    adj[eos].append({"loc": loc, "next_node": sos, "is_forward": False})

# 2. スタート地点の決定
all_nodes = set(adj.keys())
if SOR in all_nodes:
    start_point = SOR
else:
    # 接続先が1つしかない端点（源流 または 河口）を探す
    endpoints = [node for node, edges in adj.items() if len(edges) == 1]
    if not endpoints:
        raise RuntimeError("端点が見つかりません。")
    # IDが若い方（上流）をスタート地点に採用
    start_point = sorted(endpoints)[0]
    print(f"SORが見つからないため、端点候補 {start_point} から抽出を開始します。")

# 3. トラバース（中州を回避しつつ一本道を描く）
point = start_point
visited_locs = set()
visited_nodes = {start_point}
curves = []

while True:
    next_edge = None
    
    # 優先：未訪問の「ノード」へ向かう道（ループを防止）
    for edge in adj[point]:
        if edge["loc"] not in visited_locs and edge["next_node"] not in visited_nodes:
            next_edge = edge
            break
            
    # 予備：未訪問ノードへの道がなければ、仕方なく未訪問の「道」を選ぶ
    if next_edge is None:
        for edge in adj[point]:
            if edge["loc"] not in visited_locs:
                next_edge = edge
                break

    if next_edge is None:
        print(f"ノード {point} で抽出が終了しました（全 {len(curves)} 区間）。")
        break
        
    loc = next_edge["loc"]
    curves.append({"loc": loc, "is_forward": next_edge["is_forward"]})
    visited_locs.add(loc)
    point = next_edge["next_node"]
    visited_nodes.add(point)

# 4. 座標の結合（逆走した区間は座標を反転させる）
river = []
river_curve = []
for curve_info in curves:
    curve = curve_info["loc"]
    is_forward = curve_info["is_forward"]
    
    coordinates = GM_Curves[curve]
    # 逆向きに繋いだ場合は、ジオメトリが連続するように座標順序をリバースする
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
# crs="EPSG:4326" でWGS84を指定
gdf = gpd.GeoDataFrame(
    {'curve': river_curve}, 
    geometry=geometry, 
    crs="EPSG:4326"
)

# 3. GeoPackageとして保存
# engine="pyogrio" を指定すると、大規模データでも非常に高速に書き出し可能
gdf.to_file("river_centerline.gpkg", driver="GPKG", engine="pyogrio")
