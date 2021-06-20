import time
import requests
from requests.auth import HTTPBasicAuth
import datetime
import jwt
import socketio
from connect4.game import Game

class Bot:
    def __init__(self, address, username, password, ranked = False):
        if address is None:
            raise Exception('NoneType is not a valid address')
        if username is None:
            raise Exception('NoneType is not a valid username')
        if password is None:
            raise Exception('NoneType is not a valid password')
        self.address = address
        self.username = username
        self.password = password
        self.ranked = ranked

        self.headers = None
        self.token = None
        self.id = None
        self.expiry = None
        self.handler = None

        self.started = False
        self.io = socketio.Client()

        self.game = None

    def __socket_connect__(self):
        if self.io.connected:
            self.io.disconnect()
        self.io.connect(self.address, auth={
                "token":"Bearer " + self.token
            })
        self.__callbacks__()
        print("WebSocket connection established")
    
    def connect(self):
        if not self.handler:
            raise Exception("Missing game handler")

        response = requests.get(self.address + '/v1/login', auth=HTTPBasicAuth(self.username, self.password))
        if response.status_code == 200:
            self.headers = {'Authorization': "Bearer " + response.json()["token"]}
            jwt_decoded = jwt.decode(response.json()["token"], algorithms=["HS256"], options={"verify_signature": False})
            self.id = jwt_decoded["id"]
            self.expiry = datetime.datetime.fromtimestamp(jwt_decoded["exp"])
            self.token = response.json()["token"]
            self.started = True
            self.__socket_connect__()
            print("Authentication succeed")
        else:
            print("Authentication failed")
            if response.status_code == 401:
                raise Exception("Wrong username or password")
            else:
                raise Exception("Error occurred while connecting to the backend. Check the address.")


    # Checking token expiration
    def __check_expiry__(self):
        if self.expiry < datetime.datetime.now():
            print("JWT Token expired. Attempting relogin.")
            self.connect()
    
    # Checking if all variables are setted before doing any request
    def __check_request__(self):
        time.sleep(1)   # Delay to avoid spamming requests to the backend
        if not self.started:
            raise Exception("Please call the start() method before")
        if self.headers is None:
            raise Exception("Authentication header is not set")
        if self.id is None:
            raise Exception("User ID is not set")
        if self.expiry is None:
            raise Exception("Expiry is not set")
        self.__check_expiry__()

    # Requests wrapper
    def wrap_request(self, request, endpoint, json = None):
        self.__check_request__()
        if json:
            return request(endpoint, headers=self.headers, json=json)
        else:
            return request(endpoint, headers=self.headers)
    
    """Game handler setter
    Handler signature:
    board: int[][], color: int, failed: boolean -> column: int.

    board values:
    0 -> Empty cell
    1 -> Red Coin (First player)
    2 -> Yellow coin (Second player)
    
    color values:
    1 -> If bot use red coins
    2 -> If bot use yellow coins
    
    failed values:
    False -> First attempt
    True -> The previous request failed

    column:
    Must be a value between 0 and 6
    """
    def set_game_handler(self, handler):
        self.handler = handler

    def __subscribe__(self):
        self.__check_request__()
        if self.ranked:
            print("Subscribing for ranked")
            requests.put(self.address + "/v1/game/ranked", json={"subscribe":True}, headers=self.headers)
        else:
            print("Subscribing for scrimmage")
            requests.put(self.address + "/v1/game/scrimmage", json={"subscribe":True}, headers=self.headers)

    def start(self):
        self.__subscribe__()
        self.io.wait()

    def __callbacks__(self):    
        @self.io.on("game new")
        def __new__game_handler__(data):
            self.game = Game(self, data['id'])
            self.game.update()
            self.game.__make_move__()

        @self.io.on("game update")
        def __update_game_handler__():
            if self.game:
                self.game.update()
                self.game.__make_move__()
                if self.game.ended:
                    print("Game ended. Winner: " + str(self.game.winner))
                    self.game = None
                    self.__subscribe__() 
