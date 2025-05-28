# -*- coding: utf-8 -*-

import xml.etree.ElementTree as et
import numpy as np
import glob

gml = "http://www.opengis.net/gml/3.2"

"""
指定された第3次地域区画メッシュのxmlファイルのデータを読み込み，行列形式で返す関数
I: 経度の第1次，第2次，第3次地域区画座標の配列
J: 緯度の第1次，第2次，第3次地域区画座標の配列
"""
def read_elevation(I, J, dem_type = "A"):
    coordinates_id = "{:02}".format(str(J[0]))+"{:02}".format(str(I[0]))+"-"+str(J[1])+str(I[1])+"-"+str(J[2])+str(I[2])
    
    """
    dem_type = "A"ならDEM5A→5B→5Cの順番で読み込みを試みる，
    dem_type = "B"ならDEM5B→5Cの順番で読み込みを試みる，
    dem_type = "C"ならDEM5Cの読み込みを試みる，
    失敗した場合は標高データ無し（-9999）として行列を返す
    """
    if dem_type == "A":
        file_name = glob.glob("./elevation/FG-GML-"+coordinates_id+"-DEM5A-*.xml")
        if len(file_name) == 0:
            print('DEM5A of ID: '+coordinates_id+' is unavailable.')
            file_name = glob.glob("./elevation/FG-GML-"+coordinates_id+"-DEM5B-*.xml")
            if len(file_name) == 0:
                print('DEM5B of ID: '+coordinates_id+' is unavailable.')
                file_name = glob.glob("./elevation/FG-GML-"+coordinates_id+"-DEM5C-*.xml")
                if len(file_name) == 0:
                    print('xml file of ID: '+coordinates_id+' is missing.')
                    elevation = -9999.0 * np.ones((225, 150))
                    return elevation
    elif dem_type == "B":
        file_name = glob.glob("./elevation/FG-GML-"+coordinates_id+"-DEM5B-*.xml")
        if len(file_name) == 0:
            print('DEM5B of ID: '+coordinates_id+' is unavailable.')
            file_name = glob.glob("./elevation/FG-GML-"+coordinates_id+"-DEM5C-*.xml")
            if len(file_name) == 0:
                print('xml file of ID: '+coordinates_id+' is missing.')
                elevation = -9999.0 * np.ones((225, 150))
                return elevation
    else:
        file_name = glob.glob("./elevation/FG-GML-"+coordinates_id+"-DEM5C-*.xml")
        if len(file_name) == 0:
            print('xml file of ID: '+coordinates_id+' is missing.')
            elevation = -9999.0 * np.ones((225, 150))
            return elevation
    file_name = file_name[0]
    
    tree = et.parse(file_name)
    root = tree.getroot()
    
    for startPoint in root.iter("{"+gml+"}startPoint"):
        startPoint = startPoint.text.split()
        startPoint = int(startPoint[0]) + int(startPoint[1]) * 225
    
    elevation = -9999.0 * np.ones(150 * 225)
    i = startPoint
    
    for tupleLists in root.iter("{"+gml+"}tupleList"):
        tupleLists = tupleLists.text.split("\n")
        for tupleList in tupleLists:
            tupleList = tupleList.split(",")
            if len(tupleList) == 2:
                elevation[i] = float(tupleList[1])
                i += 1
    
    elevation = elevation.reshape(150, 225).T
    for i in range(225):
        elevation[i,:] = elevation[i,::-1]
    
    return elevation

