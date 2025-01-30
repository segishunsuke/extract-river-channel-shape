# -*- coding: utf-8 -*-

import os
import numpy as np
import csv
import shapefile
import pyproj
import dem
import open_channel

with open ("basic_parameters.csv", "r") as fin:
    reader = csv.reader(fin)
    data = [row for row in reader]

plane_rectangular_coordinate_system = data[0][1] # 対象の河川を含む平面直角座標系を指定
id_begin = int(data[1][1]) # 河道のポイントデータの何番目から始めるか
id_end = int(data[2][1]) # 河道のポイントデータの何番目で終えるか，id_endを含む
flow = float(data[3][1]) # 平水時の流量[m3/s]
tol1 = float(data[4][1]) # 最低点からtol1メートル以上でなければ堤防の頂点と見なさない
tol2 = float(data[5][1]) # 頂点からtol2メートル落ちたら堤防が終わったと見なす
tol3 = float(data[6][1]) # 頂点からtol2メートル落ちた後に，勾配がtol3以下になったら終了
tol4 = float(data[7][1]) # 頂点が川の端からtol4メートル以上離れている場合はtol1とtol2が高すぎるので調整してやり直し
tol5 = float(data[8][1]) # 頂点と最低点の差がtol5メートル以上の場合はtol1とtol2が高すぎるので調整してやり直し
# tol3の基準を満たす点を探している間に再び頂点が更新された場合はtol2の基準からやり直し
adjust1 = float(data[9][1])  # tol1を何倍に調整するか
adjust2 = float(data[10][1])  # tol2を何倍に調整するか
adjust3 = float(data[11][1]) # tol3を何倍に調整するか
distance_between_sections = float(data[12][1]) # 断面取得間隔[m]
transverse_interval = float(data[13][1]) # 横断面のポイント間隔[m]
margin = float(data[14][1]) # 横断線の設定に当たり，左岸端・右岸端の外側に何メートルのマージンを設けるか
iric_format = int(data[15][1]) # iRICで読み取れる形式で出力するか
difference_in_differential_equation = float(data[16][1]) # 不等流計算の差分間隔[m]
roughness = float(data[17][1]) # 粗度係数
minimum_slope_water = float(data[18][1]) # 水面勾配の最小値
n_samples_for_median = int(data[19][1]) # 中央値を計算する際のサンプル数
if n_samples_for_median % 2 == 0:
    raise ValueError("n_samples_for_averagingには奇数を指定して下さい")

"""
河川の中心線の座標データの読み取り
"""
sf = shapefile.Reader("river_centerline")
shapes = sf.shapes()
points = np.zeros((id_end+1-id_begin,2)) # 河川の中心線を構成する点の座標の配列，points[i,0]はi番の点の経度，points[i,1]はi番の点の緯度，点は下流から上流に向けて並ぶ
for i in range(len(points)):
    points[i,0], points[i,1] = shapes[id_end-i].points[0]
sf.close()

"""
座標データの緯度経度からメートルへの変換
"""
transformer_to_meter = pyproj.Transformer.from_crs("epsg:4326", plane_rectangular_coordinate_system, always_xy = True) # 緯度経度には必ず世界測地系を使うらしい
transformer_to_degree = pyproj.Transformer.from_crs(plane_rectangular_coordinate_system, "epsg:4326", always_xy = True)

points_meter = np.zeros_like(points) # 河川の中心線を構成する点の座標（メートル）の配列
for i in range(len(points)):
    points_meter[i,0], points_meter[i,1] = transformer_to_meter.transform(points[i,0], points[i,1])

