import io
import chess
import chess.pgn
import requests
from pathlib import Path

def parse_games(pgn_text):
    pgn_file = io.StringIO(pgn_text)
    all_games = []

    while True:
        game = chess.pgn.read_game(pgn_file)         
        if game is None:         
            break

        moves_uci = []
        for move in game.mainline_moves():        
            moves_uci.append(move.uci())   
        all_games.append(moves_uci)

    return all_games


def save_game(url,folder_path):
    headers = {"User-Agent":"ASC-Chess-Implementation (anemosalouphs@gmail.com)"}
    response = requests.get(url,headers=headers)
    data = response.json()
    games_pgn = data['games']
    pgn_text = []
    for game_pgn in games_pgn:
        pgn_text.append(game_pgn["pgn"])
    final_string = str()
    for game in parse_games("\n\n".join(pgn_text)):
        game_line = ",".join(game)
        final_string = final_string+f"{game_line}\n"
    folder_path.write_text(final_string)
    print("Games saved succesfully")


def main():

    Path("games_archive").mkdir(exist_ok=True)
    name = input("Give a name: ")
    year = input("Give a year(2014-2026): ")
    if len(year)!=4 or not(year.isnumeric()) or (int(year)>2026 or int(year)<2014):
        print(f"{year} is not valid input exiting.")
        return
    month = input("Give a Month(number like 05): ")
    if len(month)!=2 or not(month.isnumeric()) or (int(month)>12 or int(month)<1):
        print(f"{month} is not valid input exiting.")
        return

    folder_path = Path("games_archive")/f"{name}_{year}_{month}.txt"
    url = f"https://api.chess.com/pub/player/{name}/games/{year}/{month}"
    if folder_path.exists():
        print("Game already exists do you want to pull it again?")
        choice = input("Y/N : ")
        if choice.lower()=="y":
            save_game(url,folder_path)
            return
        else:
            return
    save_game(url,folder_path)
    

    
    

if __name__ == "__main__":
    main()