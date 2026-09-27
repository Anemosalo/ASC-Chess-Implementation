from bit_io import BitWriter
import board_state
import chess

def next_msb(board:chess.Board,move_sequence:list[str]):
    if move_sequence == []:
        return 0
    legal_moves = board_state.move_list_uci_sorted(board)
    b_t = board_state.compute_bt(legal_moves)
    while b_t == 0:
        board.push_uci(move_sequence[0])
        move_sequence = move_sequence[1:]
        legal_moves = board_state.move_list_uci_sorted(board)
        b_t = board_state.compute_bt(legal_moves)
        if move_sequence == []:
                return 0
    legal_moves = board_state.move_list_uci_sorted(board)
    k_t = board_state.compute_Kt(legal_moves)
    u_t = board_state.compute_Ut(legal_moves)
    j_t = legal_moves.index(move_sequence[0])
    if j_t < u_t:
        temp_board = board.copy()
        temp_board.push_uci(move_sequence[0])
        s_t = next_msb(temp_board,move_sequence=move_sequence[1:])
        if s_t == 0:
            c_t = j_t
        else:
            c_t = j_t+k_t
    else:
        c_t = j_t
    return (c_t>>b_t-1)&1

def encode_game(move_sequence:list[str]):



    board = chess.Board()
    writer = BitWriter()
    p_t = None
    while move_sequence:
        legal_moves = board_state.move_list_uci_sorted(board)
        k_t = board_state.compute_Kt(legal_moves)
        u_t = board_state.compute_Ut(legal_moves)
        b_t = board_state.compute_bt(legal_moves)
        j_t = legal_moves.index(move_sequence[0])
        if b_t == 0:
            writer.write_bit(0)
            board.push_uci(move_sequence[0])
            move_sequence = move_sequence[1:]
            continue
        j_t = legal_moves.index(move_sequence[0])
        if j_t < u_t:
            temp_board = board.copy()
            temp_board.push_uci(move_sequence[0])
            s_t = next_msb(temp_board,move_sequence[1:])
            if s_t == 0:
                c_t = j_t
            else:
                c_t = j_t + k_t
        else:
            s_t = None
            c_t = j_t
        if p_t != None:
            if b_t>1:
                writer.write_bits(c_t,b_t-1)
            else:
                writer.write_bits(c_t,b_t)
        else:
            writer.write_bits(c_t,b_t)
        p_t = s_t
        board.push_uci(move_sequence[0])
        move_sequence = move_sequence[1:]
    writer.pad_trailer()
    return writer.data()