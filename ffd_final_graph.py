import random
import time
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.font_manager as fm

# 日本語フォントを指定
font_path = 'C:\\Windows\\Fonts\\meiryo.ttc'  # 日本語フォントのパス
font_prop = fm.FontProperties(fname=font_path)

# 母材の長さ
L = 1570

# 切断材料の長さ
lengths = [100, 70, 53, 45, 27, 25, 23]

# 切断材料の必要数量をランダムに決定する関数
def generate_required_quantities():
    return [random.randint(1, 10000) for _ in lengths]

# First Fit Decreasing アルゴリズム
def first_fit_decreasing(L, products):
    products.sort(reverse=True)
    bins = []
    waste_lengths = defaultdict(int)
    cut_pieces = defaultdict(int)
    patterns = defaultdict(int)

    for product in products:
        placed = False
        for bin in bins:
            if sum(bin) + product <= L:
                bin.append(product)
                placed = True
                break
        if not placed:
            bins.append([product])
    
    for bin in bins:
        pattern = tuple(sorted(bin))
        patterns[pattern] += 1
        for piece in bin:
            cut_pieces[piece] += 1
        waste_length = L - sum(bin)
        if waste_length > 0:
            waste_lengths[waste_length] += 1

    extra_pieces = {length: max(0, cut_pieces[length] - required_quantities[idx]) for idx, length in enumerate(lengths)}
    
    return bins, waste_lengths, extra_pieces, patterns

# 均一パターンでの切り出し
def uniform_cutting_pattern(L, lengths, required_quantities):
    bins = []
    extra_pieces = defaultdict(int)
    waste_lengths = defaultdict(int)
    patterns = defaultdict(int)
    cut_pieces = defaultdict(int)

    for length, quantity in zip(lengths, required_quantities):
        pieces_per_bin = L // length
        num_bins = (quantity + pieces_per_bin - 1) // pieces_per_bin  # 切り上げ
        total_cut = num_bins * pieces_per_bin
        extra_pieces[length] = total_cut - quantity

        for _ in range(num_bins):
            pattern = tuple([length] * pieces_per_bin)
            patterns[pattern] += 1
            bins.append([length] * pieces_per_bin)

            # 端材が切断材料長と一致する場合の処理
            waste_length = L - (pieces_per_bin * length)
            if waste_length > 0:
                if waste_length in lengths:
                    cut_pieces[waste_length] += 1  # 端材を切断材料としてカウント
                else:
                    waste_lengths[waste_length] += 1

    # 端材が切断材料長と一致する場合の調整
    for length in lengths:
        if length in cut_pieces:
            extra_pieces[length] += cut_pieces[length]
            del cut_pieces[length]  # waste_lengthsではなくcut_piecesから削除

    return bins, extra_pieces, waste_lengths, patterns

# 試行回数
num_trials = 100

# 結果を格納するリスト
ffd_results = []
uniform_results = []

for _ in range(num_trials):
    required_quantities = generate_required_quantities()

    # 製品リストを生成
    products = []
    for length, quantity in zip(lengths, required_quantities):
        products.extend([length] * quantity)

    # FFDアルゴリズムを実行
    bins_ffd, waste_lengths_ffd, extra_pieces_ffd, patterns_ffd = first_fit_decreasing(L, products)
    total_waste_length_ffd = sum(length * count for length, count in waste_lengths_ffd.items())
    total_extra_pieces_ffd = sum(length * count for length, count in extra_pieces_ffd.items())
    ffd_results.append((len(bins_ffd), total_waste_length_ffd, total_extra_pieces_ffd))

    # 均一パターンアルゴリズムを実行
    bins_uniform, extra_pieces_uniform, waste_lengths_uniform, patterns_uniform = uniform_cutting_pattern(L, lengths, required_quantities)
    total_waste_length_uniform = sum(length * count for length, count in waste_lengths_uniform.items())
    total_extra_pieces_uniform = sum(length * count for length, count in extra_pieces_uniform.items())
    uniform_results.append((len(bins_uniform), total_waste_length_uniform, total_extra_pieces_uniform))

# データを配列に変換
ffd_results = np.array(ffd_results)
uniform_results = np.array(uniform_results)

# 差分を計算 (均一パターン - FFD)
diff_num_bins = uniform_results[:, 0] - ffd_results[:, 0]
diff_total_waste_length = uniform_results[:, 1] - ffd_results[:, 1]
diff_total_extra_pieces = uniform_results[:, 2] - ffd_results[:, 2]

