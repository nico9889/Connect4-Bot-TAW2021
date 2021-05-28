import json
import jwt
import requests
import socketio
from requests.auth import HTTPBasicAuth
from random import randrange
from time import sleep
from datetime import datetime
import sys

base_url="https://backend.nico9889.me"

headers = {"Authorization": ""}
user_id = ""
expiry = None


ranked = False

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
        self.player_move = -1
    
    def updateGame(self, data):
        print("Updating game data")
        print("Computating difference")
        self.player_move = -1

        row = 0
        while self.player_move == -1 and row<6:
            column = 0
            while self.player_move == -1 and column<7:
                if data["board"]["board"][row][column] != self.board[row][column]:
                    self.player_move = column
                column+=1
            row +=1

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
        return (self.player_one["_id"] == user_id and self.player_one_turn) or (self.player_two["_id"] == user_id and not self.player_one_turn)

    def isEnded(self):
        print("Checking if game is ended")
        return self.ended

    def randomMove(self):
        print("Making a move")
        if not self.isEnded():
            col_min = 0
            col_max = 6
            if self.player_move != -1:
                print("Hunting player :)")
                col_min = self.player_move - 1 if self.player_move-1>0 else 0
                col_max = self.player_move + 1 if self.player_move-1<7 else 6
            column = randrange(col_min, col_max)
            sleep(1)
            print("Last column:" + str(self.board[0]))
            while self.board[0][column] != 0:
                column = randrange(0,7)
            check_token_expiration()
            requests.put(base_url + "/v1/game/" + self.id, json={"x":column}, headers=headers)

    def subscribe(self):
        requests.put(base_url + "/v1/game/" + self.id + "/spectate", json={"follow": True}, headers=headers)

def subscribe_game():
    global ranked
    if ranked:
        print("Subscribing for ranked")
        check_token_expiration()
        requests.put(base_url + "/v1/game/ranked", json={"subscribe":True}, headers=headers)
    else:
        print("Subscribing for scrimmage")
        check_token_expiration()
        requests.put(base_url + "/v1/game/scrimmage", json={"subscribe":True}, headers=headers)


def login(user, pasw):
    global headers, user_id, expiry
    response = requests.get(base_url + '/v1/login', auth=HTTPBasicAuth(user, pasw))
    headers["Authorization"] = "Bearer " + response.json()["token"]
    user_id = jwt.decode(response.json()["token"], algorithms=["HS256"], options={"verify_signature": False})["id"]
    expiry = datetime.fromtimestamp(jwt.decode(response.json()["token"], algorithms=["HS256"], options={"verify_signature": False})["exp"])
    return response.json()["token"]


def socket_connect(token):
    print("Connecting socket.io with token: " + token)
    if sio.connected:
        sio.disconnect
    sio.connect(base_url, auth={
        "token":"Bearer " + token
    })


@sio.on("game update")
def game_update():
    global game
    check_token_expiration()
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
    check_token_expiration()
    response = requests.get(base_url + "/v1/game/" + data['id'], headers=headers)
    game = Game(response.json(), data['id'])
    if game.isBotTurn():
        game.randomMove()


@sio.on("notification update")
def notification_update():
    check_token_expiration()
    response = requests.get(base_url + "/v1/notifications", headers=headers)
    print(response.json())


def check_token_expiration():
    delta = expiry-datetime.now()
    if delta.seconds < 300:
        connect()


def connect():
    token = login(user['user'], user['pass'])
    if token:
        socket_connect(token)
        if game is None:
            subscribe_game()
        else:
            game.subscribe()
        sio.wait()
    else:
        print("Startup failed. Invalid credentials")

if __name__ == '__main__':
    connect()