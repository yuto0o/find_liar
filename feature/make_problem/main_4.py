import random


def generate_money_laundering_puzzle(num_companies=20, cycle_length=6):
    # 架空の企業リストを作成 (A社, B社...)
    companies = [f"{chr(65 + i)}社" for i in range(num_companies)]

    # 1. ループ（循環取引）を行う悪徳企業グループをランダムに選出
    cycle_members = random.sample(companies, cycle_length)

    transactions = []
    # 悪徳グループ内に「ループする送金ルート」を作成
    for i in range(cycle_length):
        sender = cycle_members[i]
        receiver = cycle_members[(i + 1) % cycle_length]
        transactions.append((sender, receiver))

    # 2. ダミーの送金履歴を作成（※絶対に新たなループを作らないための細工）
    # 各企業に「ランク」をつけ、必ず「低いランク→高いランク」へ送金させる
    levels = {c: random.randint(1, 100) for c in companies}

    # ランダムなダミー送金を追加
    for _ in range(num_companies * 2):
        c1, c2 = random.sample(companies, 2)
        # ランクが低い方から高い方へ送金（これで逆流＝ループが起きない）
        if levels[c1] < levels[c2]:
            # 重複していなければ追加
            if (c1, c2) not in transactions:
                transactions.append((c1, c2))

    # 3. ログをシャッフルして難読化
    random.shuffle(transactions)

    # 問題文の組み立て
    problem = f"【国税局 査察データ】\n以下の {len(transactions)} 件の送金ログの中に、売上を水増しするために資金を無限にループさせている「循環取引グループ」が1つだけ存在します。\nそのグループの企業名と、送金ルートを特定してください。\n\n"
    for i, (s, r) in enumerate(transactions):
        problem += f"ログ{i + 1:02d}: {s} から {r} へ 1,000万円を送金\n"

    # 解答の組み立て
    route = " → ".join(cycle_members) + f" → {cycle_members[0]}"
    answer = f"【模範解答】\n循環取引ルート: {route}"

    return problem, answer


# 実行
if __name__ == "__main__":
    problem, answer = generate_money_laundering_puzzle(num_companies=15, cycle_length=5)
    print(problem)
    print("-" * 40)
    print(answer)