# 平均と分散を計算
ffd_mean_bins = np.mean(ffd_results[:, 0])
ffd_var_bins = np.var(ffd_results[:, 0])
ffd_mean_waste_length = np.mean(ffd_results[:, 1])
ffd_var_waste_length = np.var(ffd_results[:, 1])
ffd_mean_extra_pieces = np.mean(ffd_results[:, 2])
ffd_var_extra_pieces = np.var(ffd_results[:, 2])

uniform_mean_bins = np.mean(uniform_results[:, 0])
uniform_var_bins = np.var(uniform_results[:, 0])
uniform_mean_waste_length = np.mean(uniform_results[:, 1])
uniform_var_waste_length = np.var(uniform_results[:, 1])
uniform_mean_extra_pieces = np.mean(uniform_results[:, 2])
uniform_var_extra_pieces = np.var(uniform_results[:, 2])

# 差分の平均と分散を計算
diff_mean_bins = np.mean(diff_num_bins)
diff_var_bins = np.var(diff_num_bins)
diff_mean_waste_length = np.mean(diff_total_waste_length)
diff_var_waste_length = np.var(diff_total_waste_length)
diff_mean_extra_pieces = np.mean(diff_total_extra_pieces)
diff_var_extra_pieces = np.var(diff_total_extra_pieces)

# 各必要切断材料長×各切断材料数の総和を計算
ffd_total_cut_length = sum(length * quantity for length, quantity in zip(lengths, required_quantities))
uniform_total_cut_length = sum(length * quantity for length, quantity in zip(lengths, required_quantities))

# 結果を表示
print(f"FFD 使用された母材数の平均: {ffd_mean_bins}, 分散: {ffd_var_bins}")
print(f"FFD 余った端材の総長の平均: {ffd_mean_waste_length}, 分散: {ffd_var_waste_length}")
print(f"FFD 余分な切断材料数の総長の平均: {ffd_mean_extra_pieces}, 分散: {ffd_var_extra_pieces}")

print(f"均一パターン 使用された母材数の平均: {uniform_mean_bins}, 分散: {uniform_var_bins}")
print(f"均一パターン 余った端材の総長の平均: {uniform_mean_waste_length}, 分散: {uniform_var_waste_length}")
print(f"均一パターン 余分な切断材料数の総長の平均: {uniform_mean_extra_pieces}, 分散: {uniform_var_extra_pieces}")

print(f"使用された母材数の差の平均: {diff_mean_bins}, 分散: {diff_var_bins}")
print(f"余った端材の総長の差の平均: {diff_mean_waste_length}, 分散: {diff_var_waste_length}")
print(f"余分な切断材料数の総長の差の平均: {diff_mean_extra_pieces}, 分散: {diff_var_extra_pieces}")

print(f"FFDの各必要切断材料長×各切断材料数の総和: {ffd_total_cut_length}")
print(f"均一パターンの各必要切断材料長×各切断材料数の総和: {uniform_total_cut_length}")

# グラフを描画
plt.figure(figsize=(10, 15))

plt.subplot(4, 1, 1)
plt.hist(diff_num_bins, bins=30, alpha=0.5, label='num_bins の差')
plt.xlabel('値', fontproperties=font_prop)
plt.ylabel('頻度', fontproperties=font_prop)
plt.title('使用された母材数の差', fontproperties=font_prop)
plt.legend(prop=font_prop)

plt.subplot(4, 1, 2)
plt.hist(diff_total_waste_length, bins=30, alpha=0.5, label='total_waste_length の差')
plt.xlabel('値', fontproperties=font_prop)
plt.ylabel('頻度', fontproperties=font_prop)
plt.title('余った端材の総長の差', fontproperties=font_prop)
plt.legend(prop=font_prop)

plt.subplot(4, 1, 3)
plt.hist(diff_total_extra_pieces, bins=30, alpha=0.5, label='total_extra_pieces の差')
plt.xlabel('値', fontproperties=font_prop)
plt.ylabel('頻度', fontproperties=font_prop)
plt.title('余分な切断材料数の総長の差', fontproperties=font_prop)
plt.legend(prop=font_prop)

plt.subplot(4, 1, 4)
plt.hist(ffd_results[:, 0], bins=30, alpha=0.5, label='FFD 必要母材数')
plt.hist(uniform_results[:, 0], bins=30, alpha=0.5, label='均一パターン 必要母材数')
plt.xlabel('値', fontproperties=font_prop)
plt.ylabel('頻度', fontproperties=font_prop)
plt.title('必要母材数', fontproperties=font_prop)
plt.legend(prop=font_prop)

plt.tight_layout()
plt.show()
