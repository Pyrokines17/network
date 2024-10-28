from unique_names_generator import get_random_name

from snakes_pb2 import *
from network import *
from view import *

import game_objects as go
import random as rnd
import pygame as pg

import threading

class Model:
    def __init__(self, view, role, binder):
        self.lastState = -1
        self.idCounter = 0
        self.counter = 0
        self.stateId = 0
        self.myId = 0

        if role == 'MASTER':
            settings = view.get_settings()
            self.end = False
        elif role == 'JOINER':
            try:
                settings, self.conn = view.get_other_settings(binder)
            except ValueError as e:
                self.end = True
                binder.stop()
                return
            
            try:
                mes = self.get_joinMsg(settings)
                binder.send_other(mes.SerializeToString(), self.conn)
                self.waitAnswear(binder)
            except Exception as e:
                self.end = True
                binder.stop()
                print(e)
                return
            
            self.end = False
        
        self.lock = threading.Lock()

        self.secRole = {
            'NORMAL': NodeRole.NORMAL,
            'MASTER': NodeRole.MASTER,
            'DEPUTY': NodeRole.DEPUTY,
            'VIEWER': NodeRole.VIEWER
        }
        self.firRole = {
            NodeRole.NORMAL : 'NORMAL',
            NodeRole.MASTER : 'MASTER',
            NodeRole.DEPUTY : 'DEPUTY',
            NodeRole.VIEWER : 'VIEWER'
        }

        self.tile_count = settings['tile_count']
        self.window = settings['resolution']
        self.name = settings['name']

        if role == 'MASTER':
            self.gameName = get_random_name(separator='-', style='lowercase')
            self.role = 'MASTER'
        elif role == 'JOINER':
            self.gameName = settings['game_name']
            self.role = settings['role']
        
        self.state_delay = settings['state_delay']
        self.food_static = settings['food_count']
        self.all_food = self.food_static
        self.fps = settings['fps']

        self.gameCon = GameConfig()
        self.gameCon.width = self.tile_count[0]
        self.gameCon.height = self.tile_count[1]
        self.gameCon.food_static = self.food_static
        self.gameCon.state_delay_ms = self.state_delay

        self.game_place = [self.window[0]//3*2, self.window[1]]

        self.tile_size = min([self.game_place[0]//self.tile_count[0], 
                              self.game_place[1]//self.tile_count[1]])
        
        self.tile_place = [self.tile_count[0]*self.tile_size,
                            self.tile_count[1]*self.tile_size]
        
        self.shift = [(self.game_place[0]-self.tile_place[0])/2, 
                      (self.game_place[1]-self.tile_place[1])/2]
        
        if settings['control'] == 'WASD':
            self.control = [pg.K_w, pg.K_s, pg.K_a, pg.K_d]
        elif settings['control'] == 'Arrows':
            self.control = [pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT]
        
        self.emptyModel()

    def waitAnswear(self, binder):
        answear = None

        while True:
            if not binder.messages.empty():
                with binder.lock:
                    answear = binder.messages.get()
                if 'error' in str(answear[0]):
                    raise Exception(answear[0].error.error_message)
                else:
                    self.myId = answear[0].receiver_id
                    break

    def MYtoSTD(self, direct):
        match direct:
            case (0, 1):
                return Direction.DOWN
            case (0, -1):
                return Direction.UP
            case (1, 0):
                return Direction.RIGHT
            case (-1, 0):
                return Direction.LEFT

    def STDtoMY(self, direct):
        match direct:
            case Direction.DOWN:
                return (0, 1)
            case Direction.UP:
                return (0, -1)
            case Direction.RIGHT:
                return (1, 0)
            case Direction.LEFT:
                return (-1, 0)
            
    def emptyModel(self):
        self.rewSnakes = {}
        self.rewAddrs = {}
        self.snakes = {}
        self.addrs = {}
        self.names = {}
        self.scores = {}
        self.roles = {}
        self.ids = {}
            
    def changeModel(self, mes, game):
        self.emptyModel()
        game.foods = []

        gameState = mes[0].state.state
        ts = self.get_tile_size()
        
        if gameState.state_order <= self.lastState:
            return
        
        self.lastState = gameState.state_order
        players = gameState.players.players
        snakes = gameState.snakes
        foods = gameState.foods

        for player in players:
            name = player.name
            role = self.firRole[player.role]

            with self.lock:
                self.roles[name] = role
                self.ids[name] = player.id
                self.names[player.id] = name
                self.scores[name] = player.score

        for snake in snakes:
            with self.lock:
                name = self.names[snake.player_id]

            if snake.player_id == self.myId:
                color = (128, 0, 128)
            else:
                color = BLUE

            initSnake = go.Snake(self, color, True, snake.points, snake.head_direction)

            with self.lock:
                self.snakes[initSnake] = name

        for food in foods:
            game.foods.append(go.Food(self, (food.x*ts, food.y*ts)))

    def get_game_name(self):
        with self.lock:
            return self.gameName
        
    def get_host(self):
        roles = self.get_roles()
        
        for name in roles:
            if roles[name] == 'MASTER':
                return name
            if roles[name] == 'DEPUTY':
                return name
        
        return 'UNKNOWN'

    def get_annMsg(self):
        gameMsg = GameMessage()
        annMsg = gameMsg.announcement.games.add()

        gamePlayers = GamePlayers()
        gameAnn = GameAnnouncement()

        ids = self.get_ids()
        roles = self.get_roles()
        scores = self.get_scores()
        snakes = self.get_snakes()

        for snake in snakes:
            gamePlayer = gamePlayers.players.add()
            name = snakes[snake]
            strRole = roles[name]
            gamePlayer.name = name
            gamePlayer.id = ids[name]
            gamePlayer.score = scores[name]
            gamePlayer.role = self.secRole[strRole]

        gameAnn.config.CopyFrom(self.gameCon)
        gameAnn.game_name = self.gameName
        gameAnn.players.CopyFrom(gamePlayers)

        annMsg.CopyFrom(gameAnn)
        gameMsg.msg_seq = self.counter
        self.counter += 1

        return gameMsg
    
    def get_joinMsg(self, config):
        gameMsg = GameMessage()
        gameMsg.join.player_name = config.get('name')
        gameMsg.join.game_name = config.get('game_name')

        if config.get('role') == 'NORMAL':
            gameMsg.join.requested_role = NodeRole.NORMAL
        elif config.get('role') == 'VIEWER':
            gameMsg.join.requested_role = NodeRole.VIEWER

        gameMsg.msg_seq = self.counter
        self.counter += 1

        return gameMsg
    
    def get_ackMsg(self, rid):
        gameMsg = GameMessage()
        gameMsg.msg_seq = self.counter
        self.counter += 1

        gameMsg.sender_id = self.mid
        gameMsg.receiver_id = rid

        return gameMsg
    
    def get_errorMsg(self, text):
        gameMsg = GameMessage()
        gameMsg.error.error_message = text
        return gameMsg
    
    def get_stateMsg(self, model, foods):
        gameMsg = GameMessage()
        gameState = GameState()
        gamePlayers = GamePlayers()

        gameState.state_order = self.stateId
        self.stateId += 1

        snakes = model.get_snakes()
        iters = snakes.keys()

        scores = model.get_scores()
        ts = model.get_tile_size()
        roles = model.get_roles()
        ids = model.get_ids()

        for snake in iters:
            name = snakes[snake]
            strRole = roles[name]

            tmp = gameState.snakes.add()
            tmp.player_id = ids[name]
            tmp.state = GameState.Snake.SnakeState.ALIVE
            tmp.head_direction = self.MYtoSTD(snake.direction)
            gamePlayer = gamePlayers.players.add()
            coords = snake.body

            fir = tmp.points.add()
            fir.x = int(coords[0][0]/ts)
            fir.y = int(coords[0][1]/ts)
            clen = len(coords)

            for i in range(1, clen):
                tmpCoord = tmp.points.add()
                tmpCoord.x = int((coords[i][0]-coords[i-1][0])/ts)
                tmpCoord.y = int((coords[i][1]-coords[i-1][1])/ts)

            gamePlayer.name = name
            gamePlayer.id = ids[name]
            gamePlayer.score = scores[name]
            gamePlayer.role = self.secRole[strRole]

        for food in foods:
            tmp = gameState.foods.add()
            tmp.x = int(food.position[0]/ts)
            tmp.y = int(food.position[1]/ts)

        gameState.players.CopyFrom(gamePlayers)
        gameMsg.state.state.CopyFrom(gameState)
        gameMsg.msg_seq = self.counter
        self.counter += 1

        return gameMsg
    
    def get_steerMsg(self, direct):
        gameMsg = GameMessage()
        gameMsg.steer.direction = self.MYtoSTD(direct)
        gameMsg.msg_seq = self.counter
        self.counter += 1
        return gameMsg
    
    def get_control(self):
        with self.lock:
            return self.control

    def get_tile_count(self):
        with self.lock:
            return self.tile_count
        
    def get_window(self):
        with self.lock:
            return self.window
        
    def get_food_static(self):
        with self.lock:
            return self.food_static
        
    def get_state_delay(self):
        with self.lock:
            return self.state_delay
        
    def get_game_place(self):
        with self.lock:
            return self.game_place
    
    def get_tile_size(self):
        with self.lock:
            return self.tile_size
        
    def get_tile_place(self):
        with self.lock:
            return self.tile_place
        
    def get_shift(self):
        with self.lock:
            return self.shift
        
    def reg_viewer(self, name, role, addr):
        with self.lock:
            self.ids[name] = self.idCounter
            self.roles[name] = role
            self.addrs[name] = addr
            self.idCounter += 1
        
        return self.ids[name]
        
    def reg_snake(self, snake, name, role, addr):
        with self.lock:
            if role == 'MASTER':
                self.mid = self.idCounter

            self.ids[name] = self.idCounter
            self.rewSnakes[name] = snake
            self.snakes[snake] = name
            self.rewAddrs[addr] = name
            self.addrs[name] = addr
            self.roles[name] = role
            self.scores[name] = 0
            self.idCounter += 1
            self.all_food += 1

        return self.ids[name]

    def remove_snake(self, snake):
        body = snake.body
        dep_flag = False

        roles = self.get_roles()
        snakes = self.get_snakes()

        del_role = roles[snakes[snake]]

        if del_role == 'MASTER' or del_role == 'DEPUTY':
            dep_flag = True

        with self.lock:
            name = self.snakes[snake]
            del self.snakes[snake]
            del self.roles[name]
            del self.scores[name]
            del self.ids[name]
            self.all_food -= 1

        new_snakes = self.get_snakes()

        if dep_flag:
            new_dep = rnd.choice(list(new_snakes.values()))

            with self.lock:
                self.roles[new_dep] = 'DEPUTY'

        return body

    def get_snakes_size(self):
        with self.lock:
            return len(self.snakes)
    
    def get_snakes(self):
        with self.lock:
            return self.snakes
    
    def get_ids(self):
        with self.lock:
            return self.ids
        
    def get_roles(self):
        with self.lock:
            return self.roles
        
    def get_scores(self):
        with self.lock:
            return self.scores
        
    def update_score(self, snake):
        with self.lock:
            name = self.snakes[snake]
            self.scores[name] += 1
        
    def get_name_score(self, snake):
        with self.lock:
            name = self.snakes[snake]
            return name, self.scores[name]
        
    def get_all_food(self):
        with self.lock:
            length = len(self.snakes)
        
        return self.food_static+length
        
    def get_addrs(self):
        with self.lock:
            return self.addrs
