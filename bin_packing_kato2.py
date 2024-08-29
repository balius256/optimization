import pulp
import time
import random

# 母材の長さ
L = 1570

# 切断材料の長さ
lengths = [100, 70, 53, 45, 27, 25, 23]

# 切断材料の必要数量をランダムに決定する関数
def generate_required_quantities():
    return [random.randint(1, 10000) for _ in lengths]

# 必要数量を生成
required_quantities = generate_required_quantities()

# 最大母材数の仮定
N = 2000

def calculate_waste(pattern, lengths, total_length):
    used_length = sum(pattern[i] * lengths[i] for i in range(len(pattern)))
    return total_length - used_length

# ステップ1: 母材枚数最小化問題の定義
prob1 = pulp.LpProblem("Minimize_Number_of_Raw_Materials", pulp.LpMinimize)

# 変数の定義
x = pulp.LpVariable.dicts("x", ((i, j) for i in range(len(lengths)) for j in range(N)), lowBound=0, cat='Integer')
y = pulp.LpVariable.dicts("y", (j for j in range(N)), cat='Binary')

# 目的関数の設定
prob1 += pulp.lpSum([y[j] for j in range(N)]), "Minimize_Total_Raw_Materials"

# 制約1: 各材料の要求本数を満たす
for i in range(len(lengths)):
    prob1 += pulp.lpSum([x[(i, j)] for j in range(N)]) == required_quantities[i], f"Demand_Constraint_{i}"

# 制約2: 母材の長さ制約
for j in range(N):
    prob1 += pulp.lpSum([lengths[i] * x[(i, j)] for i in range(len(lengths))]) <= L * y[j], f"Length_Constraint_{j}"

# 最適化実行
start_time = time.time()
prob1.solve(pulp.SCIP_CMD(msg=False))  # SCIPソルバーを使用
end_time = time.time()

# ステップ1の結果の出力
used_patterns = []
pattern_counts = {}
total_cut_material_length_initial = 0

# 母材の長さ、切断材料の長さ、切断材料の必要数量を出力
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

total_raw_materials_used = sum(y[j].varValue for j in range(N))
total_waste_length = 0

print(f"\n初期解で見つかった切り出しパターンとその利用回数:")
for pattern, count in pattern_counts.items():
    waste_length = calculate_waste(pattern, lengths, L)
    total_waste_length += waste_length * count
    total_cut_material_length_initial += sum(pattern[i] * lengths[i] for i in range(len(pattern))) * count
    print(f"パターン {pattern}: {count} 回使用, 端材の長さ: {waste_length} mm")

# 初期解の余分な切断材料の総長さを計算
total_required_material_length = sum(required_quantities[i] * lengths[i] for i in range(len(lengths)))
total_excess_cut_material_length_initial = total_cut_material_length_initial - total_required_material_length

print(f"\n初期解の余分な切断材料の総長さ: {total_excess_cut_material_length_initial} mm")

# ステップ2: パターン数制限付き最適化の実装

# 使用するパターン数の上限
k = 10  # 例として上限を設定

# 新しい問題の定義
prob2 = pulp.LpProblem("Minimize_Number_of_Raw_Materials_with_Limited_Patterns", pulp.LpMinimize)

# 変数の定義
z = pulp.LpVariable.dicts("z", (h for h in range(len(used_patterns))), lowBound=0, cat='Integer')
w = pulp.LpVariable.dicts("w", (h for h in range(len(used_patterns))), cat='Binary')

# 目的関数の設定
prob2 += pulp.lpSum([z[h] for h in range(len(used_patterns))]), "Minimize_Total_Raw_Materials_with_Limited_Patterns"

# 制約1: 切り出し要求を満たす
for j in range(len(lengths)):
    prob2 += pulp.lpSum([z[h] * used_patterns[h][j] for h in range(len(used_patterns))]) >= required_quantities[j], f"Demand_Constraint_{j}"

# 制約2: パターンを使用するかどうか
for h in range(len(used_patterns)):
    prob2 += z[h] >= w[h], f"Pattern_Usage_Constraint_{h}"

# 制約3: 使用するパターン数の上限
prob2 += pulp.lpSum([w[h] for h in range(len(used_patterns))]) <= k, "Pattern_Limit_Constraint"

# 制約4: 各切り出し材料長をカバーするパターンが少なくとも1つ選ばれることを保証
for i in range(len(lengths)):
    prob2 += pulp.lpSum([w[h] for h in range(len(used_patterns)) if used_patterns[h][i] > 0]) >= 1, f"Material_Coverage_Constraint_{i}"

# 最適化実行
prob2.solve(pulp.SCIP_CMD(msg=False))  # SCIPソルバーを使用

# ステップ2の結果の出力
final_pattern_counts = {}
total_waste_length_final = 0
total_cut_material_length_final = 0

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

print(f"\n最適解で導出された切り出しパターンとその利用回数:")
for pattern, count in final_pattern_counts.items():
    waste_length = calculate_waste(pattern, lengths, L)
    print(f"パターン {pattern}: {count} 回使用, 端材の長さ: {waste_length} mm")

# 最適解の余分な切断材料の総長さを計算
total_excess_cut_material_length_final = total_cut_material_length_final - total_required_material_length

# 出力のまとめ
print(f"\n概要:")
print(f"初期の使用母材数: {total_raw_materials_used}")
print(f"初期の総端材の長さ: {total_waste_length} mm")
print(f"初期の余分な切断材料の総長さ: {total_excess_cut_material_length_initial} mm")
if final_pattern_counts:
    print(f"最終的な使用母材数: {sum(final_pattern_counts.values())}")
    print(f"最終的な総端材の長さ: {total_waste_length_final} mm")
    print(f"最終的な余分な切断材料の総長さ: {max(0, total_excess_cut_material_length_final)} mm")
else:
    print("最終的な解ではパターンが使用されませんでした。")
print(f"計算時間: {end_time - start_time:.2f} 秒")
