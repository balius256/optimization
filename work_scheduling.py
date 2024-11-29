# 必要なライブラリのインポート
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, LpContinuous, value, LpStatus
import numpy as np
import random

# 問題の定義
prob = LpProblem("Shift_Scheduling", LpMaximize)

# パラメータの設定
N = 9   # 従業員数
T = 30  # 日数
M = 1   # 月数

# インデックスの定義
I = range(1, N+1)        # 従業員のインデックス
T_range = range(1, T+1)  # 日数のインデックス
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
H_week_max = 48  # 週の労働時間上限を48時間に調整

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
# 生産性 p_i を ±30% の範囲でランダムに設定
p_i = {i: 1.0 + random.uniform(-0.3, 0.3) for i in I}

# シフトごとの従業員数の上限・下限
E_min_day = 3
E_max_day = 5  
E_min_night = 3
E_max_night = 5  

# 36協定関連のパラメータ
O_annual = 360  # 年間時間外労働時間の上限（仮の値）
O_annual_special = 720  # 年間時間外労働時間の上限（特別条項あり）
O_max = 80  # 月間時間外労働時間の上限を80時間に緩和（法定内で）
O_max_special = 100  # 月間時間外労働時間の上限（特別条項あり）
M_over = 6  # 年間で45時間超過可能な月数の上限
M_past = 0  # 過去の月数

# その他のパラメータ
Big_M = H_max * 2  # Big_Mを十分大きな値に設定
v_it = {(i, t): 0 for i in I for t in T_range}  # 年休取得フラグ
e_i = {i: 0 for i in I}  # 特別条項付き協定フラグ
O_i_m_hist = {}  # 過去の時間外労働時間
s_i_m_hist = {}  # 過去の45時間超過フラグ

# 変数の定義
h = LpVariable.dicts("h", [(i, t) for i in I for t in T_range], lowBound=0, cat=LpContinuous)
r = LpVariable.dicts("r", [(i, t) for i in I for t in T_range], lowBound=0, cat=LpContinuous)
d = LpVariable.dicts("d", [(i, t) for i in I for t in T_range], cat=LpBinary)
n = LpVariable.dicts("n", [(i, t) for i in I for t in T_range], cat=LpBinary)
w = LpVariable.dicts("w", [(i, t) for i in I for t in T_range], cat=LpBinary)
s_start = LpVariable.dicts("s_start", [(i, t) for i in I for t in T_range], lowBound=0, cat=LpContinuous)
s_end = LpVariable.dicts("s_end", [(i, t) for i in I for t in T_range], lowBound=0, cat=LpContinuous)
f = LpVariable.dicts("f", [(i, t) for i in I for t in T_range], lowBound=0, cat=LpContinuous)
g = LpVariable.dicts("g", [(i, t) for i in I for t in T_range], lowBound=0, cat=LpContinuous)
delta = LpVariable.dicts("delta", [(i, t) for i in I for t in T_range], cat=LpBinary)
o = LpVariable.dicts("o", [(i, m) for i in I for m in M_range], lowBound=0, cat=LpContinuous)
s_var = LpVariable.dicts("s", [(i, m) for i in I for m in M_range], cat=LpBinary)

# 目的関数の定義
revenue = lpSum([S_t[t] * lpSum([p_i[i] * h[(i, t)] for i in I]) for t in T_range])
normal_pay = C_normal * lpSum([h[(i, t)] - r[(i, t)] for i in I for t in T_range])
overtime_pay = C_overtime * lpSum([r[(i, t)] for i in I for t in T_range])
night_pay = C_night * lpSum([f[(i, t)] for i in I for t in T_range])
night_overtime_pay = C_night_overtime * lpSum([g[(i, t)] for i in I for t in T_range])

prob += revenue - (normal_pay + overtime_pay + night_pay + night_overtime_pay)

# 制約条件の定義

# 1. シフト割り当ての制約
for i in I:
    for t in T_range:
        # 一日一シフト制約
        prob += d[(i, t)] + n[(i, t)] <= 1

        # 勤務日判定
        prob += w[(i, t)] == d[(i, t)] + n[(i, t)]

        # 年休取得日のシフト制限
        prob += d[(i, t)] <= 1 - v_it[(i, t)]
        prob += n[(i, t)] <= 1 - v_it[(i, t)]

