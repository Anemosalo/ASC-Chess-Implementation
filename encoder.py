from bit_io import BitWriter
import board_state
import chess
from math import floor


def encode_game(move_sequence:list[str]):



    board = chess.Board()
    writer = BitWriter()
    pending = False
    for i in range(len(move_sequence)):
        legal_moves = board_state.move_list_uci_sorted(board)
        k_t = board_state.compute_Kt(legal_moves)
        u_t = board_state.compute_Ut(legal_moves)
        b_t = board_state.compute_bt(legal_moves)
        j_t = legal_moves.index(move_sequence[i])
        if b_t == 0:
            writer.write_bit(0)
            board.push_uci(move_sequence[i])
            continue
        if k_t==2:
            c_t = j_t
            writer.write_bits(c_t,b_t)
            board.push_uci(move_sequence[i])
            continue
        if j_t < u_t:
            temp_board = board.copy()
            temp_board.push_uci(legal_moves[j_t])
            msb_next = 0
            for next_i in range(i+1, len(move_sequence)):
                next_legal = board_state.move_list_uci_sorted(temp_board)
                next_k = board_state.compute_Kt(next_legal)
                if next_k >= 3:
                    next_u = board_state.compute_Ut(next_legal)
                    next_b = board_state.compute_bt(next_legal)
                    next_j = next_legal.index(move_sequence[next_i])
                    if next_j<next_u:
                        msb_next = (2*next_j)>>(next_b-1)
                    else:
                        msb_next = (next_j+next_u)>>(next_b-1)
                    break
                temp_board.push_uci(move_sequence[next_i])
            c_t = 2*j_t + msb_next
            
        else:
            c_t = j_t + u_t
        if pending:
            writer.write_bits(c_t,b_t-1)
        else:
            writer.write_bits(c_t,b_t)
        pending = j_t < u_t
        board.push_uci(move_sequence[i])
    writer.pad_trailer()
    return writer.data()
