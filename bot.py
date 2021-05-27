import json
import jwt
import requests
import socketio
from requests.auth import HTTPBasicAuth
from random import randrange
from time import sleep
import sys

base_url="https://backend.nico9889.me"

headers = {"Authorization": ""}
user_id = ""

ranked = True

sio = socketio.Client()

with open('users.json', 'r') as f:
    users = json.loads(f.read())

user = users[int(sys.argv[1])]

game = None

class Game:
    def __init__(self, data, game_id):
        print("Creating new game")
        self.id = game_id
        self.board = data["board"]["board"]
        self.remaining_moves = data["board"]["remainingMoves"]
        self.player_one = data["playerOne"]
        self.player_two = data["playerTwo"]
        self.player_one_turn = data["playerOneTurn"]
        self.winner = None
        self.ended = False
    
    def updateGame(self, data):
        print("Updating game data")
        self.board = data["board"]["board"]
        self.remaining_moves = data["board"]["remainingMoves"]
        self.player_one = data["playerOne"]
        self.player_two = data["playerTwo"]
        self.player_one_turn = data["playerOneTurn"]
        if "winner" in data:
            self.winner = data["winner"]
        if "ended" in data:
            self.ended = data["ended"]

    def isBotTurn(self):
        global user_id
        print("Checking if is my turn")
        return (self.player_one == user_id and self.player_one_turn) or (self.player_two==user_id and not self.player_one_turn)

    def isEnded(self):
        print("Checking if game is ended")
        return self.ended

    def randomMove(self):
        print("Making a move")
        status = 0
        if not self.isEnded():
            column = randrange(0,7)
            sleep(1)
            print("Last column:" + str(self.board[0]))
            while self.board[0][column] != 0:
                column = randrange(0,7)
            response = requests.put(base_url + "/v1/game/" + self.id, json={"x":column}, headers=headers)


def login(user, pasw):
    global headers, user_id
    response = requests.get(base_url + '/v1/login', auth=HTTPBasicAuth(user, pasw))
    headers["Authorization"] = "Bearer " + response.json()["token"]
    user_id = jwt.decode(response.json()["token"], algorithms=["HS256"], options={"verify_signature": False})["id"]
    return response.json()["token"]

def subscribe_game():
    global ranked
    if ranked:
        print("Subscribing for ranked")
        requests.put(base_url + "/v1/game/ranked", json={"subscribe":True}, headers=headers)
    else:
        print("Subscribing for scrimmage")
        requests.put(base_url + "/v1/game/scrimmage", json={"subscribe":True}, headers=headers)


def socket_connect(token):
    print("Connecting socket.io with token: " + token)
    sio.connect(base_url, auth={
        "token":"Bearer " + token
    })

@sio.on("game update")
def game_update():
    global game
    response = requests.get(base_url + "/v1/game/" + game.id, headers=headers)
    game.updateGame(response.json())
    if not game.isEnded():
        if game.isBotTurn():
            game.randomMove()
    else:
        game = None
        subscribe_game()

@sio.on("game new")
def game_new(data):
    global game
    response = requests.get(base_url + "/v1/game/" + data['id'], headers=headers)
    game = Game(response.json(), data['id'])
    if game.isBotTurn():
        game.randomMove()


@sio.on("notification update")
def notification_update():
    response = requests.get(base_url + "/v1/notifications", headers=headers)
    print(response.json())

if __name__ == '__main__':
    token = login(user['user'], user['pass'])
    if token:
        socket_connect(token)
        subscribe_game()
        sio.wait()
    else:
        print("Startup failed. Invalid credentials")