def get_distance_between_points_and_vectors(i): # 河川の中心線を構成するi番目の点とi+1番目の点の間の距離（dist），i+1番目からi番目の点に向かう単位ベクトル(j_vector)，それに垂直な右岸側を向く単位ベクトル（v_vector）を求める関数，単位ベクトルは緯度経度表示に変換してある
    j_vector_meter = points_meter[i+1,:] - points_meter[i,:]
    dist = np.sqrt( np.dot(j_vector_meter, j_vector_meter) )
    j_vector_meter /= dist
    v_vector_meter = np.array([-j_vector_meter[1], j_vector_meter[0]])
    
    j_vector = np.zeros(2)
    j_vector[0], j_vector[1] = transformer_to_degree.transform(points_meter[i,0] + j_vector_meter[0], points_meter[i,1] + j_vector_meter[1])
    j_vector -= points[i,:]
    
    v_vector = np.zeros(2)
    v_vector[0], v_vector[1] = transformer_to_degree.transform(points_meter[i,0] + v_vector_meter[0], points_meter[i,1] + v_vector_meter[1])
    v_vector -= points[i,:]
    
    return dist, j_vector, v_vector

def rotate_vector(vector, center, theta): # 与えられた度表示のベクトルを反時計周りにthetaラジアン回転する 
    center_meter = np.zeros(2)
    center_meter[0], center_meter[1] = transformer_to_meter.transform(center[0], center[1])
    
    vector_meter = np.zeros(2)
    vector_meter[0], vector_meter[1] = transformer_to_meter.transform(center[0] + vector[0], center[1] + vector[1])
    vector_meter -= center_meter[:]
    
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    vector_meter_rotated = np.zeros(2)
    vector_meter_rotated[0] = cos_theta * vector_meter[0] - sin_theta * vector_meter[1]
    vector_meter_rotated[1] = sin_theta * vector_meter[0] + cos_theta * vector_meter[1]
    
    vector_rotated = np.zeros(2)
    vector_rotated[0], vector_rotated[1] = transformer_to_degree.transform(center_meter[0] + vector_meter_rotated[0], center_meter[1] + vector_meter_rotated[1])
    vector_rotated -= center[:]
    
    return vector_rotated
    
dist_between_points = np.zeros(len(points) - 1)
j_vector = np.zeros((len(points) - 1, 2))
v_vector = np.zeros((len(points) - 1, 2))
for i in range(len(points) - 1): # dist, j_vector, v_vectorを点i = 0から点i = len(points) - 1まで求めて配列に保存
    dist_between_points[i], j_vector[i], v_vector[i] = get_distance_between_points_and_vectors(i)

distance_accumulated = np.zeros(len(points))
for i in range(len(points)):
    distance_accumulated[i] = np.sum(dist_between_points[0:i]) # 点0から点iまでの累積距離

n_sections = int(distance_accumulated[-1] / distance_between_sections) # 横断面の数

stakes_right = np.zeros((n_sections, 3)) # stakes_right[i_section,0]は横断面i_sectionの右岸側の杭のx座標，stakes_right[i_section,1]は横断面i_sectionの右岸側の杭のy座標，stakes_right[i_section,2]は横断面i_sectionの右岸側の杭の標高
stakes_left = np.zeros((n_sections, 3)) # stakes_left[i_section,0]は横断面i_sectionの左岸側の杭のx座標，stakes_left[i_section,1]は横断面i_sectionの左岸側の杭のy座標，stakes_left[i_section,2]は横断面i_sectionの左岸側の杭の標高
js_stake_right = np.zeros(n_sections, dtype = int) # js_stake_right[i_section]は横断面i_sectionの右岸側の杭のj座標（後述）
js_stake_left = np.zeros(n_sections, dtype = int) # js_stake_left[i_section]は横断面i_sectionの左岸側の杭のj座標（後述）
js_center = np.zeros(n_sections, dtype = int) # js_stake_left[i_section]は横断面i_sectionの中心線上の点のj座標（後述）

sections_topography = [] # 横断面の標高データのリスト
for i_section in range(n_sections):
    sections_topography.append(None)

use_intermediate_result = np.zeros(n_sections, dtype=int) # use_intermediate_result[i_section] = 1は"intermediate_result.csv"のデータを使用

tol1s = np.ones((n_sections, 2)) * tol1 # i_sectionごとのtol1，tol1s[i_section,0]は左岸，tol1s[i_section,1]は右岸，以下同様
tol2s = np.ones((n_sections, 2)) * tol2
tol3s = np.ones((n_sections, 2)) * tol3
tol4s = np.ones((n_sections, 2)) * tol4
tol5s = np.ones((n_sections, 2)) * tol5
angle_adjusts = np.zeros(n_sections)
flows = np.ones(n_sections) * flow

