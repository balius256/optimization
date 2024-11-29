# 必要なライブラリのインポート
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpStatus, value, SCIP_CMD, PULP_CBC_CMD
import numpy as np
import random
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 問題の定義
prob = LpProblem("Shift_Scheduling", LpMaximize)

# パラメータの設定
N = 9   # 従業員数
T = 30  # 日数
M = 1   # 月数

# インデックスの定義
I = range(1, N+1)        # 従業員のインデックス
T_range = range(1, T+1)  # 日数のインデックス
T_range_minus_1 = range(1, T)  # T-1日まで
M_range = range(1, M+1)  # 月数のインデックス

# 週の定義
Weeks = [1, 2, 3, 4, 5]
Week_days = {
    1: list(range(1, 8)),
    2: list(range(8, 15)),
    3: list(range(15, 22)),
    4: list(range(22, 29)),
    5: list(range(29, 31))
}

# 労働時間関連のパラメータ
H_std = 7.75
H_max = 12
shift_length = 8.5
I_min = 11

# 週の労働時間上限
H_week_max = 38.75  # 週の労働時間上限を48時間に調整

# シフト開始時刻
s_day_start = 8.5
s_night_start = 20.5

# コスト関連のパラメータ
C_normal = 1000
C_overtime = 1.30 * C_normal
C_night = 1.20 * C_normal
C_night_overtime = 1.30 * C_night

# 製品の単価
np.random.seed(0)
S_t_array = np.random.uniform(4000, 6000, T+1)  # インデックスを1から始めるためにサイズをT+1に
S_t_array[0] = 0  # ダミーの0番目の要素
S_t = {t: S_t_array[t] for t in T_range}

# 従業員の生産性
p_i = {i: 1.0 + random.uniform(-0.3, 0.3) for i in I}

# シフトごとの従業員数の上限・下限
E_min_day = 3
E_max_day = 5
E_min_night = 3
E_max_night = 5

# 36協定関連のパラメータ
O_annual = 360  # 年間時間外労働時間の上限
O_annual_special = 720  # 年間時間外労働時間の上限（特別条項あり）
O_max = 80  # 月間時間外労働時間の上限
O_max_special = 100  # 月間時間外労働時間の上限（特別条項あり）
M_over = 6  # 年間で45時間超過可能な月数の上限
M_past = 0  # 過去の月数

# その他のパラメータ
v_it = {(i, t): 0 for i in I for t in T_range}  # 年休取得フラグ
e_i = {i: 0 for i in I}  # 特別条項付き協定フラグ

# ビッグMの設定
Big_M = 10*H_max  # H_max = 12

# 変数の定義
h = LpVariable.dicts("h", (I, T_range), lowBound=0, upBound=H_max)
r = LpVariable.dicts("r", (I, T_range), lowBound=0, upBound=H_max - H_std)
d = LpVariable.dicts("d", (I, T_range), cat='Binary')
n = LpVariable.dicts("n", (I, T_range), cat='Binary')
w = LpVariable.dicts("w", (I, T_range), cat='Binary')
s_start = LpVariable.dicts("s_start", (I, T_range), lowBound=0, upBound=24)
s_end = LpVariable.dicts("s_end", (I, T_range), lowBound=0, upBound=48)
delta = LpVariable.dicts("delta", (I, T_range_minus_1), cat='Binary')
f = LpVariable.dicts("f", (I, T_range), lowBound=0)
g = LpVariable.dicts("g", (I, T_range), lowBound=0)
o = LpVariable.dicts("o", (I, M_range), lowBound=0)
s_var = LpVariable.dicts("s_var", (I, M_range), cat='Binary')

# 目的関数の定義
revenue = lpSum([S_t[t] * lpSum([p_i[i] * h[i][t] for i in I]) for t in T_range])
normal_pay = C_normal * lpSum([h[i][t] - r[i][t] for i in I for t in T_range])
overtime_pay = C_overtime * lpSum([r[i][t] for i in I for t in T_range])
night_pay = C_night * lpSum([f[i][t] for i in I for t in T_range])
night_overtime_pay = C_night_overtime * lpSum([g[i][t] for i in I for t in T_range])

prob += revenue - (normal_pay + overtime_pay + night_pay + night_overtime_pay)

# 制約条件の定義

# 1. シフト割り当ての制約
for i in I:
    for t in T_range:
        # 1.1 一日一シフト制約
        prob += d[i][t] + n[i][t] <= 1

        # 1.2 勤務日判定
        prob += w[i][t] == d[i][t] + n[i][t]

        # 1.3 年休取得日のシフト制限
        prob += d[i][t] <= 1 - v_it[(i, t)]
        prob += n[i][t] <= 1 - v_it[(i, t)]

# 2. シフトごとの従業員数の上限・下限
for t in T_range:
    # 2.1 昼勤の従業員数制約
    prob += lpSum([d[i][t] for i in I]) >= E_min_day
    prob += lpSum([d[i][t] for i in I]) <= E_max_day

    # 2.2 夜勤の従業員数制約
    prob += lpSum([n[i][t] for i in I]) >= E_min_night
    prob += lpSum([n[i][t] for i in I]) <= E_max_night

