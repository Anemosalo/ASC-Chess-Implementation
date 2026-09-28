import math
from pathlib import Path
from encoder import encode_game
import chess
import board_state
def b_of(k_t):
    if k_t==1:
        return 0
    else:
        return math.ceil(math.log2(k_t))
    
def u_of(k_t):
    return 2**b_of(k_t) - k_t



def load_games(folder="games_archive"):
    saved_files = sorted(Path(folder).glob("*.txt"))
    all_games_moves =[]
    for file in saved_files:
        games_str = file.read_text()
        games = games_str.splitlines()
        for game in games:
            move_sequence = game.split(",")
            all_games_moves.append(move_sequence)

    return all_games_moves

def replay(game):
    board = chess.Board()
    k_j_list =[]
    for move in game:
        legal = board_state.move_list_uci_sorted(board)
        k = len(legal)
        j = legal.index(move)
        k_j_list.append([k,j])
        board.push_uci(move)
    return k_j_list


def tb_bits(k_j_list):
    total_bits = 0
    for pair in k_j_list:
        k = pair[0]
        j = pair[1]

        b = b_of(k)
        u = u_of(k)
        if k == 1:
            total_bits+=1
        elif j<u:
            total_bits+= b-1
        else:
            total_bits+= b
    return total_bits


def naive_bits(k_j_list):
    total_bits = 0
    for pair in k_j_list:
        k = pair[0]
        b = b_of(k)
        if k==1:
            total_bits+=1
        else:
            total_bits+=b
    return total_bits


def mixed_radix_bound(k_j_list):
    return sum(math.log2(pair[0]) for pair in k_j_list)

def E_of(k_j_list):
    t = 0
    index = -1
    for pair in k_j_list:
        k = pair[0]
        if k>=3:
            index = t
        t+=1
    if index == -1:
        return 0
    if (k_j_list[index])[1] < u_of(k_j_list[index][0]):
        return 1
    return 0
    return 0    

def asc_payload_bits(data):
    r = data[-1] & 7
    if r<=5:
        return (len(data)-1)*8 + r
    return (len(data)-2)*8 + r

def container_bits(payload_bits):
    return 8*math.ceil((payload_bits+3)/8)



def main():
    games = load_games()
    plies = 0
    asc = 0
    asc_container = 0
    tb = 0
    tb_container = 0
    naive = 0
    mixed = 0
    E_count = 0
    identity_ok = 0
    game_index = 0
    container_ok = 0
    for moves in games:
        k_j_list = replay(moves)
        data = encode_game(moves)
        asc_game = asc_payload_bits(data)
        tb_game = tb_bits(k_j_list)
        E = E_of(k_j_list)

        if asc_game-tb_game==E:
            identity_ok+=1
        else:
            print(f"identity fails in game {game_index}: ASC {asc_game}, TB {tb_game}, E {E}")
        if 8*len(data)==container_bits(asc_game):
            container_ok+=1
        else:
            print(f"trailer mismatch in game {game_index}")

        plies+=len(moves)
        asc+=asc_game
        asc_container+=8*len(data)
        tb+=tb_game
        tb_container+=container_bits(tb_game)
        naive+=naive_bits(k_j_list)
        mixed+=mixed_radix_bound(k_j_list)
        E_count+=E

        game_index+=1

    totals = {
        "Naive": naive,
        "Truncated binary": tb,
        "ASC": asc,
        "TB incl. byte container": tb_container,
        "ASC incl. byte container": asc_container,
        "Mixed-radix bound": mixed,
    }
    print_table(totals, plies, len(games))
    print(f"\nIdentity ASC - TB = E holds in {identity_ok}/{len(games)} games (E = 1 in {E_count})")
    print(f"Container = 8*ceil((payload+3)/8) holds in {container_ok}/{len(games)} games")


def print_table(totals, plies, n_games):
    print(f"{n_games} games, {plies} plies\n")
    print(f"{'Method':26s} {'bits/ply':>9s} {'bits/game':>10s}")
    for name, total in totals.items():
        print(f"{name:26s} {total/plies:9.4f} {total/n_games:10.2f}")


if __name__ == "__main__":
    main()