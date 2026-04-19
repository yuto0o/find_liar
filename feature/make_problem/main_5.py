import random


def generate_blind_spof_puzzle(cluster_size=6):
    # ランダムなサーバー名のプール
    pool = [
        "Alpha",
        "Bravo",
        "Charlie",
        "Delta",
        "Echo",
        "Foxtrot",
        "Golf",
        "Hotel",
        "India",
        "Juliet",
        "Kilo",
        "Lima",
        "Mike",
        "November",
        "Oscar",
        "Papa",
        "Quebec",
        "Romeo",
        "Sierra",
        "Tango",
        "Uniform",
        "Victor",
        "Whiskey",
        "X-ray",
        "Yankee",
        "Zulu",
        "Apex",
        "Nexus",
        "Vortex",
        "Quantum",
        "Cipher",
        "Enigma",
    ]

    # 必要な数の名前をランダムに抽出
    selected_names = random.sample(pool, cluster_size * 2 + 1)

    # グループとSPOFに名前を割り当て
    group_a = selected_names[:cluster_size]
    group_b = selected_names[cluster_size : cluster_size * 2]
    spof_node = selected_names[-1]

    edges = set()

    # 【修正点1】グループ内部の偶発的なSPOFを防ぐため、まず全員をリング状に繋ぐ
    def build_robust_cluster(nodes):
        cluster_edges = set()
        for i in range(len(nodes)):
            u = nodes[i]
            v = nodes[(i + 1) % len(nodes)]
            cluster_edges.add(tuple(sorted([u, v])))
        # さらにダミーの通信網をランダムに追加
        for _ in range(len(nodes)):
            u, v = random.sample(nodes, 2)
            if u != v:
                cluster_edges.add(tuple(sorted([u, v])))
        return cluster_edges

    edges.update(build_robust_cluster(group_a))
    edges.update(build_robust_cluster(group_b))

    # 【修正点2】SPOFノードを各グループの「複数」のノードと接続する（玄関口の冗長化）
    # これにより、玄関口のサーバーが落ちても別ルートでSPOFに辿り着けるようになる
    gateways_a = random.sample(group_a, 2)  # グループAから2つの玄関口を選ぶ
    gateways_b = random.sample(group_b, 2)  # グループBから2つの玄関口を選ぶ

    for gw in gateways_a:
        edges.add(tuple(sorted([gw, spof_node])))
    for gw in gateways_b:
        edges.add(tuple(sorted([gw, spof_node])))

    # 接続リスト化して完全にシャッフル（出現順からの推測を防止）
    edge_list = list(edges)
    random.shuffle(edge_list)

    # ターゲットノード（玄関口以外のノードを選ぶと問題のクオリティが上がる）
    target_a = random.choice([n for n in group_a if n not in gateways_a])
    target_b = random.choice([n for n in group_b if n not in gateways_b])

    # ---------------------------
    # 問題文の組み立て
    # ---------------------------
    problem = "【インシデント予防：単一障害点の特定】\n"
    problem += (
        "以下の接続ログは、企業の社内ネットワークの通信経路（双方向）を示しています。\n"
    )
    problem += "現在、すべてのサーバーは互いに通信可能な状態にあります。\n\n"

    for i, (u, v) in enumerate(edge_list):
        problem += f"接続 {i + 1:02d}: [{u}] <---> [{v}]\n"

    problem += f"\n＜ミッション＞\n"
    problem += f"もし「ある1つのサーバー」がダウンすると、[{target_a}] と [{target_b}] の間の通信が【完全に遮断】されてしまいます。\n"
    problem += "（他のどのサーバーがダウンしても、迂回ルートが存在するため通信は維持されます）\n"
    problem += "このネットワークにおける「単一障害点（致命的な弱点となるサーバー）」の名前を特定してください。\n"

    # ---------------------------
    # 模範解答（解説・検証用）の組み立て
    # ---------------------------
    answer = f"【模範解答】\n"
    answer += f"単一障害点 (SPOF): {spof_node}\n\n"
    answer += f"--- 以下、解説用のネットワーク構造データ ---\n"
    answer += f"■ グループA (左側のクラスタ)\n  所属サーバー: {', '.join(group_a)}\n"
    answer += f"  SPOFと接続しているノード(冗長化済): {', '.join(gateways_a)}\n\n"
    answer += f"■ グループB (右側のクラスタ)\n  所属サーバー: {', '.join(group_b)}\n"
    answer += f"  SPOFと接続しているノード(冗長化済): {', '.join(gateways_b)}\n"

    return problem, answer


# 実行
if __name__ == "__main__":
    problem, answer = generate_blind_spof_puzzle(cluster_size=6)
    print(problem)
    print("-" * 50)
    print(answer)
