# -*- coding: utf-8 -*-

import xml.etree.ElementTree as et
import numpy as np
import glob

gml = "http://www.opengis.net/gml/3.2"

n_row = 225 * 5
n_col = 150 * 5

"""
指定された第3次地域区画メッシュのxmlファイルのデータを読み込み，行列形式で返す関数
I: 経度の第1次，第2次，第3次地域区画座標の配列
J: 緯度の第1次，第2次，第3次地域区画座標の配列
"""
def read_elevation(I, J):
    coordinates_id = "{:02}".format(str(J[0]))+"{:02}".format(str(I[0]))+"-"+str(J[1])+str(I[1])+"-"+str(J[2])+str(I[2])
    
    file_name = glob.glob("./elevation/FG-GML-"+coordinates_id+"-DEM1A-*.xml")
    if len(file_name) == 0:
        print('DEM1A of ID: '+coordinates_id+' is unavailable.')
        elevation = -9999.0 * np.ones((n_row, n_col))
        return elevation
    file_name = file_name[0]
    
    tree = et.parse(file_name)
    root = tree.getroot()
    
    for startPoint in root.iter("{"+gml+"}startPoint"):
        startPoint = startPoint.text.split()
        startPoint = int(startPoint[0]) + int(startPoint[1]) * n_row
    
    elevation = -9999.0 * np.ones(n_col * n_row)
    i = startPoint
    
    for tupleLists in root.iter("{"+gml+"}tupleList"):
        tupleLists = tupleLists.text.split("\n")
        for tupleList in tupleLists:
            tupleList = tupleList.split(",")
            if len(tupleList) == 2:
                elevation[i] = float(tupleList[1])
                i += 1
    
    elevation = elevation.reshape(n_col, n_row).T
    for i in range(n_row):
        elevation[i,:] = elevation[i,::-1]
    
    return elevation

"""
与えられた座標の高度を求める関数
一度読み込んだxmlファイルのデータはIJ_elevationsリストに格納しておき，read_elevation関数の使用回数を減らしてある
"""
IJ_elevations = [] # get_elevation関数が使用するリスト
def get_elevation(lon, lat):
    x = (lon - 100.0) * (n_row * 80.0)
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
    I_l[0] = i_l // (n_row * 80)
    i_l -= I_l[0] * (n_row * 80)
    I_l[1] = i_l // (n_row * 10)
    i_l -= I_l[1] * (n_row * 10)
    I_l[2] = i_l // n_row
    i_l -= I_l[2] * n_row
    I_l[3] = i_l
    
    I_u = np.zeros(4, dtype = int)
    I_u[0] = i_u // (n_row * 80)
    i_u -= I_u[0] * (n_row * 80)
    I_u[1] = i_u // (n_row * 10)
    i_u -= I_u[1] * (n_row * 10)
    I_u[2] = i_u // n_row
    i_u -= I_u[2] * n_row
    I_u[3] = i_u
    
    y = lat * 1.5 * (n_col * 80.0)
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
    J_l[0] = j_l // (n_col * 80)
    j_l -= J_l[0] * (n_col * 80)
    J_l[1] = j_l // (n_col * 10)
    j_l -= J_l[1] * (n_col * 10)
    J_l[2] = j_l // n_col
    j_l -= J_l[2] * n_col
    J_l[3] = j_l
    
    J_u = np.zeros(4, dtype = int)
    J_u[0] = j_u // (n_col * 80)
    j_u -= J_u[0] * (n_col * 80)
    J_u[1] = j_u // (n_col * 10)
    j_u -= J_u[1] * (n_col * 10)
    J_u[2] = j_u // n_col
    j_u -= J_u[2] * n_col
    J_u[3] = j_u
    
    I_l = tuple(I_l.tolist())
    J_l = tuple(J_l.tolist())
    I_u = tuple(I_u.tolist())
    J_u = tuple(J_u.tolist())
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_l[:3] and IJ_elevation[1][:3] == J_l[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_l, J_l)
        IJ_elevations.append((I_l[:3], J_l[:3], elevation))
    else:
        elevation = IJ_elevation[2]
    elevation_ll = elevation[I_l[3], J_l[3]]
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_l[:3] and IJ_elevation[1][:3] == J_u[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_l, J_u)
        IJ_elevations.append((I_l[:3], J_u[:3], elevation))
    else:
        elevation = IJ_elevation[2]
    elevation_lu = elevation[I_l[3], J_u[3]]
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_u[:3] and IJ_elevation[1][:3] == J_l[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_u, J_l)
        IJ_elevations.append((I_u[:3], J_l[:3], elevation))
    else:
        elevation = IJ_elevation[2]
    elevation_ul = elevation[I_u[3], J_l[3]]
    
    IJ_elevation = next(filter(lambda IJ_elevation: IJ_elevation[0][:3] == I_u[:3] and IJ_elevation[1][:3] == J_u[:3], IJ_elevations), None)
    if IJ_elevation is None:
        elevation = read_elevation(I_u, J_u)
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
