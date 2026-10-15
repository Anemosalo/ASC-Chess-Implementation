"""Count how often each number of legal moves K occurs over the games in ../games_archive.

Writes k_distribution.csv (columns K, plies), the menu distribution used by decode_speed.c.
Run from this folder:  python3 k_distribution.py
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import chess  # noqa: E402
from board_state import move_list_uci_sorted  # noqa: E402

counts = Counter()
for path in sorted((HERE.parent / "games_archive").glob("*.txt")):
    for line in path.read_text().splitlines():
        moves = [m for m in line.strip().split(",") if m]
        if not moves:
            continue
        board = chess.Board()
        for uci in moves:
            counts[len(move_list_uci_sorted(board))] += 1
            board.push_uci(uci)

with open(HERE / "k_distribution.csv", "w") as f:
    f.write("K,plies\n")
    for k in sorted(counts):
        f.write(f"{k},{counts[k]}\n")
print(f"{sum(counts.values())} plies, {len(counts)} distinct K -> k_distribution.csv")
