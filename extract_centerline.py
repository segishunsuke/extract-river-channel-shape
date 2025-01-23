# -*- coding: utf-8 -*-

import csv
import xml.etree.ElementTree as et
import shapefile

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

point = SOR
curves = []
while point != EOR:
    for section in sections:
        if section["SOS"] == point:
            curves.append(section["LOC"])
            point = section["EOS"]
            break

river = []
river_curve = []
for curve in curves:
    coordinates = GM_Curves[curve]
    for coordinate in coordinates:
        if len(river) == 0:
            river.append(coordinate)
            river_curve.append(curve)
        elif river[-1] != coordinate:
            river.append(coordinate)
            river_curve.append(curve)

w = shapefile.Writer("river")
w.shapeType = shapefile.POLYLINE
w.field('id', 'N')
w.line([river])
w.record(0)
w.close()

fout = open ('river.prj', 'w')
fout.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
fout.close()

w = shapefile.Writer("river points")
w.shapeType = shapefile.POINT
w.field('id', 'N')
w.field('curve', 'C', size=16)
for i in range(len(river)):
    w.point(river[i][0], river[i][1])
    w.record(i, river_curve[i])
w.close()

fout = open ('river points.prj', 'w')
fout.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
fout.close()