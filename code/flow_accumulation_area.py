# -*- coding: utf-8 -*-

import numpy as np
import rasterio
"""
指定された経度（整数リスト）・緯度（整数リスト）のtifファイルのデータを読み込み，行列形式で返す関数
I: 経度のリスト
J: 緯度のリスト
"""
def read_area(I, J):
    tile_name = f"./upa/n{J[0]:02d}e{I[0]:03d}_upa.tif"
    with rasterio.open(tile_name) as dataset:
        area = dataset.read(1).T[:, ::-1]
    return area

"""
与えられた座標の近傍の集水面積の中で最大のものを求める関数
一度読み込んだtifファイルのデータはIJ_areasリストに格納しておき，read_area関数の使用回数を減らしてある
"""
IJ_areas = [] # get_area関数が使用するリスト
def get_area(lon, lat):
    x = lon * 3600.0
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
    
    # I_l, I_u, J_l, J_u は，それぞれ x・y 方向のtif分割インデックス（4階層）を表す
    
    I_l = np.zeros(2, dtype = int)
    I_l[0] = i_l // 3600
    i_l -= I_l[0] * 3600
    I_l[1] = i_l
    
    I_u = np.zeros(2, dtype = int)
    I_u[0] = i_u // 3600
    i_u -= I_u[0] * 3600
    I_u[1] = i_u
    
    y = lat * 3600.0
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
    
    J_l = np.zeros(2, dtype = int)
    J_l[0] = j_l // 3600
    j_l -= J_l[0] * 3600
    J_l[1] = j_l
    
    J_u = np.zeros(2, dtype = int)
    J_u[0] = j_u // 3600
    j_u -= J_u[0] * 3600
    J_u[1] = j_u
    
    I_l = tuple(I_l.tolist())
    J_l = tuple(J_l.tolist())
    I_u = tuple(I_u.tolist())
    J_u = tuple(J_u.tolist())
    
    IJ_area = next(filter(lambda IJ_area: IJ_area[0][:1] == I_l[:1] and IJ_area[1][:1] == J_l[:1], IJ_areas), None)
    if IJ_area is None:
        area = read_area(I_l, J_l)
        IJ_areas.append((I_l[:1], J_l[:1], area))
    else:
        area = IJ_area[2]
    area_ll = area[I_l[1], J_l[1]]
    
    IJ_area = next(filter(lambda IJ_area: IJ_area[0][:1] == I_l[:1] and IJ_area[1][:1] == J_u[:1], IJ_areas), None)
    if IJ_area is None:
        area = read_area(I_l, J_u)
        IJ_areas.append((I_l[:1], J_u[:1], area))
    else:
        area = IJ_area[2]
    area_lu = area[I_l[1], J_u[1]]
    
    IJ_area = next(filter(lambda IJ_area: IJ_area[0][:1] == I_u[:1] and IJ_area[1][:1] == J_l[:1], IJ_areas), None)
    if IJ_area is None:
        area = read_area(I_u, J_l)
        IJ_areas.append((I_u[:1], J_l[:1], area))
    else:
        area = IJ_area[2]
    area_ul = area[I_u[1], J_l[1]]
    
    IJ_area = next(filter(lambda IJ_area: IJ_area[0][:1] == I_u[:1] and IJ_area[1][:1] == J_u[:1], IJ_areas), None)
    if IJ_area is None:
        area = read_area(I_u, J_u)
        IJ_areas.append((I_u[:1], J_u[:1], area))
    else:
        area = IJ_area[2]
    area_uu = area[I_u[1], J_u[1]]
    
    """
    メモリ節約のため，areaデータの保存数は最大でtifファイル4個分とする
    """
    while len(IJ_areas) > 4:
        del IJ_areas[0]
    
    return max(area_ll, area_lu, area_ul, area_uu)
