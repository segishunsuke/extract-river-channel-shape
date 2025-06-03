# -*- coding: utf-8 -*-
import numpy as np

"""
center1, center2, stake1, stake2は全て2次元ベクトル
center1-stake1を結ぶ線分と，center2-stake2を結ぶ線分が交差するかどうかを判定する
交差する場合には，交差の解消に必要となる線分の回転角の余弦のうち，小さい方を返す
ここで，交差の解消は，線分stake1-stake2の75%分位点に新しいstake1が，25%分位点に新しいstake2が来るように行うものとする
交差しない場合には，1.0を返す
"""
def min_cos_angle_adjustment(center1, center2, stake1, stake2):
    vector1 = stake1 - center1
    vector2 = stake2 - center2
    outer1 = vector1[0] * (center2[1] - center1[1]) - vector1[1] * (center2[0] - center1[0])
    outer2 = vector1[0] * (stake2[1] - center1[1]) - vector1[1] * (stake2[0] - center1[0])
    outer3 = vector2[0] * (center1[1] - center2[1]) - vector2[1] * (center1[0] - center2[0])
    outer4 = vector2[0] * (stake1[1] - center2[1]) - vector2[1] * (stake1[0] - center2[0])
    if outer1 * outer2 <= 0.0 and outer3 * outer4 <= 0.0: # stake1-stake2の手前（もしくはその上）で交差している
        stake1_dash = stake1 + 0.75 * (stake2 - stake1) # 回転後のstake1
        stake2_dash = stake1 + 0.25 * (stake2 - stake1) # 回転後のstake2
        vector1_dash = stake1_dash - center1
        vector2_dash = stake2_dash - center2
        cos1 = np.dot(vector1, vector1_dash) / ( np.linalg.norm(vector1) * np.linalg.norm(vector1_dash) )
        cos2 = np.dot(vector2, vector2_dash) / ( np.linalg.norm(vector2) * np.linalg.norm(vector2_dash) )
        return min(cos1, cos2)
    else:
        return 1.0

"""
center1, center2, stake1, stake2, ostake1, ostake2は全て2次元ベクトル
center1-stake1を結ぶ線分と，center2-stake2を結ぶ線分は交差しなければいけない
ostake1は線分center1-stake1をcenter1側に延長した先に存在する点でなければいけない
ostake2は線分center2-stake2をcenter2側に延長した先に存在する点でなければいけない
以下の値を返す
center1-stake1を結ぶ線分と，center2-stake2を結ぶ線分の交差を解消するような，回転角angle1, angle2
回転後のstake1とstake2の位置，stake1_dash, stake2_dash
回転後のostake1とostake2の位置，ostake1_dash, ostake2_dash
ここで，交差の解消は，線分stake1-stake2の75%分位点に新しいstake1が，25%分位点に新しいstake2が来るように行うものとする
ostake1_dash, ostake2_dashは，直線ostake1-ostake2上に存在するように取る
"""
def angle_adjustment(center1, center2, stake1, stake2, ostake1, ostake2):
    vector1 = stake1 - center1
    vector2 = stake2 - center2
    stake1_dash = stake1 + 0.75 * (stake2 - stake1) # 回転後のstake1
    stake2_dash = stake1 + 0.25 * (stake2 - stake1) # 回転後のstake2
    vector1_dash = stake1_dash - center1
    vector2_dash = stake2_dash - center2
    sin1 = np.cross(vector1, vector1_dash) / ( np.linalg.norm(vector1) * np.linalg.norm(vector1_dash) )
    sin2 = np.cross(vector2, vector2_dash) / ( np.linalg.norm(vector2) * np.linalg.norm(vector2_dash) )
    angle1 = np.arcsin(sin1)
    angle2 = np.arcsin(sin2)
    
    """
    媒介変数表示の直線 t * ostake1 + (1 - t) * ostake2 と s * center + (1 - s) * stake の交点を求める
    s, tを変数とする二元連立方程式をnp.linalg.solveで解く
    x[0]がtを，x[1]がsを表す
    """
    A = np.zeros((2,2))
    b = np.zeros(2)
    A[:,0] = ostake1[:] - ostake2[:]
    
    A[:,1] = stake1_dash[:] - center1[:]
    b[:] = stake1_dash[:] - ostake2[:]
    x = np.linalg.solve(A, b)
    ostake1_dash = x[0] * ostake1 + (1.0 - x[0]) * ostake2
    
    
    A[:,1] = stake2_dash[:] - center2[:]
    b[:] = stake2_dash[:] - ostake2[:]
    x = np.linalg.solve(A, b)
    ostake2_dash = x[0] * ostake1 + (1.0 - x[0]) * ostake2
    
    return angle1, angle2, stake1_dash, stake2_dash, ostake1_dash, ostake2_dash