# シフトごとの従業員数の上限・下限
for t in T_range:
    prob += lpSum([d[(i, t)] for i in I]) >= E_min_day
    prob += lpSum([d[(i, t)] for i in I]) <= E_max_day
    prob += lpSum([n[(i, t)] for i in I]) >= E_min_night
    prob += lpSum([n[(i, t)] for i in I]) <= E_max_night

# 2. 勤務時間と時間外労働時間の関係
for i in I:
    for t in T_range:
        # 勤務時間の定義
        prob += h[(i, t)] == H_std * w[(i, t)] + r[(i, t)]
        # 勤務していない場合、労働時間と時間外労働時間はゼロ
        prob += h[(i, t)] <= H_max * w[(i, t)]
        prob += r[(i, t)] <= (H_max - H_std) * w[(i, t)]
        prob += r[(i, t)] >= 0

# 3. 勤務開始・終了時刻の制約
for i in I:
    for t in T_range:
        # 勤務開始時刻の定義
        prob += s_start[(i, t)] == s_day_start * d[(i, t)] + s_night_start * n[(i, t)]

        # 勤務終了時刻の定義
        prob += s_end[(i, t)] == s_start[(i, t)] + shift_length * w[(i, t)]

# 4. 勤務間インターバル制約
for i in I:
    for t in T_range:
        if t < T:
            # 最低休息時間の確保
            prob += s_start[(i, t+1)] - s_end[(i, t)] + 24 * delta[(i, t)] >= I_min

            # 日付跨ぎの判定
            prob += delta[(i, t)] >= n[(i, t)] + d[(i, t+1)] - 1

# 5. 労働時間の週次制約（週の労働時間上限を設定）
for i in I:
    for week in Weeks:
        days = Week_days[week]
        prob += lpSum([h[(i, t)] for t in days]) <= H_week_max

# 6. 時間外労働時間の計算
for i in I:
    for m in M_range:
        if m >= M_past + 1:
            # ここでは、全ての勤務日を対象とします
            prob += o[(i, m)] == lpSum([r[(i, t)] for t in T_range])

# 7. 36協定および特別条項に基づく制約
for i in I:
    total_overtime = lpSum([o[(i, m)] for m in M_range])
    if e_i[i] == 0:
        prob += total_overtime <= O_annual
    else:
        prob += total_overtime <= O_annual_special

    for m in M_range:
        if m >= M_past + 1:
            if e_i[i] == 0:
                prob += o[(i, m)] <= O_max
            else:
                prob += o[(i, m)] <= O_max_special

# 8. 月45時間超過月の回数制限
for i in I:
    for m in M_range:
        if m >= M_past + 1:
            prob += o[(i, m)] - O_max <= (O_max_special - O_max) * s_var[(i, m)]

    total_flags = lpSum([s_var[(i, m)] for m in M_range])
    prob += total_flags <= M_over

# 9. 連続勤務日の上限を設定（最大6連勤）
for i in I:
    for t in T_range:
        if t + 6 <= T:
            prob += lpSum([w[(i, t + k)] for k in range(0, 7)]) <= 6

# 10. 夜勤に関する補助変数の制約
for i in I:
    for t in T_range:
        # g_{i,t} の線形化
        prob += g[(i, t)] >= r[(i, t)] - Big_M * (1 - n[(i, t)])
        prob += g[(i, t)] <= r[(i, t)]
        prob += g[(i, t)] <= Big_M * n[(i, t)]

        # f_{i,t} の線形化
        prob += f[(i, t)] >= (h[(i, t)] - r[(i, t)]) - Big_M * (1 - n[(i, t)])
        prob += f[(i, t)] <= h[(i, t)] - r[(i, t)]
        prob += f[(i, t)] <= Big_M * n[(i, t)]

# 問題の解決
prob.solve()

# 結果の表示
print("Status:", LpStatus[prob.status])

for i in I:
    print(f'従業員 {i}:{p_i[i]}')
    for t in T_range:
        shift = '休み'
        if value(d[(i, t)]) == 1:
            shift = '昼勤務'
        elif value(n[(i, t)]) == 1:
            shift = '夜勤務'
        if shift == '休み':
            labor_hours = 0.00
            overtime_hours = 0.00
        else:
            labor_hours = value(h[(i, t)])
            overtime_hours = value(r[(i, t)])
        print(f'  日 {t}: {shift}, 労働時間: {labor_hours:.2f} 時間, 時間外: {overtime_hours:.2f} 時間')
    print('-----------------------------------')

print(f'総利益: {value(prob.objective):.2f} 円')
