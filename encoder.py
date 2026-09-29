from bit_io import BitWriter
import board_state
import chess

def resolve_chain(board:chess.Board,move_sequence:list[str]):
    temp_board = board.copy()
    chain = []
    while move_sequence:
        legal_moves = board_state.move_list_uci_sorted(temp_board)
        k_t = board_state.compute_Kt(legal_moves)
        if k_t >=3:
            u_t = board_state.compute_Ut(legal_moves)
            b_t = board_state.compute_bt(legal_moves)
            j_t = legal_moves.index(move_sequence[0])
            chain.append((j_t,k_t,u_t,b_t))
            if j_t >= u_t:
                break
        temp_board.push_uci(move_sequence[0])
        move_sequence = move_sequence[1:]
    msb_t = 0
    chain_codes = []
    for j_t,k_t,u_t,b_t in reversed(chain):
        if j_t < u_t and msb_t == 1:
            c_t = j_t + k_t
        else:
            c_t = j_t
        msb_t = (c_t>>b_t-1)&1
        chain_codes.append((c_t,msb_t))
    chain_codes.reverse()
    return chain_codes

def encode_game(move_sequence:list[str]):



    board = chess.Board()
    writer = BitWriter()
    p_t = None
    chain_codes = [] 
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
        if k_t==2:
            c_t = j_t
            writer.write_bits(c_t,b_t)
            board.push_uci(move_sequence[0])
            move_sequence = move_sequence[1:]
            continue
        if chain_codes == []:
            chain_codes = resolve_chain(board,move_sequence)
        c_t = chain_codes[0][0]
        chain_codes = chain_codes[1:]
        if j_t < u_t:
            if chain_codes == []:
                s_t = 0
            else:
                s_t = chain_codes[0][1]
        else:
            s_t = None
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