"""
以下は動作確認用のコード
"""
"""
import matplotlib.pyplot as plt

center1 = np.array([0.25, 0.5])
center2 = np.array([0.75, 0.5])
stake1 = np.array([np.random.rand(), 0.5+0.5*np.random.rand()])
stake2 = np.array([np.random.rand(), 0.5+0.5*np.random.rand()])

t1 = center1[1] / (stake1[1] - center1[1])
t2 = center1[0] / (stake1[0] - center1[0])
if t2 <= 0.0:
    t2 = 1.0e100
t3 = (center1[0] - 1.0) / (stake1[0] - center1[0])
if t3 <= 0.0:
    t3 = 1.0e100
t = min(t1, t2, t3)
ostake1 = center1 - t * (stake1 - center1) * np.random.rand()

t1 = center2[1] / (stake2[1] - center2[1])
t2 = center2[0] / (stake2[0] - center2[0])
if t2 <= 0.0:
    t2 = 1.0e100
t3 = (center2[0] - 1.0) / (stake2[0] - center2[0])
if t3 <= 0.0:
    t3 = 1.0e100
t = min(t1, t2, t3)
ostake2 = center2 - t * (stake2 - center2) * np.random.rand()

# 左岸と右岸を反転
#stake1[1] = 0.5 - (stake1[1] - 0.5)
#stake2[1] = 0.5 - (stake2[1] - 0.5)
#ostake1[1] = 0.5 - (ostake1[1] - 0.5)
#ostake2[1] = 0.5 - (ostake2[1] - 0.5)

g = plt.subplot()
g.set_ylim([0,1])
g.set_xlim([0,1])
g.set_aspect('equal')

plt.plot(center1[0], center1[1], marker='o', color = "blue")
plt.plot(center2[0], center2[1], marker='o', color = "blue")

plt.plot(stake1[0], stake1[1], marker='^', color = "blue")
plt.plot(stake2[0], stake2[1], marker='^', color = "blue")

plt.plot(ostake1[0], ostake1[1], marker='s', color = "blue")
plt.plot(ostake2[0], ostake2[1], marker='s', color = "blue")

plt.plot([ostake1[0], stake1[0]], [ostake1[1], stake1[1]], color = "blue")
plt.plot([ostake2[0], stake2[0]], [ostake2[1], stake2[1]], color = "blue")

cos = min_cos_angle_adjustment(center1, center2, stake1, stake2)

if cos == 1.0:
    print(0.0)
else:
    print(np.arccos(cos) * 180.0 / np.pi)
    angle1, angle2, stake1_dash, stake2_dash, ostake1_dash, ostake2_dash = angle_adjustment(center1, center2, stake1, stake2, ostake1, ostake2)
    print(angle1 * 180.0 / np.pi, angle2 * 180.0 / np.pi)
    
    plt.plot(stake1_dash[0], stake1_dash[1], marker='^', color = "red")
    plt.plot(stake2_dash[0], stake2_dash[1], marker='^', color = "red")

    plt.plot(ostake1_dash[0], ostake1_dash[1], marker='s', color = "red")
    plt.plot(ostake2_dash[0], ostake2_dash[1], marker='s', color = "red")
    
    plt.plot([ostake1_dash[0], stake1_dash[0]], [ostake1_dash[1], stake1_dash[1]], color = "red")
    plt.plot([ostake2_dash[0], stake2_dash[0]], [ostake2_dash[1], stake2_dash[1]], color = "red")
"""