"""
与えられた座標の高度を求める関数
一度読み込んだxmlファイルのデータはIJ_elevationsリストに格納しておき，read_elevation関数の使用回数を減らしてある
"""
IJ_elevations = [] # get_elevation関数が使用するリスト
def get_elevation(lon, lat, dem_type = "A"):
    x = (lon - 100.0) * 18000.0
    i = int(x)
    modx = x - i
    
    if modx < 0.5:
        i_l = i - 1
        i_u = i
        modx += 0.5
    else:
        i_l = i
        i_u = i + 1
        modx -= 0.5
    
    # I_l, I_u, J_l, J_u は，それぞれ x・y 方向のXML分割インデックス（4階層）を表す
    
    I_l = np.zeros(4, dtype = int)
    I_l[0] = i_l // 18000
    i_l -= I_l[0] * 18000
    I_l[1] = i_l // 2250
    i_l -= I_l[1] * 2250
    I_l[2] = i_l // 225
    i_l -= I_l[2] * 225
    I_l[3] = i_l
    
    I_u = np.zeros(4, dtype = int)
    I_u[0] = i_u // 18000
    i_u -= I_u[0] * 18000
    I_u[1] = i_u // 2250
    i_u -= I_u[1] * 2250
    I_u[2] = i_u // 225
    i_u -= I_u[2] * 225
    I_u[3] = i_u
    
    y = lat * 1.5 * 12000.0
    j = int(y)
    mody = y - j
    
    if mody < 0.5:
        j_l = j - 1
        j_u = j
        mody += 0.5
    else:
        j_l = j
        j_u = j + 1
        mody -= 0.5
    
    J_l = np.zeros(4, dtype = int)
    J_l[0] = j_l // 12000
    j_l -= J_l[0] * 12000
    J_l[1] = j_l // 1500
    j_l -= J_l[1] * 1500
    J_l[2] = j_l // 150
    j_l -= J_l[2] * 150
    J_l[3] = j_l
    
    J_u = np.zeros(4, dtype = int)
    J_u[0] = j_u // 12000
    j_u -= J_u[0] * 12000
    J_u[1] = j_u // 1500
    j_u -= J_u[1] * 1500
    J_u[2] = j_u // 150
    j_u -= J_u[2] * 150
    J_u[3] = j_u
    
    I_l = tuple(I_l.tolist())
    J_l = tuple(J_l.tolist())
    I_u = tuple(I_u.tolist())
    J_u = tuple(J_u.tolist())
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_l[:3] and IJ_elevation[1][:3] == J_l[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_l, J_l, dem_type)
        IJ_elevations.append((I_l[:3], J_l[:3], elevation))
    else:
        elevation = IJ_elevation[2]
    elevation_ll = elevation[I_l[3], J_l[3]]
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_l[:3] and IJ_elevation[1][:3] == J_u[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_l, J_u, dem_type)
        IJ_elevations.append((I_l[:3], J_u[:3], elevation))
    else:
        elevation = IJ_elevation[2]
    elevation_lu = elevation[I_l[3], J_u[3]]
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_u[:3] and IJ_elevation[1][:3] == J_l[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_u, J_l, dem_type)
        IJ_elevations.append((I_u[:3], J_l[:3], elevation))
    else:
        elevation = IJ_elevation[2]
    elevation_ul = elevation[I_u[3], J_l[3]]
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_u[:3] and IJ_elevation[1][:3] == J_u[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_u, J_u, dem_type)
        IJ_elevations.append((I_u[:3], J_u[:3], elevation))
    else:
        elevation = IJ_elevation[2]
    elevation_uu = elevation[I_u[3], J_u[3]]
    
    """
    メモリ節約のため，elevationデータの保存数は最大でxmlファイル16個分とする
    """
    while len(IJ_elevations) > 16:
        del IJ_elevations[0]
    
    if elevation_ll != -9999.0 and elevation_lu != -9999.0 and elevation_ul != -9999.0 and elevation_uu != -9999.0:
        return elevation_ll * (1.0 - modx) * (1.0 - mody) + elevation_lu * (1.0 - modx) * mody \
            + elevation_ul * modx * (1.0 - mody) + elevation_uu * modx * mody
    else:
        if modx < 0.5 and mody < 0.5:
            return elevation_ll
        elif modx < 0.5 and mody >= 0.5:
            return elevation_lu
        elif modx >= 0.5 and mody < 0.5:
            return elevation_ul
        else:
            return elevation_uu
