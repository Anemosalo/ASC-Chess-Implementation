import chess
import math
def move_list_uci_sorted(board:chess.Board)->list[str]:
    moves = board.legal_moves
    moves_uci=[]
    for move in moves:
        moves_uci.append(move.uci())
    return sorted(moves_uci)


def compute_Kt(moves:list[str]):
    return len(moves)

def compute_bt(moves:list[str]):
     return math.ceil(math.log2(compute_Kt(moves=moves)))

def compute_Ut(moves:list[str]):
    return 2**compute_bt(moves=moves) - compute_Kt(moves=moves)