import pulp
import time
import random

# 母材の長さ
L = 1570

# 切断材料の長さ
lengths = [100, 70, 53, 45, 27, 25, 23]

# 切断材料の必要数量
required_quantities = [97, 16, 51, 74, 41, 56, 93]  # 指定された例の数量

# 最大母材数の仮定
N = 100

def calculate_waste(pattern, lengths, total_length):
    used_length = sum(pattern[i] * lengths[i] for i in range(len(pattern)))
    return max(0, total_length - used_length)

# ステップ1: 母材枚数最小化問題の定義
prob1 = pulp.LpProblem("Minimize_Number_of_Raw_Materials", pulp.LpMinimize)

# 変数の定義
x = pulp.LpVariable.dicts("x", ((i, j) for i in range(len(lengths)) for j in range(N)), lowBound=0, cat='Integer')
y = pulp.LpVariable.dicts("y", (j for j in range(N)), cat='Binary')

# 目的関数の設定
prob1 += pulp.lpSum([y[j] for j in range(N)]), "Minimize_Total_Raw_Materials"

# 制約1: 各材料の要求本数を満たす
for i in range(len(lengths)):
    prob1 += pulp.lpSum([x[(i, j)] for j in range(N)]) >= required_quantities[i], f"Demand_Constraint_{i}"

# 制約2: 母材の長さ制約
for j in range(N):
    prob1 += pulp.lpSum([lengths[i] * x[(i, j)] for i in range(len(lengths))]) <= L * y[j], f"Length_Constraint_{j}"

# 最適化実行
start_time = time.time()
prob1.solve(pulp.PULP_CBC_CMD(msg=True))  # CBCソルバーを使用
end_time = time.time()

# ステップ1の結果の出力
used_patterns = []
pattern_counts = {}
total_cut_material_length_initial = 0
total_waste_length = 0

# 検算用の初期解での切り出し結果
cut_materials_initial = [0] * len(lengths)

print(f"\n母材の長さ: {L} mm")
print(f"切断材料の長さ: {lengths} mm")
print(f"切断材料の必要数量: {required_quantities}")

print(f"\nステータス (ステップ1): {pulp.LpStatus[prob1.status]}")
for j in range(N):
    if y[j].varValue > 0:
        pattern = tuple(int(x[(i, j)].varValue) for i in range(len(lengths)))
        if pattern in pattern_counts:
            pattern_counts[pattern] += 1
        else:
            pattern_counts[pattern] = 1
            used_patterns.append(pattern)

# 各パターンの端切れ長を計算し、パターンごとに保存
for pattern, count in pattern_counts.items():
    waste_length = calculate_waste(pattern, lengths, L)
    total_waste_length += waste_length * count
    total_cut_material_length_initial += sum(pattern[i] * lengths[i] for i in range(len(pattern))) * count

    # 検算のため、切り出された材料の数量を集計
    for i in range(len(lengths)):
        cut_materials_initial[i] += pattern[i] * count

print(f"\n初期解の余分な切断材料の総長さ: {total_cut_material_length_initial - sum(required_quantities[i] * lengths[i] for i in range(len(lengths)))} mm")
print("\n初期解の検算結果:")
for i in range(len(lengths)):
    print(f"材料 {lengths[i]}mm: 必要数量 = {required_quantities[i]}個, 実際に切り出された数量 = {cut_materials_initial[i]}個")

# パターン数の上限を初期解から段階的に減らしていく
for k in range(len(used_patterns), 0, -1):
    print(f"\n\nパターン数の上限を {k} に設定して最適化を実行中...")

    # 新しい問題の定義 (ステップ2: パターン数制限付き最適化)
    prob2 = pulp.LpProblem(f"Minimize_Number_of_Raw_Materials_with_Limited_Patterns_k={k}", pulp.LpMinimize)

    # 変数の定義
    z = pulp.LpVariable.dicts("z", (h for h in range(len(used_patterns))), lowBound=0, cat='Integer')
    w = pulp.LpVariable.dicts("w", (h for h in range(len(used_patterns))), cat='Binary')

    # 目的関数の設定
    prob2 += pulp.lpSum([z[h] for h in range(len(used_patterns))]), "Minimize_Total_Raw_Materials_with_Limited_Patterns"

    # 制約1: 切り出し要求を満たす
    for j in range(len(lengths)):
        prob2 += pulp.lpSum([z[h] * used_patterns[h][j] for h in range(len(used_patterns))]) >= required_quantities[j], f"Demand_Constraint_{j}_Step2"

    # 制約2: パターンを使用するかどうか
    M = 1000  # 十分大きな定数
    for h in range(len(used_patterns)):
        prob2 += w[h] <= z[h], f"Pattern_Usage_Constraint_1_{h}"
        prob2 += z[h] <= M * w[h], f"Pattern_Usage_Constraint_2_{h}"

    # 制約3: 使用するパターン数の上限
    prob2 += pulp.lpSum([w[h] for h in range(len(used_patterns))]) <= k, "Pattern_Limit_Constraint"

    # 最適化実行
    start_time_step2 = time.time()
    prob2.solve(pulp.PULP_CBC_CMD(msg=True))
    end_time_step2 = time.time()

    # ステップ2の結果の出力
    final_pattern_counts = {}
    total_waste_length_final = 0
    total_cut_material_length_final = 0

    # 検算用の最適解での切り出し結果
    cut_materials_final = [0] * len(lengths)

    print(f"\nステータス (ステップ2): {pulp.LpStatus[prob2.status]}")
    for h in range(len(used_patterns)):
        if w[h].varValue > 0:
            pattern = used_patterns[h]
            count = int(z[h].varValue)
            if count > 0:  # countが0より大きいときのみ処理
                final_pattern_counts[pattern] = count
                waste_length = calculate_waste(pattern, lengths, L)
                total_waste_length_final += waste_length * count
                total_cut_material_length_final += sum(pattern[i] * lengths[i] for i in range(len(pattern))) * count

                # 検算のため、切り出された材料の数量を集計
                for i in range(len(lengths)):
                    cut_materials_final[i] += pattern[i] * count

    print(f"\n最適解で導出された切り出しパターンとその利用回数:")
    for pattern, count in final_pattern_counts.items():
        waste_length = calculate_waste(pattern, lengths, L)
        print(f"パターン {pattern}: {count} 回使用, 端材の長さ: {waste_length} mm")

    # 最適解の検算結果を表示
    print("\n最適解の検算結果:")
    for i in range(len(lengths)):
        print(f"材料 {lengths[i]}mm: 必要数量 = {required_quantities[i]}個, 実際に切り出された数量 = {cut_materials_final[i]}個")

    # 最終的な使用母材数と端材の長さを表示
    print(f"\n最終的な使用母材数: {sum(final_pattern_counts.values())}")
    print(f"最終的な総端材の長さ: {total_waste_length_final} mm")
    print(f"ステップ2の計算時間: {end_time_step2 - start_time_step2:.2f} 秒")

