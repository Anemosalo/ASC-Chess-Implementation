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

def main():

    

    name = input("Give a name: ")
    year = input("Give a year(2014-2026): ")
    if len(year)!=4 or not(year.isnumeric()) or (int(year)>2026 or int(year)<2014):
        print(f"{year} is not valid input exiting.")
        return
    month = input("Give a Month(number like 05): ")
    if len(month)!=2 or not(month.isnumeric()) or (int(month)>12 or int(month)<1):
        print(f"{month} is not valid input exiting.")
        return
    url = f"https://api.chess.com/pub/player/{name}/games/{year}/{month}"
    headers = {"User-Agent":"ASC-Chess-Implementation (anemosalouphs@gmail.com)"}
    response = requests.get(url,headers=headers)
    data = response.json()
    games_pgn = data['games']
    pgn_text = []
    for game_pgn in games_pgn:
        pgn_text.append(game_pgn["pgn"])
    print(parse_games("\n\n".join(pgn_text)))

if __name__ == "__main__":
    main()