dem_types = []
for i_section in range(n_sections):
    dem_types.append(["A", "A"])

"""
前回の途中経過があればそれを利用
"""
try:
    with open ("setting.csv", "r") as fin:
        reader = csv.reader(fin)
        data = [row for row in reader]
    
    for i_section in range(len(data)-1):
        use_intermediate_result[i_section] = int(data[1+i_section][1])
        flows[i_section] = float(data[1+i_section][2])
        angle_adjusts[i_section] = float(data[1+i_section][3]) * np.pi / 180.0
        tol1s[i_section,0] = float(data[1+i_section][4])
        tol2s[i_section,0] = float(data[1+i_section][5])
        tol3s[i_section,0] = float(data[1+i_section][6])
        tol4s[i_section,0] = float(data[1+i_section][7])
        tol5s[i_section,0] = float(data[1+i_section][8])
        dem_types[i_section][0] = data[1+i_section][9]
        tol1s[i_section,1] = float(data[1+i_section][10])
        tol2s[i_section,1] = float(data[1+i_section][11])
        tol3s[i_section,1] = float(data[1+i_section][12])
        tol4s[i_section,1] = float(data[1+i_section][13])
        tol5s[i_section,1] = float(data[1+i_section][14])
        dem_types[i_section][1] = data[1+i_section][15]
    
    with open ("intermediate_result.csv", "r") as fin:
        reader = csv.reader(fin)
        data = [row for row in reader]
    
    for i_section in range(n_sections):
        if use_intermediate_result[i_section]:
            stakes_right[i_section,0] = float(data[i_section][0])
            stakes_right[i_section,1] = float(data[i_section][1])
            stakes_right[i_section,2] = float(data[i_section][2])
            stakes_left[i_section,0] = float(data[i_section][3])
            stakes_left[i_section,1] = float(data[i_section][4])
            stakes_left[i_section,2] = float(data[i_section][5])
            js_stake_right[i_section] = int(data[i_section][6])
            js_stake_left[i_section] = int(data[i_section][7])
            js_center[i_section] = int(data[i_section][8])
            dim_section_topography = int(data[i_section][9])
            section_topography = np.zeros(dim_section_topography)
            for j in range(dim_section_topography):
                section_topography[j] = float(data[i_section][10+j])
            sections_topography[i_section] = section_topography

except FileNotFoundError:
    pass


