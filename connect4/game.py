import requests
import json

class Game:
    def __init__(self, bot, game_id):
        print("Creating new game")
        self.bot = bot
        self.id = game_id
        self.board = [
            [0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0]
        ]

        self.tries = 0
        self.remaining_moves = None
        self.player_one = None
        self.player_two = None
        self.player_one_turn = None
        self.winner = None
        self.ended = None
        self.player_move = None

    def __check_turn__(self):
        return self.player_one == self.bot.id and self.player_one_turn or not self.player_one_turn
    
    def __make_move__(self):
        if not self.ended and self.__check_turn__():
            print("Making a move.")
            status_code = 0
            while status_code != 200 and self.tries < 3:
                color = 1 if self.bot.id == self.player_one else 2
                column = self.bot.handler(self.board, color, self.tries > 0)
                print("Calculated column: " + str(column))
                self.tries += 1
                if 0 <= column < 7:
                    res = self.bot.wrap_request(requests.put, self.bot.address + "/v1/game/" + self.id, json={"column": column})
                    status_code = res.status_code
                else:
                    raise Exception("Invalid move. The handler must return a number between 0 and 6")
            if status_code == 200:
                self.tries = 0
            else:
                raise Exception("Failed three times to send move")

    def update(self):
        print("Querying game data")
        response = self.bot.wrap_request(requests.get, self.bot.address + "/v1/game/" + self.id)
        if response.status_code != 200:
            raise Exception("Failed to retrieve game data. Status code: " + str(response.status_code))
        data = json.loads(response.text)
        self.board = data["board"]["board"]
        self.remaining_moves = data["board"]["remainingMoves"]
        self.player_one = data["playerOne"]["_id"]
        self.player_two = data["playerTwo"]["_id"]
        self.player_one_turn = data["playerOneTurn"]
        if "winner" in data:
            self.winner = data["winner"]["username"]
        if "ended" in data:
            self.ended = data["ended"]
        self.__make_move__()
        

        
    
    