from bit_io import BitReader
import board_state
import chess


def decode_game(data):
    reader = BitReader(data)
    
    board = chess.Board()
    p_t = None
    move_sequence = []
    while True:
        legal_moves = board_state.move_list_uci_sorted(board)
        k_t = board_state.compute_Kt(legal_moves)
        if k_t == 0:
            break ##Checkmate, Stalemate etc.
        u_t = board_state.compute_Ut(legal_moves)
        b_t = board_state.compute_bt(legal_moves)
        if b_t == 0:
            if reader.read_bits(1) == -1:
                break
            board.push_uci(legal_moves[0])
            move_sequence.append(legal_moves[0])
            continue
        if k_t==2:
            c_t = reader.read_bits(1)
            if c_t == -1:
                break
            j_t = c_t
            board.push_uci(legal_moves[j_t])
            move_sequence.append(legal_moves[j_t])
            continue
        if p_t == None:
            c_t = reader.read_bits(b_t)
            if c_t == -1:
                break
        else:
            c_t = reader.read_bits(b_t-1)
            if c_t == -1:
                break
            c_t = (p_t<<(b_t -1) | c_t)
            

        if c_t< u_t:
            p_t = 0
            j_t = c_t
        elif c_t >= k_t:
            p_t = 1
            j_t = c_t - k_t
        else:
            p_t = None
            j_t = c_t

        board.push_uci(legal_moves[j_t])
        move_sequence.append(legal_moves[j_t])
    return move_sequence