"""
下流（i_section = 0）から上流に向けて横断面の標高データを生成していく
"""
print("横断面の標高データを読み取ります")
for i_section in range(n_sections):
    print(str(i_section)+" / "+str(n_sections))
    
    if use_intermediate_result[i_section] != 1:
        distance_section = distance_between_sections * i_section # 中心線を一定距離上るごとに横断面データを作成
        for i in range(len(points) - 1):
            if distance_accumulated[i+1] >= distance_section:
                break
        center = points[i,:] + (distance_section - distance_accumulated[i]) * j_vector[i] # 中心線上の点の緯度経度座標
        
        if angle_adjusts[i_section] == 0.0:
            direction_transverse = v_vector[i] # direction_transverseは右岸側を向く単位ベクトル
        else:
            direction_transverse = rotate_vector(v_vector[i], center, angle_adjusts[i_section])
        
        """
        右岸側の断面データの読み取り
        """
        if use_intermediate_result[i_section] == 0:
            section_topography_right = np.array([]) # 右岸側の標高データの配列
        else:
            section_topography_right = sections_topography[i_section][js_center[i_section]:]
        
        j = 0 # 中心線上の点がj = 0，そこから右岸側にtransverse_intervalメートル進むごとに+1，左岸側にtransverse_intervalメートル進むごとに-1される整数座標
        top = -9999.0 # 右岸側で発見された中で最高の標高（初期値は-9999.0）
        bottom = -9999.0 # 右岸側で発見された中で最低の標高（初期値は-9999.0）
        elevation_previous = -9999.0 # 一つ前の点の標高（初期値は-9999.0）
        
        while True: # 右岸側の横断面データが完成するまで繰り返す
            current = center + j * transverse_interval * direction_transverse # 点jに対応した緯度経度座標
            
            if section_topography_right.size == j:
                elevation = dem.get_elevation(current[0], current[1], dem_types[i_section][1]) # 点jの標高を取得
                section_topography_right = np.append(section_topography_right, elevation) # section_topography_rightに標高データを追加
            else:
                elevation = section_topography_right[j] # 標高データを読み取り済みの場合
            
            if elevation != -9999.0: # 標高データが正常値の場合（水面は-9999.0）
                if bottom == -9999.0: # bottomが初期値の場合はその標高データをbottomに代入
                    bottom = elevation
                elif bottom > elevation: # そうでない場合はその標高データが現在のbottomより低い場合にbottomを更新
                    bottom = elevation
                
                if elevation >= top: # 標高データが最高値を更新したら暫定の頂点データとして記録
                    top = elevation # 最高の標高
                    stakes_right[i_section,0:2] = current # 杭の座標
                    stakes_right[i_section,2] = top # 杭の標高
                    j_stake_right = j # 杭のj
                
                if top >= bottom + tol1s[i_section,1] and elevation <= top - tol2s[i_section,1] and abs(elevation - elevation_previous) <= tol3s[i_section,1] * transverse_interval: # tol1, tol2, tol3の条件が満たされたら記録終了
                    break
            
            if abs(j) * transverse_interval >= tol4s[i_section,1] or (bottom != -9999.0 and elevation - bottom >= tol5s[i_section,1]): # tol4やtol5の基準から見て問題がある場合にはscale1とscale2を調整してwhileループを最初からやり直し
                tol1s[i_section,1] *= adjust1
                tol2s[i_section,1] = max(tol2s[i_section,1] * adjust2 - 0.1, 0.0)
                tol3s[i_section,1] *= adjust3
                if tol3s[i_section,1] >= 100.0:
                    raise ValueError("座標("+str(center[1])+"N, "+str(center[0])+"E)の右岸側の地形データが存在しません")
                j = 0
                top = -9999.0
                bottom = -9999.0
                elevation_previous = -9999.0
            else:
                elevation_previous = elevation # 一つ前の点の標高を更新（勾配の計算に使用）
                j += 1
        
        """
        左岸側の断面データの読み取り（方法は右岸側と同様）
        """
        if use_intermediate_result[i_section] == 0:
            section_topography_left = np.array([])
        else:
            section_topography_left = sections_topography[i_section][:js_center[i_section]]
            section_topography_left[:] = section_topography_left[::-1]
        
        j = -1 # j = -1からスタート
        top = -9999.0
        bottom = -9999.0
        elevation_previous = -9999.0
        
        while True:
            current = center + j * transverse_interval * direction_transverse
            
            if section_topography_left.size == -j-1:
                elevation = dem.get_elevation(current[0], current[1], dem_types[i_section][0])
                section_topography_left = np.append(section_topography_left, elevation)
            else:
                elevation = section_topography_left[-j-1]
            
            if elevation != -9999.0:
                if bottom == -9999.0:
                    bottom = elevation
                elif bottom > elevation:
                    bottom = elevation
                
                if elevation >= top:
                    top = elevation
                    stakes_left[i_section,0:2] = current
                    stakes_left[i_section,2] = top
                    j_stake_left = j
                
                if top >= bottom + tol1s[i_section,0] and elevation <= top - tol2s[i_section,0] and abs(elevation - elevation_previous) <= tol3s[i_section,0] * transverse_interval: # tol1, tol2, tol3の条件が満たされたら記録終了
                    break
            
            if abs(j) * transverse_interval >= tol4s[i_section,0] or (bottom != -9999.0 and elevation - bottom >= tol5s[i_section,0]):
                tol1s[i_section,0] *= adjust1
                tol2s[i_section,0] = max(tol2s[i_section,0] * adjust2 - 0.1, 0.0)
                tol3s[i_section,0] *= adjust3
                if tol3s[i_section,0] >= 100.0:
                    raise ValueError("座標("+str(center[1])+"N, "+str(center[0])+"E)の左岸側の地形データが存在しません")
                j = -1
                top = -9999.0
                bottom = -9999.0
                elevation_previous = -9999.0
            else:
                elevation_previous = elevation
                j -= 1
        
        section_topography_left[:] = section_topography_left[::-1] # section_topography_leftの標高データの配列はj = -1, j = -2, j = -3, ...と逆順に並んでいるため反転させる
        
        section_topography = np.append(section_topography_left, section_topography_right) # 左岸側・右岸側のデータの結合
        j_stake_right = j_stake_right + len(section_topography_left) # 右岸側の杭のj座標の修正（左岸側の左端の点をj = 0とする）
        j_stake_left = j_stake_left + len(section_topography_left) # 左岸側の杭のj座標の修正（左岸側の左端の点をj = 0とする）
        js_center[i_section] = len(section_topography_left) # 中心線上の点のj座標（修正後の座標）をjs_centerベクトルに記録
        js_stake_right[i_section] = j_stake_right # 右岸側の杭のj座標（修正後の座標）をjs_stake_rightベクトルに記録
        js_stake_left[i_section] = j_stake_left # 左岸側の杭のj座標（修正後の座標）をjs_stake_leftベクトルに記録
        
        n_water_points = np.count_nonzero(section_topography == -9999.0) # 杭に挟まれた区間内の水面の点の個数
        if n_water_points == 0: # 水面が見つからなかった場合にはtolを緩めてやり直す
            print("水面が見つかりませんでした，この断面のtol1-3を緩めて標高読み取りをやり直します")
            tol1s[i_section,0] = tol5s[i_section,0] * 0.9
            tol2s[i_section,0] = 0.0
            tol3s[i_section,0] = 1.0
            tol1s[i_section,1] = tol5s[i_section,1] * 0.9
            tol2s[i_section,1] = 0.0
            tol3s[i_section,1] = 1.0
            continue
        
        sections_topography[i_section] = section_topography # 断面データのsections_topographyリストへの追加

