# -*- coding: utf-8 -*-

import numpy as np

gravitational_acceleration = 9.80665

def find_depth(depth_up, flow, width_river_down, width_river_up, slope_water, distance_between_sections, n_divisions, roughness):
    delta_width_river = (width_river_up - width_river_down) / n_divisions
    depth_plus = depth_up
    width_river_plus = width_river_up
    for i_division in range(n_divisions):
        width_river_minus = width_river_plus - delta_width_river
        
        right_hand_side = slope_water * distance_between_sections / n_divisions + 0.5 * np.power( flow / (width_river_plus * depth_plus), 2 ) * (1.0 / gravitational_acceleration - roughness * roughness * distance_between_sections / n_divisions / np.power(depth_plus, 4.0 / 3.0) )
        if right_hand_side <= 0.0:
            raise ValueError("difference_in_differential_equationの設定値が大き過ぎます")
        
        depth_down = depth_plus
        error_prev = 1.0e100
        
        left_hand_side_1 = 0.5 * np.power( flow / (width_river_minus * depth_down), 2 ) / gravitational_acceleration
        left_hand_side_2 = 0.5 * distance_between_sections / n_divisions * np.power( roughness * flow / width_river_minus, 2 ) / np.power(depth_down, 10.0 / 3.0)
        error = left_hand_side_1 + left_hand_side_2 - right_hand_side
        
        while True:
            if abs(error) <= 1.0e-7 and abs(error) >= abs(error_prev) * (1.0 - 1.0e-7):
                break
            else:
                d_left_hand_side_1_d_depth_down = - 2.0 * left_hand_side_1 / depth_down
                d_left_hand_side_2_d_depth_down = - 10.0 / 3.0 * left_hand_side_2 / depth_down
                d_error_d_depth_down = d_left_hand_side_1_d_depth_down + d_left_hand_side_2_d_depth_down
                delta_depth_down = - error / d_error_d_depth_down
                
                while depth_down + delta_depth_down <= 0.0:
                    delta_depth_down *= 0.5
                
                depth_down_prev = depth_down
                error_prev = error
                while True:
                    depth_down = depth_down_prev + delta_depth_down
                    left_hand_side_1 = 0.5 * np.power( flow / (width_river_minus * depth_down), 2 ) / gravitational_acceleration
                    left_hand_side_2 = 0.5 * distance_between_sections / n_divisions * np.power( roughness * flow / width_river_minus, 2 ) / np.power(depth_down, 10.0 / 3.0)
                    error = left_hand_side_1 + left_hand_side_2 - right_hand_side
                    if abs(error) <= abs(error_prev):
                        break
                    else:
                        delta_depth_down *= 0.5
        
        depth_plus = depth_down
        width_river_plus = width_river_minus
    
    return depth_down