from bit_io import BitWriter
import board_state
import chess

def resolve_chain(board:chess.Board,move_sequence:list[str],start:int):
    temp_board = board.copy(stack=False)
    chain = []
    i = start
    while i < len(move_sequence):
        legal_moves = board_state.move_list_uci_sorted(temp_board)
        k_t = board_state.compute_Kt(legal_moves)
        if k_t >=3:
            u_t = board_state.compute_Ut(legal_moves)
            b_t = board_state.compute_bt(legal_moves)
            j_t = legal_moves.index(move_sequence[i])
            chain.append((j_t,k_t,u_t,b_t))
            if j_t >= u_t:
                break
        temp_board.push_uci(move_sequence[i])
        i+=1
    # Every codeword in a chain starts with the same bit as the last one (0 if the chain
    # runs to the end of the game), so no backward pass is needed.
    j_last,k_last,u_last,b_last = chain[-1]
    msb = (j_last>>b_last-1)&1 if j_last >= u_last else 0
    return [j_t + k_t*msb if j_t < u_t else j_t for j_t,k_t,u_t,b_t in chain]

def encode_game(move_sequence:list[str]):



    board = chess.Board()
    writer = BitWriter()
    pending = False
    chain_codes = []
    chain_pos = 0
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
        if chain_pos == len(chain_codes):
            chain_codes = resolve_chain(board,move_sequence,i)
            chain_pos = 0
        c_t = chain_codes[chain_pos]
        chain_pos+=1
        if pending:
            writer.write_bits(c_t,b_t-1)
        else:
            writer.write_bits(c_t,b_t)
        pending = j_t < u_t
        board.push_uci(move_sequence[i])
    writer.pad_trailer()
    return writer.data()