"""
途中経過の出力
"""
print("途中経過を出力します")
with open ("intermediate_result.csv", "w") as fout:
    for i_section in range(n_sections):
        fout.write(str(stakes_right[i_section,0])+","+str(stakes_right[i_section,1])+","+str(stakes_right[i_section,2])+","+str(stakes_left[i_section,0])+","+str(stakes_left[i_section,1])+","+str(stakes_left[i_section,2])+","+str(js_stake_right[i_section])+","+str(js_stake_left[i_section])+","+str(js_center[i_section])+","+str(len(sections_topography[i_section])))
        for j in range(len(sections_topography[i_section])):
            fout.write(","+str(sections_topography[i_section][j]))
        fout.write("\n")

with open ("setting.csv", "w") as fout:
    fout.write("Distance,Use intermediate result,Flow,Angle adjustment,Left tol1,Left tol2,Left tol3,Left tol4,Left tol5,Left DEM,Right tol1,Right tol2,Roght tol3,Right tol4,Right tol5,Right DEM\n")
    for i_section in range(n_sections):
        fout.write(str(0.001*distance_between_sections*i_section)+",1,"+str(flows[i_section])+","+str(angle_adjusts[i_section] * 180.0 / np.pi)+","+str(tol1s[i_section,0])+","+str(tol2s[i_section,0])+","+str(tol3s[i_section,0])+","+str(tol4s[i_section,0])+","+str(tol5s[i_section,0])+","+dem_types[i_section][0]+","+str(tol1s[i_section,1])+","+str(tol2s[i_section,1])+","+str(tol3s[i_section,1])+","+str(tol4s[i_section,1])+","+str(tol5s[i_section,1])+","+dem_types[i_section][1]+"\n")

