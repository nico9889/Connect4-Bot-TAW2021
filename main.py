from connect4.bot import Bot
from random import randrange
import json
import sys


prev_board = None

# Example handler
def handler(board, color, failed):
    if failed:
        raise Exception("Previous move failed. Can't handle.")
    global prev_board
    if prev_board == None:
        prev_board = board
        return randrange(0,7)
    else:
        player_move = -1

        row = 0
        while player_move == -1 and row<6:
            column = 0
            while player_move == -1 and column<7:
                if board[row][column] != prev_board[row][column]:
                    player_move = column
                column+=1
            row +=1
        col_min = 0
        col_max = 6
        if player_move != -1:
            print("Hunting player :)")
            col_min = max(player_move-1, 0)
            col_max = min(player_move + 1, 6)
        column = randrange(col_min, col_max)
        while board[0][column] != 0:
            column = randrange(0,7)
        return column

bot = Bot("endpoint here","your username here", "your password here")


bot.set_game_handler(handler)
bot.connect()
bot.start()