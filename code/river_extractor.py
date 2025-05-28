# -*- coding: utf-8 -*-

import os
import numpy as np
import csv
import shapefile
import pyproj
import dem
import open_channel
import rotation

class RiverCrossSectionExtractor:
    def __init__(self):
        self.read_basic_parameters()
        self.read_centerline()
        self.initialize_transformers()
        self.convert_points_to_meter()
        self.compute_direction_vectors()
        self.initialize_section_data()
        self.read_setting()
        self.read_intermediate_result()

    def read_basic_parameters(self):
        with open("basic_parameters.csv", "r") as fin:
            reader = csv.reader(fin)
            data = [row for row in reader]

        self.plane_rectangular_coordinate_system = data[0][1] # 対象の河川を含む平面直角座標系を指定
        self.id_begin = int(data[1][1]) # 河道のポイントデータの何番目から始めるか
        self.id_end = int(data[2][1]) # 河道のポイントデータの何番目で終えるか，id_endを含む
        self.flow = float(data[3][1]) # 平水時の流量[m3/s]，use_jflwdir_to_set_flow()を使うときは比流量[(m3/s)/(km2)]
        self.clear_crossings = int(data[4][1]) # 横断線の交差を解消するか
        self.tol1 = float(data[5][1]) # 最低点からtol1メートル以上でなければ堤防の頂点と見なさない
        self.tol2 = float(data[6][1]) # 頂点からtol2メートル下がったら堤防が終わったと見なす
        self.tol3 = float(data[7][1]) # 頂点からtol2メートル下がって，かつ，勾配がtol3以下になったら終了
        self.tol4 = float(data[8][1]) # 頂点が川の端からtol4メートル以上離れている場合はtol1とtol2が高すぎるので調整してやり直し
        self.tol5 = float(data[9][1]) # 頂点と最低点の差がtol5メートル以上の場合はtol1とtol2が高すぎるので調整してやり直し
        self.adjust1 = float(data[10][1]) # tol1を何倍に調整するか
        self.adjust2 = float(data[11][1]) # tol2を何倍に調整するか
        self.adjust3 = float(data[12][1]) # tol3を何倍に調整するか
        self.distance_between_sections = float(data[13][1]) # 断面取得間隔[m]
        self.transverse_interval = float(data[14][1]) # 横断面のポイント間隔[m]
        self.margin = float(data[15][1]) # 左岸端・右岸端の外側に何メートルのマージンを設けるか
        self.iric_format = int(data[16][1]) # iRICで読み取れる形式で出力するか
        self.difference_in_differential_equation = float(data[17][1]) # 不等流計算の差分間隔[m]
        self.roughness = float(data[18][1]) # 粗度係数
        self.minimum_slope_water = float(data[19][1]) # 水面勾配の最小値
        self.n_samples_for_median = int(data[20][1]) # 中央値を計算する際のサンプル数

        if self.n_samples_for_median % 2 == 0:
            raise ValueError("n_samples_for_averagingには奇数を指定して下さい")

    def read_centerline(self):
        sf = shapefile.Reader("river_centerline")
        shapes = sf.shapes()
        self.points = np.zeros((self.id_end + 1 - self.id_begin, 2)) # 河川の中心線を構成する点の座標の配列，points[i,0]はi番の点の経度，points[i,1]はi番の点の緯度，点は下流から上流に向けて並ぶ
        for i in range(len(self.points)):
            self.points[i, 0], self.points[i, 1] = shapes[self.id_end - i].points[0]
        sf.close()

    def initialize_transformers(self):
        self.transformer_to_meter = pyproj.Transformer.from_crs("epsg:4326", self.plane_rectangular_coordinate_system, always_xy=True)
        self.transformer_to_degree = pyproj.Transformer.from_crs(self.plane_rectangular_coordinate_system, "epsg:4326", always_xy=True)

    def convert_points_to_meter(self):
        self.points_meter = np.zeros_like(self.points) # 河川の中心線を構成する点の座標（メートル）の配列
        for i in range(len(self.points)):
            self.points_meter[i, 0], self.points_meter[i, 1] = self.transformer_to_meter.transform(self.points[i, 0], self.points[i, 1])

    def compute_direction_vectors(self):
        self.dist_between_points = np.zeros(len(self.points) - 1)
        self.j_vector = np.zeros((len(self.points) - 1, 2))
        self.v_vector = np.zeros((len(self.points) - 1, 2))
        for i in range(len(self.points) - 1):
            self.dist_between_points[i], self.j_vector[i], self.v_vector[i] = self.get_distance_between_points_and_vectors(i) # dist, j_vector, v_vectorを点i = 0から点i = len(points) - 1まで求めて配列に保存

        self.distance_accumulated = np.zeros(len(self.points))
        for i in range(len(self.points)):
            self.distance_accumulated[i] = np.sum(self.dist_between_points[0:i]) # 点0から点iまでの累積距離
    
    # 河川の中心線を構成するi番目の点とi+1番目の点の間の距離（dist），i+1番目からi番目の点に向かう単位ベクトル(j_vector)，それに垂直な右岸側を向く単位ベクトル（v_vector）を求める関数，単位ベクトルは緯度経度表示に変換してある
    def get_distance_between_points_and_vectors(self, i):
        j_vector_meter = self.points_meter[i+1,:] - self.points_meter[i,:]
        dist = np.sqrt(np.dot(j_vector_meter, j_vector_meter))
        j_vector_meter /= dist
        v_vector_meter = np.array([-j_vector_meter[1], j_vector_meter[0]])

        j_vector = np.zeros(2)
        j_vector[0], j_vector[1] = self.transformer_to_degree.transform(self.points_meter[i,0] + j_vector_meter[0], self.points_meter[i,1] + j_vector_meter[1])
        j_vector -= self.points[i,:]

        v_vector = np.zeros(2)
        v_vector[0], v_vector[1] = self.transformer_to_degree.transform(self.points_meter[i,0] + v_vector_meter[0], self.points_meter[i,1] + v_vector_meter[1])
        v_vector -= self.points[i,:]

        return dist, j_vector, v_vector
    
    # 与えられた度表示のベクトルを反時計周りにthetaラジアン回転する 
    def rotate_vector(self, vector, center, theta):
        center_meter = np.zeros(2)
        center_meter[0], center_meter[1] = self.transformer_to_meter.transform(center[0], center[1])
        
        vector_meter = np.zeros(2)
        vector_meter[0], vector_meter[1] = self.transformer_to_meter.transform(center[0] + vector[0], center[1] + vector[1])
        vector_meter -= center_meter[:]
        
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        vector_meter_rotated = np.zeros(2)
        vector_meter_rotated[0] = cos_theta * vector_meter[0] - sin_theta * vector_meter[1]
        vector_meter_rotated[1] = sin_theta * vector_meter[0] + cos_theta * vector_meter[1]
        
        vector_rotated = np.zeros(2)
        vector_rotated[0], vector_rotated[1] = self.transformer_to_degree.transform(center_meter[0] + vector_meter_rotated[0], center_meter[1] + vector_meter_rotated[1])
        vector_rotated -= center[:]
        
        return vector_rotated

    def initialize_section_data(self):
        self.n_sections = int(self.distance_accumulated[-1] / self.distance_between_sections)
        self.centers = np.zeros((self.n_sections, 2)) # centers[i_section,0]は横断面i_sectionの河道中心線上のx座標，centers[i_section,1]は横断面i_sectionの河道中心線上のy座標
        self.stakes_right = np.zeros((self.n_sections, 3)) # stakes_right[i_section,0]は横断面i_sectionの右岸側の杭のx座標，stakes_right[i_section,1]は横断面i_sectionの右岸側の杭のy座標，stakes_right[i_section,2]は横断面i_sectionの右岸側の杭の標高
        self.stakes_left = np.zeros((self.n_sections, 3)) # stakes_left[i_section,0]は横断面i_sectionの左岸側の杭のx座標，stakes_left[i_section,1]は横断面i_sectionの左岸側の杭のy座標，stakes_left[i_section,2]は横断面i_sectionの左岸側の杭の標高
        self.js_stake_right = np.zeros(self.n_sections, dtype=int) # js_stake_right[i_section]は横断面i_sectionの右岸側の杭のj座標
        self.js_stake_left = np.zeros(self.n_sections, dtype=int) # js_stake_left[i_section]は横断面i_sectionの左岸側の杭のj座標
        self.js_center = np.zeros(self.n_sections, dtype=int) # js_stake_left[i_section]は横断面i_sectionの中心線上の点のj座標

        self.sections_topography = [None] * self.n_sections # 横断面の標高データのリスト
        self.use_intermediate_result = np.zeros(self.n_sections, dtype=int) # use_intermediate_result[i_section] = 0は"intermediate_result.csv"のデータを使わない
        self.tol1s = np.ones((self.n_sections, 2)) * self.tol1 # i_sectionごとのtol1，tol1s[i_section,0]は左岸，tol1s[i_section,1]は右岸，以下同様
        self.tol2s = np.ones((self.n_sections, 2)) * self.tol2
        self.tol3s = np.ones((self.n_sections, 2)) * self.tol3
        self.tol4s = np.ones((self.n_sections, 2)) * self.tol4
        self.tol5s = np.ones((self.n_sections, 2)) * self.tol5
        self.angle_adjusts = np.zeros(self.n_sections)
        self.flows = np.ones(self.n_sections) * self.flow
        self.dem_types = [["A", "A"] for _ in range(self.n_sections)]

    def read_setting(self):
        try:
            with open("setting.csv", "r") as fin:
                reader = csv.reader(fin)
                data = [row for row in reader]

            for i_section in range(self.n_sections):
                self.use_intermediate_result[i_section] = int(data[1+i_section][1])
                self.flows[i_section] = float(data[1+i_section][2])
                self.angle_adjusts[i_section] = float(data[1+i_section][3]) * np.pi / 180.0
                self.tol1s[i_section][0] = float(data[1+i_section][4])
                self.tol2s[i_section][0] = float(data[1+i_section][5])
                self.tol3s[i_section][0] = float(data[1+i_section][6])
                self.tol4s[i_section][0] = float(data[1+i_section][7])
                self.tol5s[i_section][0] = float(data[1+i_section][8])
                self.dem_types[i_section][0] = data[1+i_section][9]
                self.tol1s[i_section][1] = float(data[1+i_section][10])
                self.tol2s[i_section][1] = float(data[1+i_section][11])
                self.tol3s[i_section][1] = float(data[1+i_section][12])
                self.tol4s[i_section][1] = float(data[1+i_section][13])
                self.tol5s[i_section][1] = float(data[1+i_section][14])
                self.dem_types[i_section][1] = data[1+i_section][15]

        except FileNotFoundError:
            pass
    
    def export_setting(self):
        with open("setting.csv", "w", newline="") as fout:
            writer = csv.writer(fout)
            writer.writerow([
                "Distance", "Use intermediate result", "Flow", "Angle adjustment",
                "Left tol1", "Left tol2", "Left tol3", "Left tol4", "Left tol5", "Left DEM",
                "Right tol1", "Right tol2", "Roght tol3", "Right tol4", "Right tol5", "Right DEM"
            ])
            for i_section in range(self.n_sections):
                distance = 0.001 * self.distance_between_sections * i_section
                angle_deg = self.angle_adjusts[i_section] * 180.0 / np.pi
                row = [
                    f"{distance:.3f}",
                    self.use_intermediate_result[i_section],
                    self.flows[i_section],
                    angle_deg,
                    self.tol1s[i_section, 0], self.tol2s[i_section, 0], self.tol3s[i_section, 0],
                    self.tol4s[i_section, 0], self.tol5s[i_section, 0], self.dem_types[i_section][0],
                    self.tol1s[i_section, 1], self.tol2s[i_section, 1], self.tol3s[i_section, 1],
                    self.tol4s[i_section, 1], self.tol5s[i_section, 1], self.dem_types[i_section][1]
                ]
                writer.writerow(row)
    
    def use_jflwdir_to_set_flow(self, flow_ratio, progress_callback=None):
        import flow_accumulation_area
        
        for i_section in range(self.n_sections):
            if progress_callback:
                progress_callback(i_section, self.n_sections, "流量設定")
            
            distance_section = self.distance_between_sections * i_section # 中心線を一定距離上るごとに横断面データを作成
            for i in range(len(self.points) - 1):
                if self.distance_accumulated[i+1] >= distance_section:
                    break

            self.centers[i_section, :] = self.points[i, :] + (distance_section - self.distance_accumulated[i]) * self.j_vector[i] # 中心線上の点の緯度経度座標

            if self.angle_adjusts[i_section] == 0.0:
                direction_transverse = self.v_vector[i] # direction_transverseは右岸側を向く単位ベクトル
            else:
                direction_transverse = self.rotate_vector(self.v_vector[i], self.centers[i_section, :], self.angle_adjusts[i_section])

            max_area = 0.0
            min_area = 1.0e100
            j = 0 # 中心線上の点がj = 0，jが+1されると右岸側に5m進む
            while True:
                current = self.centers[i_section, :] + j * 5.0 * direction_transverse
                area = flow_accumulation_area.get_area(current[0], current[1])
                max_area = max(area, max_area)
                min_area = min(area, min_area)
                
                current = self.centers[i_section, :] - j * 5.0 * direction_transverse
                area = flow_accumulation_area.get_area(current[0], current[1])
                max_area = max(area, max_area)
                min_area = min(area, min_area)
                
                if max_area >= min_area * 100.0 and max_area >= 1.0 and j * 5.0 >= 100.0:
                    break
                else:
                    j += 1
            
            self.flows[i_section] = flow_ratio * max_area
        
        if progress_callback:
            progress_callback(0, 1, "ファイル出力")
        
        # setting.csv の出力
        self.export_setting()
    
    def read_intermediate_result(self):
        try:
            with open("intermediate_result.csv", "r") as fin:
                reader = csv.reader(fin)
                data = [row for row in reader]

            for i_section in range(self.n_sections):
                if self.use_intermediate_result[i_section]:
                    self.centers[i_section][0] = float(data[i_section][0])
                    self.centers[i_section][1] = float(data[i_section][1])
                    self.stakes_right[i_section][0] = float(data[i_section][2])
                    self.stakes_right[i_section][1] = float(data[i_section][3])
                    self.stakes_right[i_section][2] = float(data[i_section][4])
                    self.stakes_left[i_section][0] = float(data[i_section][5])
                    self.stakes_left[i_section][1] = float(data[i_section][6])
                    self.stakes_left[i_section][2] = float(data[i_section][7])
                    self.js_stake_right[i_section] = int(data[i_section][8])
                    self.js_stake_left[i_section] = int(data[i_section][9])
                    self.js_center[i_section] = int(data[i_section][10])
                    dim_section_topography = int(data[i_section][11])
                    section_topography = np.zeros(dim_section_topography)
                    for j in range(dim_section_topography):
                        section_topography[j] = float(data[i_section][12 + j])
                    self.sections_topography[i_section] = section_topography

        except FileNotFoundError:
            pass
    
    def read_elevation(self, progress_callback=None):
        for i_section in range(self.n_sections):
            if progress_callback:
                progress_callback(i_section, self.n_sections, "標高読み取り")
            
            if not self.use_intermediate_result[i_section]:
                distance_section = self.distance_between_sections * i_section # 中心線を一定距離上るごとに横断面データを作成
                for i in range(len(self.points) - 1):
                    if self.distance_accumulated[i+1] >= distance_section:
                        break

                self.centers[i_section, :] = self.points[i, :] + (distance_section - self.distance_accumulated[i]) * self.j_vector[i] # 中心線上の点の緯度経度座標

                if self.angle_adjusts[i_section] == 0.0:
                    direction_transverse = self.v_vector[i] # direction_transverseは右岸側を向く単位ベクトル
                else:
                    direction_transverse = self.rotate_vector(self.v_vector[i], self.centers[i_section, :], self.angle_adjusts[i_section])

                section_topography_right = np.array([]) # 右岸側の標高データの配列

                j = 0 # 中心線上の点がj = 0，そこから右岸側にtransverse_intervalメートル進むごとに+1，左岸側にtransverse_intervalメートル進むごとに-1される整数座標
                top = bottom = elevation_previous = -9999.0 # 右岸側で発見された中で最高の標高，最低の標高，一つ前の点の標高（初期値は-9999.0）

                while True: # 右岸側の横断面データが完成するまで繰り返す
                    current = self.centers[i_section, :] + j * self.transverse_interval * direction_transverse # 点jに対応した緯度経度座標

                    if section_topography_right.size == j:
                        elevation = dem.get_elevation(current[0], current[1], self.dem_types[i_section][1]) # 点jの標高を取得
                        section_topography_right = np.append(section_topography_right, elevation) # section_topography_rightに標高データを追加
                    else:
                        elevation = section_topography_right[j] # 標高データを読み取り済みの場合

                    if elevation != -9999.0: # 標高データが正常値の場合（水面は-9999.0）
                        if bottom == -9999.0 or elevation < bottom: # bottomが初期値の場合はその標高データをbottomに代入，そうでない場合はその標高データが現在のbottomより低い場合にbottomを更新
                            bottom = elevation
                        if elevation >= top: # 標高データが最高値を更新したら暫定の頂点データとして記録
                            top = elevation # 最高の標高
                            self.stakes_right[i_section, 0:2] = current # 杭の座標
                            self.stakes_right[i_section, 2] = top # 杭の標高
                            j_stake_right = j # 杭のj

                        if top >= bottom + self.tol1s[i_section,1] and elevation <= top - self.tol2s[i_section,1] and abs(elevation - elevation_previous) <= self.tol3s[i_section,1] * self.transverse_interval: # tol1, tol2, tol3の条件が満たされたら記録終了
                            break

                    if abs(j) * self.transverse_interval >= self.tol4s[i_section,1] or (bottom != -9999.0 and elevation - bottom >= self.tol5s[i_section,1]): # tol4やtol5の基準から見て問題がある場合にはscale1とscale2を調整してwhileループを最初からやり直し
                        self.tol1s[i_section,1] *= self.adjust1
                        self.tol2s[i_section,1] = max(self.tol2s[i_section,1] * self.adjust2 - 0.1, 0.0)
                        self.tol3s[i_section,1] *= self.adjust3
                        if self.tol3s[i_section,1] >= 100.0:
                            raise ValueError(f"座標({self.centers[i_section,1]}N, {self.centers[i_section,0]}E)の右岸側の地形データが存在しません")
                        j = 0
                        top = bottom = elevation_previous = -9999.0
                    else:
                        elevation_previous = elevation # 一つ前の点の標高を更新（勾配の計算に使用）
                        j += 1

                section_topography_left = np.array([])

                j = -1
                top = bottom = elevation_previous = -9999.0

                while True:
                    current = self.centers[i_section, :] + j * self.transverse_interval * direction_transverse

                    if section_topography_left.size == -j-1:
                        elevation = dem.get_elevation(current[0], current[1], self.dem_types[i_section][0])
                        section_topography_left = np.append(section_topography_left, elevation)
                    else:
                        elevation = section_topography_left[-j-1]

                    if elevation != -9999.0:
                        if bottom == -9999.0 or elevation < bottom:
                            bottom = elevation
                        if elevation >= top:
                            top = elevation
                            self.stakes_left[i_section, 0:2] = current
                            self.stakes_left[i_section, 2] = top
                            j_stake_left = j

                        if top >= bottom + self.tol1s[i_section,0] and elevation <= top - self.tol2s[i_section,0] and abs(elevation - elevation_previous) <= self.tol3s[i_section,0] * self.transverse_interval:
                            break

                    if abs(j) * self.transverse_interval >= self.tol4s[i_section,0] or (bottom != -9999.0 and elevation - bottom >= self.tol5s[i_section,0]):
                        self.tol1s[i_section,0] *= self.adjust1
                        self.tol2s[i_section,0] = max(self.tol2s[i_section,0] * self.adjust2 - 0.1, 0.0)
                        self.tol3s[i_section,0] *= self.adjust3
                        if self.tol3s[i_section,0] >= 100.0:
                            raise ValueError(f"座標({self.centers[i_section,1]}N, {self.centers[i_section,0]}E)の左岸側の地形データが存在しません")
                        j = -1
                        top = bottom = elevation_previous = -9999.0
                    else:
                        elevation_previous = elevation
                        j -= 1

                section_topography_left = section_topography_left[::-1] # section_topography_leftの標高データの配列はj = -1, j = -2, j = -3, ...と逆順に並んでいるため反転させる

                section_topography = np.append(section_topography_left, section_topography_right) # 左岸側・右岸側のデータの結合
                j_stake_right += len(section_topography_left) # 右岸側の杭のj座標の修正（左岸側の左端の点をj = 0とする）
                j_stake_left += len(section_topography_left) # 左岸側の杭のj座標の修正（左岸側の左端の点をj = 0とする）
                self.js_center[i_section] = len(section_topography_left) # 中心線上の点のj座標（修正後の座標）をjs_centerベクトルに記録
                self.js_stake_right[i_section] = j_stake_right # 右岸側の杭のj座標（修正後の座標）をjs_stake_rightベクトルに記録
                self.js_stake_left[i_section] = j_stake_left # 左岸側の杭のj座標（修正後の座標）をjs_stake_leftベクトルに記録

                n_water_points = np.count_nonzero(section_topography == -9999.0) # 杭に挟まれた区間内の水面の点の個数
                if n_water_points == 0: # 水面が見つからなかった場合にはtolを緩めてやり直す
                    print("水面が見つかりませんでした，この断面のtol1-3を緩めて標高読み取りをやり直します")
                    self.tol1s[i_section,0] = self.tol5s[i_section,0] * 0.9
                    self.tol2s[i_section,0] = 0.0
                    self.tol3s[i_section,0] = 1.0
                    self.tol1s[i_section,1] = self.tol5s[i_section,1] * 0.9
                    self.tol2s[i_section,1] = 0.0
                    self.tol3s[i_section,1] = 1.0
                    continue

                self.sections_topography[i_section] = section_topography # 断面データのsections_topographyリストへの追加
                self.use_intermediate_result[i_section] = 1 # このプログラム内で次回にread_elevationを使うときは基本的にuse_intermediate_result = 1
    
    def export_intermediate_result(self):
        with open("intermediate_result.csv", "w", newline="") as fout:
            writer = csv.writer(fout)
            for i_section in range(self.n_sections):
                row = [
                    self.centers[i_section, 0], self.centers[i_section, 1],
                    self.stakes_right[i_section, 0], self.stakes_right[i_section, 1], self.stakes_right[i_section, 2],
                    self.stakes_left[i_section, 0], self.stakes_left[i_section, 1], self.stakes_left[i_section, 2],
                    self.js_stake_right[i_section], self.js_stake_left[i_section], self.js_center[i_section],
                    len(self.sections_topography[i_section])
                ]
                row += self.sections_topography[i_section].tolist()  # 地形情報を展開
                writer.writerow(row)
    
    def rotate_crossed_lines(self):
        centers_meter = np.zeros((self.n_sections, 2))
        stakes_right_meter = np.zeros((self.n_sections, 2))
        stakes_left_meter = np.zeros((self.n_sections, 2))
        rotated = np.zeros(self.n_sections, dtype=int) # この関数内で回転が行われた場合にTrueになる

        for i_section in range(self.n_sections):
            centers_meter[i_section, 0], centers_meter[i_section, 1] = self.transformer_to_meter.transform(
                self.centers[i_section, 0], self.centers[i_section, 1]
            )
            stakes_left_meter[i_section, 0], stakes_left_meter[i_section, 1] = self.transformer_to_meter.transform(
                self.stakes_left[i_section, 0], self.stakes_left[i_section, 1]
            )
            stakes_right_meter[i_section, 0], stakes_right_meter[i_section, 1] = self.transformer_to_meter.transform(
                self.stakes_right[i_section, 0], self.stakes_right[i_section, 1]
            )

        while True:
            min_cos = 1.0
            selected_i_section1 = -1
            selected_left_or_right = 0

            for i_section1 in range(self.n_sections - 1):
                i_section2 = i_section1 + 1

                cos = rotation.min_cos_angle_adjustment(
                    centers_meter[i_section1], centers_meter[i_section2],
                    stakes_left_meter[i_section1], stakes_left_meter[i_section2]
                )
                if cos < min_cos:
                    min_cos = cos
                    selected_i_section1 = i_section1
                    selected_left_or_right = -1

                cos = rotation.min_cos_angle_adjustment(
                    centers_meter[i_section1], centers_meter[i_section2],
                    stakes_right_meter[i_section1], stakes_right_meter[i_section2]
                )
                if cos < min_cos:
                    min_cos = cos
                    selected_i_section1 = i_section1
                    selected_left_or_right = 1

            if selected_i_section1 == -1: # 交差する横断線はもはや無いので終了
                break

            i_section1 = selected_i_section1
            i_section2 = i_section1 + 1

            if selected_left_or_right == -1:
                angle1, angle2, stake1_dash, stake2_dash, ostake1_dash, ostake2_dash = rotation.angle_adjustment(
                    centers_meter[i_section1], centers_meter[i_section2],
                    stakes_left_meter[i_section1], stakes_left_meter[i_section2],
                    stakes_right_meter[i_section1], stakes_right_meter[i_section2]
                )
                self.angle_adjusts[i_section1] += angle1
                self.angle_adjusts[i_section2] += angle2
                stakes_left_meter[i_section1] = stake1_dash
                stakes_left_meter[i_section2] = stake2_dash
                stakes_right_meter[i_section1] = ostake1_dash
                stakes_right_meter[i_section2] = ostake2_dash
            else:
                angle1, angle2, stake1_dash, stake2_dash, ostake1_dash, ostake2_dash = rotation.angle_adjustment(
                    centers_meter[i_section1], centers_meter[i_section2],
                    stakes_right_meter[i_section1], stakes_right_meter[i_section2],
                    stakes_left_meter[i_section1], stakes_left_meter[i_section2]
                )
                self.angle_adjusts[i_section1] += angle1
                self.angle_adjusts[i_section2] += angle2
                stakes_right_meter[i_section1] = stake1_dash
                stakes_right_meter[i_section2] = stake2_dash
                stakes_left_meter[i_section1] = ostake1_dash
                stakes_left_meter[i_section2] = ostake2_dash

            rotated[i_section1] = 1
            rotated[i_section2] = 1
            self.use_intermediate_result[i_section1] = 0 # 回転したら再度標高を読み取らないといけない
            self.use_intermediate_result[i_section2] = 0 # 回転したら再度標高を読み取らないといけない

            print(
                f"{0.001 * self.distance_between_sections * i_section1:.3f}kを{angle1 * 180.0 / np.pi}°，"
                f"{0.001 * self.distance_between_sections * i_section2:.3f}kを{angle2 * 180.0 / np.pi}°回転しました"
            )

        return np.any(rotated)

    def calculate_water_surface(self):
        self.widths_river = np.zeros(self.n_sections)
        self.elevations_water_tmp = np.zeros(self.n_sections)

        for i_section in range(self.n_sections):
            section_topography = self.sections_topography[i_section] # 横断面i_sectionの標高の数列
            j_right = self.js_stake_right[i_section] # 右岸側の杭のj座標
            j_left = self.js_stake_left[i_section] # 左岸側の杭のj座標
            segment = section_topography[j_left:j_right+1]

            self.widths_river[i_section] = np.count_nonzero(segment == -9999.0) * self.transverse_interval # 杭に挟まれた区間内の水面の点の個数
            self.elevations_water_tmp[i_section] = np.min(segment[segment != -9999.0]) # 杭に挟まれた区間内の標高の最小値を水面の標高とする

        self.elevations_water = np.zeros(self.n_sections)
        for i in range(self.n_sections):
            r = min(self.n_samples_for_median // 2, i, self.n_sections - 1 - i) # 自身±rの範囲の横断面を考える
            self.elevations_water[i] = np.median(self.elevations_water_tmp[i - r:i + r + 1])

        for i in range(self.n_sections - 2, -1, -1): # 水位は必ず低下するという制約を課す
            self.elevations_water[i] = min(
                self.elevations_water[i],
                self.elevations_water[i + 1] - self.minimum_slope_water * self.distance_between_sections
            )

        self.slopes_water = np.zeros(self.n_sections)
        self.slopes_water[self.n_sections - 1] = self.minimum_slope_water # 最上流はminimum_slope_water
        for i in range(self.n_sections - 1):
            self.slopes_water[i] = (
                self.elevations_water[i + 1] - self.elevations_water[i]
            ) / self.distance_between_sections

    def calculate_riverbed(self, progress_callback=None):
        self.depths = np.zeros(self.n_sections)
        self.elevations_riverbed_tmp = np.zeros(self.n_sections)

        for i in range(self.n_sections - 1, -1, -1): # 上流の横断面から下流の横断面に向けて水深の計算を行う
            if progress_callback:
                progress_callback(self.n_sections - 1 - i, self.n_sections, "河床標高計算")
            
            if self.widths_river[i] == 0.0 or self.slopes_water[i] == 0.0:
                print(self.widths_river[i], self.slopes_water[i])
                raise ValueError

            if i == self.n_sections - 1:
                self.depths[i] = (self.flows[i] * self.roughness / (self.widths_river[i] * np.sqrt(self.slopes_water[i]))) ** (3.0 / 5.0) # 最上流には等流の公式を適用
            else:
                self.depths[i] = open_channel.find_depth(
                    self.depths[i + 1], self.flows[i + 1],
                    self.widths_river[i], self.widths_river[i + 1],
                    self.slopes_water[i], self.distance_between_sections,
                    int(self.distance_between_sections / self.difference_in_differential_equation + 0.5),
                    self.roughness
                )

            self.elevations_riverbed_tmp[i] = self.elevations_water[i] - self.depths[i]

        self.elevations_riverbed = np.zeros(self.n_sections)
        for i in range(self.n_sections):
            r = min(self.n_samples_for_median // 2, i, self.n_sections - 1 - i)
            self.elevations_riverbed[i] = np.median(self.elevations_riverbed_tmp[i - r:i + r + 1])

            section_topography = self.sections_topography[i]
            j_left = self.js_stake_left[i]
            j_right = self.js_stake_right[i]
            section_topography[j_left:j_right+1] = np.fmax(
                section_topography[j_left:j_right+1],
                self.elevations_riverbed[i]
            ) # 河床底面を設定（-9999.0を河床底面の標高に切り上げ，elevation_riverbedよりも低い点も含む）

            for j in range(j_right + 1, len(section_topography)):
                if (section_topography[j] < self.elevations_water[i] or
                    section_topography[j] > self.stakes_right[i, 2] or
                    (j - j_right) * self.transverse_interval >= self.margin + 1.0e-7):
                    section_topography = section_topography[:j]
                    break

            for j in range(j_left - 1, -1, -1):
                if (section_topography[j] < self.elevations_water[i] or
                    section_topography[j] > self.stakes_left[i, 2] or
                    (j_left - j) * self.transverse_interval >= self.margin + 1.0e-7):
                    self.js_center[i] -= j + 1 # 左岸側を切り取る場合はj座標の補正が必要
                    self.js_stake_right[i] -= j + 1 # 左岸側を切り取る場合はj座標の補正が必要
                    self.js_stake_left[i] -= j + 1 # 左岸側を切り取る場合はj座標の補正が必要
                    section_topography = section_topography[j + 1:]
                    break

            self.sections_topography[i] = section_topography
    
    def export_results(self):
        if not os.path.exists("output"):
            os.makedirs("output")
    
        if not self.iric_format:
            with open("./output/oudan.csv", "w") as fout:
                for i in range(self.n_sections):
                    fout.write(f"{0.001 * self.distance_between_sections * i:.3f},{self.distance_between_sections},{self.stakes_left[i,2]},{self.stakes_right[i,2]},-9999,-9999,{len(self.sections_topography[i])},-9999,-9999,-9999,-9999,0,20010101,0000000000,水系,川\n")
                    for j, elev in enumerate(self.sections_topography[i]):
                        fout.write(f"0,{1.0 * (j - self.js_stake_left[i])},{elev}\n")
    
            with open("./output/kui.csv", "w") as fout:
                fout.write("水系名,河川名,河川番号,地方整備局名,事務所名,管轄出張所名,左右岸,距離標名,緯度,経度,測量年月日,設置日,撤去日\n")
                for i in range(self.n_sections):
                    fout.write(f"水系,川,0000000000,地方整備局,事務所,出張所,左岸,{0.001 * self.distance_between_sections * i:.3f},{self.stakes_left[i,1]},{self.stakes_left[i,0]},20010101,,\n")
                    fout.write(f"水系,川,0000000000,地方整備局,事務所,出張所,右岸,{0.001 * self.distance_between_sections * i:.3f},{self.stakes_right[i,1]},{self.stakes_right[i,0]},20010101,,\n")
        else:
            if not os.path.exists("./output/oudan"):
                os.makedirs("./output/oudan")
            for i in range(self.n_sections):
                with open(f"./output/oudan/{0.001 * self.distance_between_sections * i:.3f}k.csv", "w") as fout:
                    fout.write(f"{0.001 * self.distance_between_sections * i:.3f},{self.distance_between_sections},{self.stakes_left[i,2]},{self.stakes_right[i,2]},-9999,-9999,{len(self.sections_topography[i])},-9999,-9999,-9999,-9999,0,20010101,0000000000,水系,川\n")
                    for j, elev in enumerate(self.sections_topography[i]):
                        fout.write(f"0,{1.0 * (j - self.js_stake_left[i])},{elev}\n")
    
            with open("./output/kui.csv", "w") as fout:
                fout.write("K.P.,LX,LY,RX,RY\n")
                for i in range(self.n_sections):
                    ly, lx = self.transformer_to_meter.transform(self.stakes_left[i,0], self.stakes_left[i,1])
                    ry, rx = self.transformer_to_meter.transform(self.stakes_right[i,0], self.stakes_right[i,1])
                    fout.write(f"{0.001 * self.distance_between_sections * i:.3f},{lx},{ly},{rx},{ry}\n")
    
        with open("./output/elevation.csv", "w") as fout:
            fout.write("Distance,Riverbed,Water surface,Water Edge,Stake left,Stake right\n")
            for i in range(self.n_sections):
                fout.write(f"{0.001 * self.distance_between_sections * i},{self.elevations_riverbed[i]},{self.elevations_water[i]},{self.elevations_water_tmp[i]},{self.stakes_left[i,2]},{self.stakes_right[i,2]}\n")
        
        # 平滑化前河床標高も表示する場合
        """
        with open("./output/elevation.csv", "w") as fout:
            fout.write("Distance,Riverbed,Raw Riverbed,Water surface,Water Edge,Stake left,Stake right\n")
            for i in range(self.n_sections):
                fout.write(f"{0.001 * self.distance_between_sections * i},{self.elevations_riverbed[i]},{self.elevations_riverbed_tmp[i]},{self.elevations_water[i]},{self.elevations_water_tmp[i]},{self.stakes_left[i,2]},{self.stakes_right[i,2]}\n")
        """
        
        w = shapefile.Writer("./output/river_channel")
        w.shapeType = shapefile.POLYLINE
        w.field('name', 'C')
        w.field('left bank', 'N', decimal=3)
        w.field('right bank', 'N', decimal=3)
        w.field('riverbed', 'N', decimal=3)
    
        points = [(self.stakes_left[i,0], self.stakes_left[i,1]) for i in range(self.n_sections)]
        w.line([points])
        w.record("Left", None, None, None)
        points = [(self.stakes_right[i,0], self.stakes_right[i,1]) for i in range(self.n_sections)]
        w.line([points])
        w.record("Right", None, None, None)
    
        for i in range(self.n_sections):
            dlon = (self.stakes_right[i,0] - self.stakes_left[i,0]) / (self.js_stake_right[i] - self.js_stake_left[i])
            dlat = (self.stakes_right[i,1] - self.stakes_left[i,1]) / (self.js_stake_right[i] - self.js_stake_left[i])
            start = (self.stakes_left[i,0] + (0 - self.js_stake_left[i]) * dlon, self.stakes_left[i,1] + (0 - self.js_stake_left[i]) * dlat)
            end = (self.stakes_left[i,0] + (len(self.sections_topography[i]) - 1 - self.js_stake_left[i]) * dlon, self.stakes_left[i,1] + (len(self.sections_topography[i]) - 1 - self.js_stake_left[i]) * dlat)
            w.line([[start, end]])
            w.record(f"{0.001 * self.distance_between_sections * i:.3f}k", self.stakes_left[i,2], self.stakes_right[i,2], self.elevations_riverbed[i])
        w.close()
    
        with open('./output/river_channel.prj', 'w') as fout:
            fout.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
    
    def run(self, progress_callback=None):
        self.read_setting() # ユーザーの設定変更を反映
        self.read_intermediate_result() # 河床標高が推定される前の中間結果を読まないといけない
        
        self.read_elevation(progress_callback=progress_callback)
        
        if progress_callback:
            progress_callback(0, 1, "中間結果出力")
        self.export_intermediate_result()
        self.export_setting()
        
        if self.clear_crossings:
            if progress_callback:
                progress_callback(0, 1, "横断線交差判定・修正")
            if self.rotate_crossed_lines():
                self.read_elevation(progress_callback=progress_callback)
                if progress_callback:
                    progress_callback(0, 1, "中間結果出力")
                self.export_intermediate_result()
                self.export_setting()
        
        self.calculate_water_surface()

        self.calculate_riverbed(progress_callback=progress_callback)

        if progress_callback:
            progress_callback(0, 1, "ファイル出力")
        self.export_results()

        if progress_callback:
            progress_callback(1, 1, "完了")