# 3. 勤務時間と時間外労働時間の関係
for i in I:
    for t in T_range:
        # 3.1 勤務時間の定義
        prob += h[i][t] == H_std * w[i][t]  + r[i][t]

        # 3.2 労働時間の上限
        prob += h[i][t] <= H_max * w[i][t] 

        # 3.3 時間外労働時間の上限
        prob += r[i][t] <= (H_max - H_std) * w[i][t] 

# 4. 勤務開始・終了時刻の制約
for i in I:
    for t in T_range:
        # 4.1 勤務開始時刻の定義
        prob += s_start[i][t] == s_day_start * d[i][t] + s_night_start * n[i][t]

        # 4.2 勤務終了時刻の定義
        prob += s_end[i][t] == s_start[i][t] + shift_length * w[i][t] 

# 5. 勤務間インターバル制約
for i in I:
    for t in T_range_minus_1:
        # 5.1 最低休息時間の確保
        prob += s_start[i][t] - s_end[i][t] + 24 * delta[i][t] >= I_min

        # 5.2 日付跨ぎの判定
        prob += delta[i][t] >= n[i][t] + d[i][t] - 1

# 6. 労働時間の週次制約
for i in I:
    for week in Weeks:
        prob += lpSum([h[i][t] for t in Week_days[week] if t in T_range]) <= H_week_max

# 7. 時間外労働時間の計算
for i in I:
    for m in M_range:
        prob += o[i][m] == lpSum([r[i][t] for t in T_range])

# 8. 36協定および特別条項に基づく制約
for i in I:
    total_overtime = lpSum([o[i][m] for m in M_range])
    if e_i[i] == 0:
        prob += total_overtime <= O_annual
    else:
        prob += total_overtime <= O_annual_special

    for m in M_range:
        if e_i[i] == 0:
            prob += o[i][m] <= O_max
        else:
            prob += o[i][m] <= O_max_special

# 9. 月45時間超過月の回数制限
for i in I:
    for m in M_range:
        prob += o[i][m] - O_max <= (O_max_special - O_max) * s_var[i][m]

    prob += lpSum([s_var[i][m] for m in M_range]) <= M_over

# 10. 夜勤に関する補助変数の制約（修正）
for i in I:
    for t in T_range:
        # 10.1 夜勤の通常労働時間の線形化
        prob += f[i][t] >= (h[i][t] - r[i][t]) - Big_M * (1 - n[i][t])
        prob += f[i][t] <= h[i][t] - r[i][t]
        prob += f[i][t] <= Big_M * n[i][t]
        prob += f[i][t] >= 0

        # 10.2 夜勤の時間外労働時間の線形化
        prob += g[i][t] >= r[i][t] - Big_M * (1 - n[i][t])
        prob += g[i][t] <= r[i][t]
        prob += g[i][t] <= Big_M * n[i][t]
        prob += g[i][t] >= 0

solver = SCIP_CMD("C:\\Program Files\\SCIPOptSuite 9.1.0\\bin\\scip.exe")

# 問題の解決
prob.solve(solver)

# 結果の収集
results = []

for i in I:
    for t in T_range:
        if value(d[i][t]) == 1:
            shift = '昼勤務'
        elif value(n[i][t]) == 1:
            shift = '夜勤務'
        else:
            shift = '休み'
        labor_hours = value(h[i][t])
        overtime_hours = value(r[i][t])
        results.append({
            '従業員ID': i,
            '従業員名': f'従業員{i}',
            '日付': t,
            'シフト': shift,
            '労働時間': labor_hours,
            '時間外労働時間': overtime_hours
        })

# データフレームに変換
df_results = pd.DataFrame(results)

# CSVに出力
df_results.to_csv('shift_schedule.csv', index=False, encoding='utf-8-sig')

# 勤務表として可視化

# フォントの設定（Windows環境に合わせて修正）
plt.rcParams['font.family'] = 'Meiryo'  # または 'Yu Gothic'

pivot_table = df_results.pivot(index='従業員名', columns='日付', values='シフト')

# 可視化のためのマッピング
shift_mapping = {'昼勤務': 1, '夜勤務': 2, '休み': 0}
pivot_table_numeric = pivot_table.replace(shift_mapping)

plt.figure(figsize=(20, 6))
sns.heatmap(pivot_table_numeric, annot=pivot_table, fmt='', cmap='YlGnBu', cbar=False)
plt.title('勤務表')
plt.xlabel('日付')
plt.ylabel('従業員名')
plt.tight_layout()

# 可視化結果をファイルに出力
plt.savefig('shift_schedule.png')

# 結果の表示
print("Status:", LpStatus[prob.status])

for i in I:
    print(f'従業員 {i}: 生産性 {p_i[i]:.2f}')
    for t in T_range:
        shift = '休み'
        if value(d[i][t]) == 1:
            shift = '昼勤務'
        elif value(n[i][t]) == 1:
            shift = '夜勤務'
        if shift == '休み':
            labor_hours = 0.00
            overtime_hours = 0.00
        else:
            labor_hours = value(h[i][t])
            overtime_hours = value(r[i][t])
        print(f'  日 {t}: {shift}, 労働時間: {labor_hours:.2f} 時間, 時間外: {overtime_hours:.2f} 時間')
    print('-----------------------------------')

print(f'総利益: {value(prob.objective):.2f} 円')
