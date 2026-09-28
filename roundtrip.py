from encoder import encode_game
from decoder import decode_game
from pathlib import Path



def main():
    saved_files = Path("games_archive").glob("*.txt")
    total_games = 0
    sucess_games = 0
    for file in saved_files:
        games_str = file.read_text()
        games = games_str.splitlines()
        for game in games:
            move_sequence = game.split(",")
            data = encode_game(move_sequence)
            decoded_sequence = decode_game(data)
            if move_sequence != decoded_sequence:
                print("FAIL")
            else:
                print("SUCCESS")
                sucess_games+=1
            total_games+=1
    print(f"{sucess_games}/{total_games}")



if __name__ == "__main__":
    main()
