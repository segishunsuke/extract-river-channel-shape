# -*- coding: utf-8 -*-

import os
import numpy as np
import csv
import pyproj
import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import linemerge

import dem
import dem1a
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
        
        # 限界線のキャッシュ
        self.left_limit_line = None
        self.right_limit_line = None
        
        self.read_intermediate_result()

    def read_basic_parameters(self):
        with open("./input/basic_parameters.csv", "r") as fin:
            reader = csv.reader(fin)
            data = [row for row in reader]

        self.plane_rectangular_coordinate_system = data[0][1]
        self.id_begin = int(data[1][1])
        self.id_end = int(data[2][1])
        self.estimate_water_depth = int(data[3][1])
        self.clear_crossings = int(data[4][1])
        self.flow = float(data[5][1])
        self.tol1 = float(data[6][1])
        self.tol2 = float(data[7][1])
        self.tol3 = float(data[8][1])
        self.tol4 = float(data[9][1])
        self.tol5 = float(data[10][1])
        self.dem_type = data[11][1]
        self.distance_between_sections = float(data[12][1])
        self.transverse_interval = float(data[13][1])
        self.margin = float(data[14][1])
        self.iric_format = int(data[15][1])
        self.adjust1 = float(data[16][1])
        self.adjust2 = float(data[17][1])
        self.adjust3 = float(data[18][1])
        self.water_surface_tolerance = float(data[19][1])
        self.difference_in_differential_equation = float(data[20][1])
        self.roughness = float(data[21][1])
        self.minimum_slope_water = float(data[22][1])
        self.n_samples_for_median_water_surface = int(data[23][1])
        self.n_samples_for_median_riverbed = int(data[24][1])

        if self.n_samples_for_median_water_surface % 2 == 0:
            self.n_samples_for_median_water_surface += 1
        if self.n_samples_for_median_riverbed % 2 == 0:
            self.n_samples_for_median_riverbed += 1

    def read_centerline(self):
        gdf = gpd.read_file("./input/river_centerline.gpkg", engine="pyogrio")
        self.points = np.zeros((self.id_end + 1 - self.id_begin, 2))
        for i in range(len(self.points)):
            point_geom = gdf.geometry.iloc[self.id_end - i]
            self.points[i, 0] = point_geom.x
            self.points[i, 1] = point_geom.y

    def initialize_transformers(self):
        self.transformer_to_meter = pyproj.Transformer.from_crs("epsg:4326", self.plane_rectangular_coordinate_system, always_xy=True)
        self.transformer_to_degree = pyproj.Transformer.from_crs(self.plane_rectangular_coordinate_system, "epsg:4326", always_xy=True)

    def convert_points_to_meter(self):
        self.points_meter = np.zeros_like(self.points)
        for i in range(len(self.points)):
            self.points_meter[i, 0], self.points_meter[i, 1] = self.transformer_to_meter.transform(self.points[i, 0], self.points[i, 1])

    def compute_direction_vectors(self):
        self.dist_between_points = np.zeros(len(self.points) - 1)
        self.j_vector = np.zeros((len(self.points) - 1, 2))
        self.v_vector = np.zeros((len(self.points) - 1, 2))
        for i in range(len(self.points) - 1):
            self.dist_between_points[i], self.j_vector[i], self.v_vector[i] = self.get_distance_between_points_and_vectors(i)

        self.distance_accumulated = np.zeros(len(self.points))
        for i in range(len(self.points)):
            self.distance_accumulated[i] = np.sum(self.dist_between_points[0:i])
    
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
        self.centers = np.zeros((self.n_sections, 2))
        self.stakes_right = np.zeros((self.n_sections, 3))
        self.stakes_left = np.zeros((self.n_sections, 3))
        self.js_stake_right = np.zeros(self.n_sections, dtype=int)
        self.js_stake_left = np.zeros(self.n_sections, dtype=int)
        self.js_center = np.zeros(self.n_sections, dtype=int)

        self.sections_topography = [None] * self.n_sections
        self.use_intermediate_result = np.zeros(self.n_sections, dtype=int)
        self.tol1s = np.ones((self.n_sections, 2)) * self.tol1
        self.tol2s = np.ones((self.n_sections, 2)) * self.tol2
        self.tol3s = np.ones((self.n_sections, 2)) * self.tol3
        self.tol4s = np.ones((self.n_sections, 2)) * self.tol4
        self.tol5s = np.ones((self.n_sections, 2)) * self.tol5
        self.angle_adjusts = np.zeros(self.n_sections)
        self.flows = np.ones(self.n_sections) * self.flow
        self.dem_types = [[self.dem_type, self.dem_type] for _ in range(self.n_sections)]
        self.wsts = np.zeros(self.n_sections)

        self.mode_left = np.zeros(self.n_sections, dtype=int)
        self.mode_right = np.zeros(self.n_sections, dtype=int)

    def read_setting(self):
        try:
            with open("settings.csv", "r") as fin:
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
                self.wsts[i_section] = float(data[1+i_section][16])
                
                if len(data[1+i_section]) > 17:
                    self.mode_left[i_section] = int(data[1+i_section][17])
                    self.mode_right[i_section] = int(data[1+i_section][18])

        except FileNotFoundError:
            pass
    
    def export_setting(self):
        with open("settings.csv", "w", newline="") as fout:
            writer = csv.writer(fout)
            writer.writerow([
                "Distance", "Use intermediate result", "Flow", "Angle adjustment",
                "Left tol1", "Left tol2", "Left tol3", "Left tol4", "Left tol5", "Left DEM",
                "Right tol1", "Right tol2", "Right tol3", "Right tol4", "Right tol5", "Right DEM",
                "W.S.T.", "Left Mode", "Right Mode"
            ])
            for i_section in range(self.n_sections):
                distance = 0.001 * self.distance_between_sections * i_section
                angle_deg = self.angle_adjusts[i_section] * 180.0 / np.pi
                row = [
                    f"{distance:.3f}",
                    self.use_intermediate_result[i_section],
                    self.flows[i_section],
                    angle_deg,
                    f"{self.tol1s[i_section, 0]:.3f}", f"{self.tol2s[i_section, 0]:.3f}", f"{self.tol3s[i_section, 0]:.3f}",
                    self.tol4s[i_section, 0], self.tol5s[i_section, 0], self.dem_types[i_section][0],
                    f"{self.tol1s[i_section, 1]:.3f}", f"{self.tol2s[i_section, 1]:.3f}", f"{self.tol3s[i_section, 1]:.3f}",
                    self.tol4s[i_section, 1], self.tol5s[i_section, 1], self.dem_types[i_section][1],
                    self.wsts[i_section],
                    self.mode_left[i_section],
                    self.mode_right[i_section]
                ]
                writer.writerow(row)
    
    def use_jflwdir_to_set_flow(self, flow_ratio, progress_callback=None):
        import flow_accumulation_area
        for i_section in range(self.n_sections):
            if progress_callback:
                progress_callback(i_section, self.n_sections, "流量設定")
            
            distance_section = self.distance_between_sections * i_section
            for i in range(len(self.points) - 1):
                if self.distance_accumulated[i+1] >= distance_section:
                    break

            self.centers[i_section, :] = self.points[i, :] + (distance_section - self.distance_accumulated[i]) * self.j_vector[i]

            if self.angle_adjusts[i_section] == 0.0:
                direction_transverse = self.v_vector[i]
            else:
                direction_transverse = self.rotate_vector(self.v_vector[i], self.centers[i_section, :], self.angle_adjusts[i_section])

            max_area = 0.0
            min_area = 1.0e100
            j = 0
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
        self.export_setting()

    def load_limit_lines_if_needed(self):
        """Mode=1（限界線指定）が設定されている場合のみ、GPKGを読み込む"""
        if 1 in self.mode_left and self.left_limit_line is None:
            if not os.path.exists("./input/left_limit.gpkg"):
                raise FileNotFoundError("左岸が限界線モードになっていますが、./input/left_limit.gpkg が見つかりません。")
                
            gdf_left = gpd.read_file("./input/left_limit.gpkg", engine="pyogrio")
            left_lines = []
            for geom in gdf_left.geometry:
                if geom is None: continue
                if 'LineString' in geom.geom_type:
                    if 'Multi' in geom.geom_type:
                        for line in geom.geoms:
                            meter_pts = [self.transformer_to_meter.transform(x, y) for x, y in line.coords]
                            left_lines.append(LineString(meter_pts))
                    else:
                        meter_pts = [self.transformer_to_meter.transform(x, y) for x, y in geom.coords]
                        left_lines.append(LineString(meter_pts))
            
            if not left_lines:
                raise ValueError("left_limit.gpkg に有効な線データがありません。QGISで「レイヤの編集を保存」したか確認してください。")
            self.left_limit_line = linemerge(left_lines) if len(left_lines) > 1 else left_lines[0]

        if 1 in self.mode_right and self.right_limit_line is None:
            if not os.path.exists("./input/right_limit.gpkg"):
                raise FileNotFoundError("右岸が限界線モードになっていますが、./input/right_limit.gpkg が見つかりません。")
                
            gdf_right = gpd.read_file("./input/right_limit.gpkg", engine="pyogrio")
            right_lines = []
            for geom in gdf_right.geometry:
                if geom is None: continue
                if 'LineString' in geom.geom_type:
                    if 'Multi' in geom.geom_type:
                        for line in geom.geoms:
                            meter_pts = [self.transformer_to_meter.transform(x, y) for x, y in line.coords]
                            right_lines.append(LineString(meter_pts))
                    else:
                        meter_pts = [self.transformer_to_meter.transform(x, y) for x, y in geom.coords]
                        right_lines.append(LineString(meter_pts))
            
            if not right_lines:
                raise ValueError("right_limit.gpkg に有効な線データがありません。QGISで「レイヤの編集を保存」したか確認してください。")
            self.right_limit_line = linemerge(right_lines) if len(right_lines) > 1 else right_lines[0]

    def read_intermediate_result(self):
        try:
            with open("./output/intermediate_result.csv", "r") as fin:
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
        self.load_limit_lines_if_needed()

        for i_section in range(self.n_sections):
            if progress_callback:
                progress_callback(i_section, self.n_sections, "標高読み取り")
            
            if not self.use_intermediate_result[i_section]:
                distance_section = self.distance_between_sections * i_section
                for i in range(len(self.points) - 1):
                    if self.distance_accumulated[i+1] >= distance_section:
                        break

                self.centers[i_section, :] = self.points[i, :] + (distance_section - self.distance_accumulated[i]) * self.j_vector[i]

                if self.angle_adjusts[i_section] == 0.0:
                    direction_transverse = self.v_vector[i]
                else:
                    direction_transverse = self.rotate_vector(self.v_vector[i], self.centers[i_section, :], self.angle_adjusts[i_section])

                center_m = self.transformer_to_meter.transform(self.centers[i_section, 0], self.centers[i_section, 1])

                # ==================================
                # 右岸側の処理
                # ==================================
                section_topography_right = np.array([])
                
                if self.mode_right[i_section] == 1:
                    p_far_right = self.centers[i_section, :] + 10000.0 * direction_transverse
                    p_far_right_m = self.transformer_to_meter.transform(p_far_right[0], p_far_right[1])
                    ray_right = LineString([center_m, p_far_right_m])
                    inter_right = ray_right.intersection(self.right_limit_line)

                    # 確実な None と empty 回避
                    if inter_right is None or inter_right.is_empty:
                        raise ValueError(f"断面 {0.001 * self.distance_between_sections * i_section:.3f}k で右限界線と交差しません。QGISで限界線が十分な長さか確認してください。")
                    
                    dist_right = Point(center_m).distance(inter_right) if inter_right.geom_type == 'Point' else min([Point(center_m).distance(p) for p in inter_right.geoms])
                    
                    # 限界線が近すぎても探索範囲が0にならないように最低1を確保する
                    j_limit_right = max(1, int(dist_right / self.transverse_interval))

                    margin_j = int(self.margin / self.transverse_interval) + 5
                    top_right_elev = -9999.0
                    j_stake_right = 0

                    for j in range(j_limit_right + margin_j + 1):
                        current = self.centers[i_section, :] + j * self.transverse_interval * direction_transverse
                        if self.dem_types[i_section][1] == "1A":
                            elevation = dem1a.get_elevation(current[0], current[1])
                        else:
                            elevation = dem.get_elevation(current[0], current[1], self.dem_types[i_section][1])
                        
                        section_topography_right = np.append(section_topography_right, elevation)

                        if j <= j_limit_right and elevation != -9999.0 and elevation >= top_right_elev:
                            top_right_elev = elevation
                            j_stake_right = j
                            self.stakes_right[i_section, 0:2] = current
                            self.stakes_right[i_section, 2] = top_right_elev

                    # 有効な標高が見つからなかった（0,0に飛ぶ）場合の防波堤
                    if top_right_elev == -9999.0:
                        raise ValueError(f"断面 {0.001 * self.distance_between_sections * i_section:.3f}k の右岸で有効な標高データが見つかりません。限界線内に陸地（DEM）がないか、中心線に近すぎます。")

                else:
                    j = 0
                    top = bottom = elevation_previous = -9999.0

                    while True:
                        current = self.centers[i_section, :] + j * self.transverse_interval * direction_transverse
                        if section_topography_right.size == j:
                            if self.dem_types[i_section][1] == "1A":
                                elevation = dem1a.get_elevation(current[0], current[1])
                            else:
                                elevation = dem.get_elevation(current[0], current[1], self.dem_types[i_section][1])
                            section_topography_right = np.append(section_topography_right, elevation)
                        else:
                            elevation = section_topography_right[j]

                        if elevation != -9999.0:
                            if bottom == -9999.0 or elevation < bottom:
                                bottom = elevation
                            if elevation >= top:
                                top = elevation
                                self.stakes_right[i_section, 0:2] = current
                                self.stakes_right[i_section, 2] = top
                                j_stake_right = j

                            if top >= bottom + self.tol1s[i_section,1] and elevation <= top - self.tol2s[i_section,1] and abs(elevation - elevation_previous) <= self.tol3s[i_section,1] * self.transverse_interval:
                                break

                        if abs(j) * self.transverse_interval >= self.tol4s[i_section,1] or (bottom != -9999.0 and elevation - bottom >= self.tol5s[i_section,1]):
                            self.tol1s[i_section,1] *= self.adjust1
                            self.tol2s[i_section,1] = max(self.tol2s[i_section,1] * self.adjust2 - 0.1, 0.0)
                            self.tol3s[i_section,1] *= self.adjust3
                            if self.tol3s[i_section,1] >= 100.0:
                                raise ValueError(f"座標({self.centers[i_section,1]}N, {self.centers[i_section,0]}E)の右岸側の地形データが存在しません")
                            j = 0
                            top = bottom = elevation_previous = -9999.0
                        else:
                            elevation_previous = elevation
                            j += 1

                # ==================================
                # 左岸側の処理
                # ==================================
                section_topography_left = np.array([])
                
                if self.mode_left[i_section] == 1:
                    p_far_left = self.centers[i_section, :] - 10000.0 * direction_transverse
                    p_far_left_m = self.transformer_to_meter.transform(p_far_left[0], p_far_left[1])
                    ray_left = LineString([center_m, p_far_left_m])
                    inter_left = ray_left.intersection(self.left_limit_line)

                    # 確実な None と empty 回避
                    if inter_left is None or inter_left.is_empty:
                        raise ValueError(f"断面 {0.001 * self.distance_between_sections * i_section:.3f}k で左限界線と交差しません。QGISで限界線が十分な長さか確認してください。")
                    
                    dist_left = Point(center_m).distance(inter_left) if inter_left.geom_type == 'Point' else min([Point(center_m).distance(p) for p in inter_left.geoms])
                    
                    # 限界線が近すぎても探索範囲が0にならないように最低1を確保する
                    j_limit_left = max(1, int(dist_left / self.transverse_interval))

                    margin_j = int(self.margin / self.transverse_interval) + 5
                    top_left_elev = -9999.0
                    j_stake_left = 0

                    for j in range(-1, -(j_limit_left + margin_j + 1) - 1, -1):
                        current = self.centers[i_section, :] + j * self.transverse_interval * direction_transverse
                        if self.dem_types[i_section][0] == "1A":
                            elevation = dem1a.get_elevation(current[0], current[1])
                        else:
                            elevation = dem.get_elevation(current[0], current[1], self.dem_types[i_section][0])
                        
                        section_topography_left = np.append(section_topography_left, elevation)

                        if abs(j) <= j_limit_left and elevation != -9999.0 and elevation >= top_left_elev:
                            top_left_elev = elevation
                            j_stake_left = j
                            self.stakes_left[i_section, 0:2] = current
                            self.stakes_left[i_section, 2] = top_left_elev

                    # 有効な標高が見つからなかった（0,0に飛ぶ）場合の防波堤
                    if top_left_elev == -9999.0:
                        raise ValueError(f"断面 {0.001 * self.distance_between_sections * i_section:.3f}k の左岸で有効な標高データが見つかりません。限界線内に陸地（DEM）がないか、中心線に近すぎます。")
                else:
                    j = -1
                    top = bottom = elevation_previous = -9999.0

                    while True:
                        current = self.centers[i_section, :] + j * self.transverse_interval * direction_transverse
                        if section_topography_left.size == -j-1:
                            if self.dem_types[i_section][0] == "1A":
                                elevation = dem1a.get_elevation(current[0], current[1])
                            else:
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

                section_topography_left = section_topography_left[::-1]
                section_topography = np.append(section_topography_left, section_topography_right)
                j_stake_right += len(section_topography_left)
                j_stake_left += len(section_topography_left)
                
                self.js_center[i_section] = len(section_topography_left)
                self.js_stake_right[i_section] = j_stake_right
                self.js_stake_left[i_section] = j_stake_left
                
                self.sections_topography[i_section] = section_topography
                self.use_intermediate_result[i_section] = 1
    
    def export_intermediate_result(self):
        if not os.path.exists("./output"):
            os.makedirs("./output")

        with open("./output/intermediate_result.csv", "w", newline="") as fout:
            writer = csv.writer(fout)
            for i_section in range(self.n_sections):
                row = [
                    self.centers[i_section, 0], self.centers[i_section, 1],
                    self.stakes_right[i_section, 0], self.stakes_right[i_section, 1], self.stakes_right[i_section, 2],
                    self.stakes_left[i_section, 0], self.stakes_left[i_section, 1], self.stakes_left[i_section, 2],
                    self.js_stake_right[i_section], self.js_stake_left[i_section], self.js_center[i_section],
                    len(self.sections_topography[i_section])
                ]
                row += self.sections_topography[i_section].tolist()
                writer.writerow(row)
    
    def rotate_crossed_lines(self):
        centers_meter = np.zeros((self.n_sections, 2))
        stakes_right_meter = np.zeros((self.n_sections, 2))
        stakes_left_meter = np.zeros((self.n_sections, 2))
        rotated = np.zeros(self.n_sections, dtype=int)

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

            if selected_i_section1 == -1:
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
            self.use_intermediate_result[i_section1] = 0
            self.use_intermediate_result[i_section2] = 0

        return np.any(rotated)

    def calculate_water_surface(self):
        self.widths_river = np.zeros(self.n_sections)
        self.elevations_water_tmp = np.zeros(self.n_sections)

        for i_section in range(self.n_sections):
            section_topography = self.sections_topography[i_section]
            j_right = self.js_stake_right[i_section]
            j_left = self.js_stake_left[i_section]
            segment = section_topography[j_left:j_right+1]
            
            if self.wsts[i_section] == 0.0:
                min_elevation = np.min(segment)
                if min_elevation == -9999.0:
                    self.widths_river[i_section] = np.count_nonzero(segment == -9999.0) * self.transverse_interval
                    self.elevations_water_tmp[i_section] = np.min(segment[segment != -9999.0])
                else:
                    self.widths_river[i_section] = np.count_nonzero(segment <= min_elevation + self.water_surface_tolerance) * self.transverse_interval
                    self.elevations_water_tmp[i_section] = min_elevation
            else:
                self.widths_river[i_section] = np.count_nonzero(segment <= min_elevation + self.wsts[i_section]) * self.transverse_interval
                self.elevations_water_tmp[i_section] = min_elevation
        
        self.elevations_water = np.zeros(self.n_sections)
        
        for i in range(self.n_sections):
            r = min(self.n_samples_for_median_water_surface // 2, i, self.n_sections - 1 - i)
            self.elevations_water[i] = np.median(self.elevations_water_tmp[i - r:i + r + 1])
        
        for i in range(self.n_sections - 2, -1, -1):
            self.elevations_water[i] = min(
                self.elevations_water[i],
                self.elevations_water[i + 1] - self.minimum_slope_water * self.distance_between_sections
            )

        self.slopes_water = np.zeros(self.n_sections)
        self.slopes_water[self.n_sections - 1] = self.minimum_slope_water
        for i in range(self.n_sections - 1):
            self.slopes_water[i] = (
                self.elevations_water[i + 1] - self.elevations_water[i]
            ) / self.distance_between_sections

    def calculate_riverbed(self, progress_callback=None):
        self.depths = np.zeros(self.n_sections)
        self.elevations_riverbed_tmp = np.zeros(self.n_sections)
        
        if self.estimate_water_depth:
            for i in range(self.n_sections - 1, -1, -1):
                if progress_callback:
                    progress_callback(self.n_sections - 1 - i, self.n_sections, "河床標高計算")
    
                if i == self.n_sections - 1:
                    self.depths[i] = (self.flows[i] * self.roughness / (self.widths_river[i] * np.sqrt(self.slopes_water[i]))) ** (3.0 / 5.0)
                else:
                    self.depths[i] = open_channel.find_depth(
                        self.depths[i + 1], self.flows[i + 1],
                        self.widths_river[i], self.widths_river[i + 1],
                        self.slopes_water[i], self.distance_between_sections,
                        int(self.distance_between_sections / self.difference_in_differential_equation + 0.5),
                        self.roughness
                    )
        
        self.elevations_riverbed_tmp[:] = self.elevations_water[:] - self.depths[:]
        self.elevations_riverbed = np.zeros(self.n_sections)
        
        for i in range(self.n_sections):
            r = min(self.n_samples_for_median_riverbed // 2, i, self.n_sections - 1 - i)
            self.elevations_riverbed[i] = np.median(self.elevations_riverbed_tmp[i - r:i + r + 1])
        
        for i in range(self.n_sections):
            section_topography = self.sections_topography[i]
            j_left = self.js_stake_left[i]
            j_right = self.js_stake_right[i]
            
            if self.wsts[i] == 0.0:
                min_elevation = np.min(section_topography[j_left:j_right+1])
                if min_elevation == -9999.0:
                    section_topography[j_left:j_right+1] = np.fmax(
                        section_topography[j_left:j_right+1],
                        self.elevations_riverbed[i]
                    )
                else:
                    mask = section_topography[j_left:j_right+1] <= min_elevation + self.water_surface_tolerance
                    section_topography[j_left:j_right+1][mask] = self.elevations_riverbed[i]
            else:
                mask = section_topography[j_left:j_right+1] <= min_elevation + self.wsts[i]
                section_topography[j_left:j_right+1][mask] = self.elevations_riverbed[i]
            
            section_topography[j_left:j_right+1] = np.fmax(
                section_topography[j_left:j_right+1],
                self.elevations_riverbed[i]
            )

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
                    self.js_center[i] -= j + 1
                    self.js_stake_right[i] -= j + 1
                    self.js_stake_left[i] -= j + 1
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
            fout.write("Distance,Riverbed,Raw riverbed,Water surface,Raw water surface,Stake left,Stake right\n")
            for i in range(self.n_sections):
                fout.write(f"{0.001 * self.distance_between_sections * i},{self.elevations_riverbed[i]},{self.elevations_riverbed_tmp[i]},{self.elevations_water[i]},{self.elevations_water_tmp[i]},{self.stakes_left[i,2]},{self.stakes_right[i,2]}\n")

        # ==================================
        # GPKG出力部分 (None を -9999.0 に修正済み)
        # ==================================
        data = []
    
        left_bank_coords = [(self.stakes_left[i,0], self.stakes_left[i,1]) for i in range(self.n_sections)]
        data.append({
            'name': 'Left',
            'left_bank': 0.0,
            'right_bank': 0.0,
            'riverbed': 0.0,
            'geometry': LineString(left_bank_coords)
        })
    
        right_bank_coords = [(self.stakes_right[i,0], self.stakes_right[i,1]) for i in range(self.n_sections)]
        data.append({
            'name': 'Right',
            'left_bank': 0.0,
            'right_bank': 0.0,
            'riverbed': 0.0,
            'geometry': LineString(right_bank_coords)
        })
    
        for i in range(self.n_sections):
            dlon = (self.stakes_right[i,0] - self.stakes_left[i,0]) / (self.js_stake_right[i] - self.js_stake_left[i])
            dlat = (self.stakes_right[i,1] - self.stakes_left[i,1]) / (self.js_stake_right[i] - self.js_stake_left[i])
            start = (self.stakes_left[i,0] + (0 - self.js_stake_left[i]) * dlon, self.stakes_left[i,1] + (0 - self.js_stake_left[i]) * dlat)
            end = (self.stakes_left[i,0] + (len(self.sections_topography[i]) - 1 - self.js_stake_left[i]) * dlon, self.stakes_left[i,1] + (len(self.sections_topography[i]) - 1 - self.js_stake_left[i]) * dlat)
            
            data.append({
                'name': f"{0.001 * self.distance_between_sections * i:.3f}k",
                'left_bank': round(self.stakes_left[i,2], 3),
                'right_bank': round(self.stakes_right[i,2], 3),
                'riverbed': round(self.elevations_riverbed[i], 3),
                'geometry': LineString([start, end])
            })
            
        gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
        gdf.to_file("./output/river_channel.gpkg", driver="GPKG", engine="pyogrio")
    
    def run(self, progress_callback=None):
        # 抽出を実行するたびに、限界線のメモリ(キャッシュ)を強制的にリセットする
        self.left_limit_line = None
        self.right_limit_line = None
        
        self.read_setting()
        self.read_intermediate_result()
        
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
