import random


def generate_system_failure_puzzle():
    # 監視対象のサーバー（コンポーネント）リスト
    servers = ["Web", "DB", "API", "Auth", "Cache"]

    while True:
        statements = {}
        # 1. 各エージェントにランダムなログ（証言）を割り当てる
        for s in servers:
            stmt_type = random.choice(["not_me", "blame", "defend"])
            target = random.choice([x for x in servers if x != s])

            if stmt_type == "not_me":
                text = f"自コンポーネント({s})は正常に稼働しています。"
            elif stmt_type == "blame":
                text = f"エラーを検知しました。根本原因は {target} です。"
            else:  # defend
                text = f"{target} との通信は正常です（原因ではありません）。"

            statements[s] = {"type": stmt_type, "target": target, "text": text}

        # 2. 条件をランダムに設定（「1つだけバグっている」or「1つだけ正常」）
        condition = random.choice(["bug", "normal"])
        target_truth_count = len(servers) - 1 if condition == "bug" else 1

        if condition == "bug":
            condition_text = "監視エージェントのうち、1つだけが故障して【誤ったログ】を出力しており、残りはすべて正しいログを出力しています。"
        else:
            condition_text = "大規模なネットワーク障害により、監視エージェントのうち1つだけが【正しいログ】を出力しており、残りはすべて誤ったログを出力しています。"

        # 3. 全サーバーが原因だった場合をシミュレーションし、矛盾がないか確認
        valid_solutions = []
        for test_cause in servers:
            truth_count = 0
            for speaker, stmt in statements.items():
                if stmt["type"] == "not_me":
                    is_true = test_cause != speaker
                elif stmt["type"] == "blame":
                    is_true = test_cause == stmt["target"]
                elif stmt["type"] == "defend":
                    is_true = test_cause != stmt["target"]

                if is_true:
                    truth_count += 1

            # 条件と一致するなら、そのサーバーが根本原因の可能性がある
            if truth_count == target_truth_count:
                valid_solutions.append(test_cause)

        # 4. 解が「たった1つ」に確定する問題だけを採用して返す
        if len(valid_solutions) == 1:
            problem = f"【インシデント調査レポート】\nシステムで障害が発生しました。各サーバーの監視エージェントが以下のログを出力しています。\n\n＜前提条件＞\n{condition_text}\n\n＜エージェントのログ＞\n"
            for s in servers:
                problem += f"[{s}エージェント]: {statements[s]['text']}\n"
            problem += "\n根本原因となっているサーバーはどれでしょうか？"

            answer = f"【根本原因の解答】\n{valid_solutions[0]}"

            return problem, answer


# 実行
if __name__ == "__main__":
    problem, answer = generate_system_failure_puzzle()
    print(problem)
    print("-" * 30)
    print(answer)
