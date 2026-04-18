import random


def generate_complex_puzzle(num_chars=10):
    # A〜Jの10人の登場人物
    chars = [chr(65 + i) for i in range(num_chars)]

    while True:
        statements = {}
        # 1. 各登場人物にランダムな発言を割り当てる
        for speaker in chars:
            # ターゲットを1〜2人ランダムに選ぶ
            targets = random.sample(chars, random.choice([1, 2]))

            if len(targets) == 1:
                t1 = targets[0]
                stmt_type = random.choice(["blame_1", "defend_1"])
                name1 = "私" if t1 == speaker else t1

                if stmt_type == "blame_1":
                    text = f"{name1}が犯人だ。"
                else:
                    text = f"{name1}は犯人ではない。"
            else:
                t1, t2 = targets
                stmt_type = random.choice(["blame_2", "defend_2"])
                name1 = "私" if t1 == speaker else t1
                name2 = "私" if t2 == speaker else t2

                if stmt_type == "blame_2":
                    text = f"{name1}か{name2}のどちらかが犯人だ。"
                else:
                    text = f"{name1}も{name2}も犯人ではない。"

            statements[speaker] = {"type": stmt_type, "targets": targets, "text": text}

        # 2. 条件をランダムに設定（「嘘つきが1人」or「正直者が1人」）
        condition = random.choice(["liar", "honest"])
        target_truth_count = num_chars - 1 if condition == "liar" else 1
        cond_text = (
            "この中で【嘘をついているのは1人だけ】である。"
            if condition == "liar"
            else "この中で【本当のことを言っているのは1人だけ】である。"
        )

        # 3. 全員が犯人だった場合をシミュレーションし、矛盾がないか確認
        valid_solutions = []
        for test_cause in chars:
            truth_count = 0
            for speaker, stmt in statements.items():
                stype = stmt["type"]
                tgs = stmt["targets"]

                # 発言の真偽を判定
                if stype == "blame_1":
                    is_true = test_cause == tgs[0]
                elif stype == "defend_1":
                    is_true = test_cause != tgs[0]
                elif stype == "blame_2":
                    is_true = test_cause in tgs
                elif stype == "defend_2":
                    is_true = test_cause not in tgs

                if is_true:
                    truth_count += 1

            # 条件（正直者の数）と一致するなら、その人は犯人の可能性がある
            if truth_count == target_truth_count:
                valid_solutions.append(test_cause)

        # 4. 解が「たった1つ」に確定する良問だけを採用して返す
        if len(valid_solutions) == 1:
            problem = f"【問題】\n{num_chars}人の容疑者（A〜{chars[-1]}）が以下の証言をしています。\n{cond_text}\n\n"
            for s in chars:
                problem += f"{s}: {statements[s]['text']}\n"
            problem += "\n犯人は誰でしょうか？"

            answer = f"【模範解答】\n{valid_solutions[0]}"
            return problem, answer


# 実行
if __name__ == "__main__":
    problem, answer = generate_complex_puzzle(10)
    print(problem)
    print("-" * 30)
    print(answer)