"""
川幅と水面の標高・勾配の設定
"""
print("横断面の河床標高を設定します")
widths_river = np.zeros(n_sections)
elevations_water_tmp = np.zeros(n_sections)
for i_section in range(n_sections):
    section_topography = sections_topography[i_section] # 横断面i_sectionの標高の数列
    j_stake_right = js_stake_right[i_section] # 右岸側の杭のj座標
    j_stake_left = js_stake_left[i_section] # 左岸側の杭のj座標
    section_topography = section_topography[j_stake_left:j_stake_right+1]
    
    n_water_points = np.count_nonzero(section_topography == -9999.0) # 杭に挟まれた区間内の水面の点の個数
    widths_river[i_section] = n_water_points * transverse_interval
    
    elevations_water_tmp[i_section] = np.min( section_topography[section_topography != -9999.0] ) # 杭に挟まれた区間内の標高の最小値を水面の標高とする

elevations_water = np.zeros(n_sections)
for i_section in range(n_sections):
    r = min(n_samples_for_median // 2, i_section, n_sections - 1 - i_section) # 自身±rの範囲の横断面を考える
    elevations_water[i_section] = np.median(elevations_water_tmp[i_section-r:i_section+r+1])

for i_section in range(n_sections-2, -1, -1): # 水位は必ず低下するという制約を課す
    elevations_water[i_section] = min(elevations_water[i_section], elevations_water[i_section+1] - minimum_slope_water * distance_between_sections)

slopes_water = np.zeros(n_sections)
slopes_water[n_sections-1] = minimum_slope_water # 最上流はminimum_slope_water
for i_section in range(n_sections-1):
    slopes_water[i_section] = (elevations_water[i_section+1] - elevations_water[i_section]) / distance_between_sections

"""
河床の設定
"""
depths = np.zeros(n_sections)
elevations_riverbed_tmp = np.zeros(n_sections)
for i_section in range(n_sections-1, -1, -1): # 上流の横断面から下流の横断面に向けて水深の計算を行う
    print(str(i_section)+" / "+str(n_sections))    
    if i_section == n_sections - 1:
        depths[i_section] = np.power(flows[i_section] * roughness / ( widths_river[i_section] * np.sqrt(slopes_water[i_section] ) ), 3.0 / 5.0) # 最上流には等流の公式を適用
    else:
        depths[i_section] = open_channel.find_depth(depths[i_section+1], flows[i_section+1], widths_river[i_section], widths_river[i_section+1], slopes_water[i_section], distance_between_sections, int(distance_between_sections / difference_in_differential_equation + 0.5), roughness)
    
    elevations_riverbed_tmp[i_section] = elevations_water[i_section] - depths[i_section]

elevations_riverbed = np.zeros(n_sections)
for i_section in range(n_sections):
    r = min(n_samples_for_median // 2, i_section, n_sections - 1 - i_section) # 自身±rの範囲の横断面を考える
    elevations_riverbed[i_section] = np.median(elevations_riverbed_tmp[i_section-r:i_section+r+1])
    
    section_topography = sections_topography[i_section] # 横断面i_sectionの標高の数列
    j_stake_right = js_stake_right[i_section] # 右岸側の杭のj座標
    j_stake_left = js_stake_left[i_section] # 左岸側の杭のj座標
    section_topography[j_stake_left:j_stake_right+1] = np.fmax(section_topography[j_stake_left:j_stake_right+1], elevations_riverbed[i_section]) # 河床底面を設定（-9999.0を河床底面の標高に切り上げ，elevation_riverbedよりも低い点も含む）
        
    """
    杭の外側の範囲の切り取り
    水位より標高が低い点，堤防よりも標高が高い点，標高が不明の点がある場合，その点以降をカットする
    また，杭からmargin[m]以上離れた点はカットする
    """
    for j in range(j_stake_right+1, len(section_topography)):
        if section_topography[j] < elevations_water[i_section] or section_topography[j] > stakes_right[i_section,2] or (j - j_stake_right) * transverse_interval >= margin + 1.0e-7:
            section_topography = section_topography[:j]
            break
    
    for j in range(j_stake_left-1, -1, -1):
        if section_topography[j] < elevations_water[i_section] or section_topography[j] > stakes_left[i_section,2]  or (j_stake_left - j) * transverse_interval >= margin + 1.0e-7:
            js_center[i_section] -= j + 1 # 左岸側を切り取る場合はj座標の補正が必要
            js_stake_right[i_section] -= j + 1 # 左岸側を切り取る場合はj座標の補正が必要
            js_stake_left[i_section] -= j + 1 # 左岸側を切り取る場合はj座標の補正が必要
            section_topography = section_topography[j+1:]
            break
    
    sections_topography[i_section] = section_topography

print("河道縦横断データを出力します")

if not os.path.exists("output"):
    os.makedirs("output")

if not iric_format:
    with open ("./output/oudan.csv", "w") as fout:
        for i_section in range(n_sections):
            fout.write("{:.3f}".format(0.001*distance_between_sections*i_section)+","+str(distance_between_sections)+","+str(stakes_left[i_section,2])+","+str(stakes_right[i_section,2])+",-9999,-9999,"+str(len(sections_topography[i_section]))+",-9999,-9999,-9999,0,0,20010101,0000000000,水系,川\n")
            for j in range(len(sections_topography[i_section])):
                fout.write("0,"+str(1.0*(j - js_stake_left[i_section]))+","+str(sections_topography[i_section][j])+"\n")
    
    with open ("./output/kui.csv", "w") as fout:
        fout.write("水系名,河川名,河川番号,地方整備局名,事務所名,管轄出張所名,左右岸,距離標名,緯度,経度,測量年月日,設置日,撤去日\n")
        for i_section in range(n_sections):
            fout.write("水系,川,0000000000,地方整備局,事務所,出張所,左岸,"+"{:.3f}".format(0.001*distance_between_sections*i_section)+","+str(stakes_left[i_section,1])+","+str(stakes_left[i_section,0])+",20010101,,\n")
            fout.write("水系,川,0000000000,地方整備局,事務所,出張所,右岸,"+"{:.3f}".format(0.001*distance_between_sections*i_section)+","+str(stakes_right[i_section,1])+","+str(stakes_right[i_section,0])+",20010101,,\n")
else:
    if not os.path.exists("./output/oudan"):
        os.makedirs("./output/oudan")
    
    for i_section in range(n_sections):
        with open ("./output/oudan/"+"{:.3f}".format(0.001*distance_between_sections*i_section)+"k.csv", "w") as fout:
            fout.write("{:.3f}".format(0.001*distance_between_sections*i_section)+","+str(distance_between_sections)+","+str(stakes_left[i_section,2])+","+str(stakes_right[i_section,2])+",-9999,-9999,"+str(len(sections_topography[i_section]))+",-9999,-9999,-9999,0,0,20010101,0000000000,水系,川\n")
            for j in range(len(sections_topography[i_section])):
                fout.write("0,"+str(1.0*(j - js_stake_left[i_section]))+","+str(sections_topography[i_section][j])+"\n")
    
    with open ("./output/kui.csv", "w") as fout:
        fout.write("K.P.,LX,LY,RX,RY\n")
        for i_section in range(n_sections):
            ly, lx = transformer_to_meter.transform(stakes_left[i_section,0], stakes_left[i_section,1])
            ry, rx = transformer_to_meter.transform(stakes_right[i_section,0], stakes_right[i_section,1])
            fout.write("{:.3f}".format(0.001*distance_between_sections*i_section)+","+str(lx)+","+str(ly)+","+str(rx)+","+str(ry)+"\n")

with open ("./output/elevation.csv", "w") as fout:
    fout.write("Distance,Riverbed,Water surface,Stake left,Stake right\n")
    for i_section in range(n_sections):
        fout.write(str(0.001*distance_between_sections*i_section)+","+str(elevations_riverbed[i_section])+","+str(elevations_water[i_section])+","+str(stakes_left[i_section,2])+","+str(stakes_right[i_section,2])+"\n")

print("プログラムの実行が完了しました")
