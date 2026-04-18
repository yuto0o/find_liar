import itertools
import random
from pathlib import Path
from typing import Dict, List, Tuple

# =========================
# 設定パラメータ
# =========================
NUM_PEOPLE = 10  # 登場人物数（A, B, C...）
MAX_SOLUTIONS = 6  # Noneなら制限なし、整数で解の数を制限
SEED = None  # 再現性が欲しい場合は整数を入れる
CURRENT_PATH = Path(__file__)
OUTPUT_FILE = CURRENT_PATH.parent / "puzzle.txt"

if SEED is not None:
    random.seed(SEED)


# =========================
# 人物生成
# =========================
def generate_people(n: int) -> List[str]:
    return [chr(ord("A") + i) for i in range(n)]


# =========================
# 発言テンプレート
# =========================
def statement_templates(speaker: str, people: List[str]):
    others = [p for p in people if p != speaker]

    target = random.choice(others)

    templates = [
        (f"{target}は嘘つきだ。", lambda assign: not assign[target]),
        (f"{target}は正しい。", lambda assign: assign[target]),
    ]

    # 自己言及
    templates += [
        ("私は嘘をついていない。", lambda assign: assign[speaker]),
        ("私は嘘つきだ。", lambda assign: not assign[speaker]),
    ]

    return random.choice(templates)


# =========================
# 問題生成
# =========================
def generate_puzzle(people: List[str]):
    statements = {}
    evaluators = {}

    for p in people:
        text, func = statement_templates(p, people)
        statements[p] = text
        evaluators[p] = func

    return statements, evaluators


# =========================
# 解探索
# =========================
def find_solutions(people: List[str], evaluators: Dict[str, callable]):
    solutions = []

    for values in itertools.product([True, False], repeat=len(people)):
        assign = dict(zip(people, values))

        valid = True
        for p in people:
            if evaluators[p](assign) != assign[p]:
                valid = False
                break

        if valid:
            solutions.append(assign)

    return solutions


# =========================
# メイン
# =========================
def main():
    people = generate_people(NUM_PEOPLE)

    while True:
        statements, evaluators = generate_puzzle(people)
        solutions = find_solutions(people, evaluators)

        if len(solutions) == 0:
            continue

        if MAX_SOLUTIONS is not None and len(solutions) > MAX_SOLUTIONS:
            continue

        break

    # ファイル出力
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("証言から嘘をついているのがだれか見つけましょう\n\n")
        for p in people:
            f.write(f"{p}: {statements[p]}\n")

        f.write("\n--- 解答例 ---\n")
        for i, sol in enumerate(solutions):
            f.write(f"パターン{i + 1}:\n")
            for p in people:
                f.write(f"  {p}: {'真' if sol[p] else '嘘'}\n")
            f.write("\n")

    print(f"問題を {OUTPUT_FILE} に出力しました")
    print(f"解の数: {len(solutions)}")


if __name__ == "__main__":
    main()
