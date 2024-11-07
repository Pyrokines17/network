from unique_names_generator import get_random_name

from snakes_pb2 import *
from network import *
from view import *

import game_objects as go
import pygame as pg

import threading

class Model:
    def __init__(self, view, role, binder):
        self.lastState = -1
        self.idCounter = 0
        self.counter = 0
        self.stateId = 0
        self.myId = 0

        self.viewId = []

        if role == 'MASTER':
            settings = view.get_settings()
            self.end = False
        elif role == 'JOINER':
            try:
                settings, self.conn = view.get_other_settings(binder)
            except ValueError as e:
                self.end = True
                binder.stopMul()
                binder.stop()
                return
            
            try:
                mes = self.get_joinMsg(settings)
                binder.send_other(mes.SerializeToString(), self.conn)
                self.waitAnswear(binder)
            except Exception as e:
                self.end = True
                binder.stopMul()
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
                if answear[0].HasField('error'):
                    raise Exception(answear[0].error.error_message)
                elif answear[0].HasField('ack'):
                    self.myId = answear[0].receiver_id
                    self.mid = answear[0].sender_id
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
            
    def changeModel(self, mes, game):
        self.idCounter = 0
        self.emptyModel()
        self.viewId = []
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
                self.idCounter += 1
                self.roles[player.id] = role
                if role == 'VIEWER':
                    self.viewId.append(player.id)
                self.names[player.id] = name
                self.scores[player.id] = player.score
                self.addrs[player.id] = (player.ip_address, player.port)
                self.rewAddrs[(player.ip_address, player.port)] = player.id

        for snake in snakes:
            if snake.player_id == self.myId:
                color = (128, 0, 128)
            else:
                color = BLUE

            initSnake = go.Snake(self, color, True, snake.points, snake.head_direction)

            with self.lock:
                self.snakes[initSnake] = snake.player_id
                self.rewSnakes[snake.player_id] = initSnake

        for food in foods:
            game.foods.append(go.Food(self, (food.x*ts, food.y*ts)))

    def changeRole(self, mes):
        role = self.firRole[mes.role_change.receiver_role]
        with self.lock:
            self.role = role

    def get_myId(self):
        with self.lock:
            return self.myId
        
    def get_myName(self):
        with self.lock:
            return self.name

    def get_game_name(self):
        with self.lock:
            return self.gameName
        
    def get_host(self):
        roles = self.get_roles()
        
        for id in roles:
            if roles[id] == 'MASTER':
                return self.names[id]
            if roles[id] == 'DEPUTY':
                return self.names[id]
        
        return 'UNKNOWN'

    def get_annMsg(self):
        gameMsg = GameMessage()
        annMsg = gameMsg.announcement.games.add()

        gamePlayers = GamePlayers()
        gameAnn = GameAnnouncement()

        addrs = self.get_addrs()
        names = self.get_names()
        roles = self.get_roles()
        scores = self.get_scores()
        snakes = self.get_snakes()
        iters = snakes.keys()

        for snake in iters:
            gamePlayer = gamePlayers.players.add()
            id = snakes[snake]
            strRole = roles[id]
            gamePlayer.name = names[id]
            gamePlayer.id = id
            gamePlayer.ip_address = addrs[id][0]
            gamePlayer.port = addrs[id][1]
            gamePlayer.role = self.secRole[strRole]
            gamePlayer.score = scores[id]

        gameAnn.config.CopyFrom(self.gameCon)
        gameAnn.game_name = self.gameName
        gameAnn.players.CopyFrom(gamePlayers)

        annMsg.CopyFrom(gameAnn)
        gameMsg.msg_seq = self.counter
        gameMsg.sender_id = self.myId
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
    
    def get_ackMsg(self, rid, seq):
        gameMsg = GameMessage()
        gameMsg.ack.SetInParent()
        gameMsg.msg_seq = seq
        gameMsg.sender_id = self.myId
        gameMsg.receiver_id = rid
        return gameMsg
    
    def get_errorMsg(self, text, seq):
        gameMsg = GameMessage()
        gameMsg.error.error_message = text
        gameMsg.msg_seq = seq
        gameMsg.sender_id = self.myId
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
        names = model.get_names()
        addrs = model.get_addrs()

        for snake in iters:
            id = snakes[snake]
            strRole = roles[id]

            tmp = gameState.snakes.add()

            tmp.player_id = id
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

            gamePlayer.id = id
            gamePlayer.name = names[id]
            gamePlayer.ip_address = addrs[id][0]
            gamePlayer.port = addrs[id][1]
            gamePlayer.score = scores[id]
            gamePlayer.role = self.secRole[strRole]

        for id in self.viewId:
            gamePlayer = gamePlayers.players.add()
            gamePlayer.id = id
            gamePlayer.name = names[id]
            gamePlayer.ip_address = addrs[id][0]
            gamePlayer.port = addrs[id][1]
            gamePlayer.score = scores[id]
            gamePlayer.role = self.secRole[roles[id]]

        for food in foods:
            tmp = gameState.foods.add()
            tmp.x = int(food.position[0]/ts)
            tmp.y = int(food.position[1]/ts)

        gameState.players.CopyFrom(gamePlayers)
        gameMsg.state.state.CopyFrom(gameState)
        gameMsg.msg_seq = self.counter
        gameMsg.sender_id = self.myId
        self.counter += 1

        return gameMsg
    
    def get_steerMsg(self, direct):
        gameMsg = GameMessage()
        gameMsg.steer.direction = self.MYtoSTD(direct)
        gameMsg.msg_seq = self.counter
        gameMsg.sender_id = self.myId
        gameMsg.receiver_id = self.mid
        self.counter += 1
        return gameMsg
    
    def get_pingMsg(self):
        gameMsg = GameMessage()
        gameMsg.ping.SetInParent()
        gameMsg.msg_seq = self.counter
        gameMsg.sender_id = self.myId
        gameMsg.receiver_id = self.mid
        self.counter += 1
        return gameMsg
    
    def get_changeMsg(self, role, id):
        gameMsg = GameMessage()
        gameMsg.role_change.sender_role = self.secRole[self.role]
        gameMsg.role_change.receiver_role = self.secRole[role]
        gameMsg.msg_seq = self.counter
        gameMsg.sender_id = self.myId
        gameMsg.receiver_id = id
        self.counter += 1
        return gameMsg
    
    def get_names(self):
        with self.lock:
            return self.names
    
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
            self.rewAddrs[addr] = self.idCounter
            self.addrs[self.idCounter] = addr
            self.names[self.idCounter] = name
            self.roles[self.idCounter] = role
            self.scores[self.idCounter] = 0
            self.viewId.append(self.idCounter)
            self.idCounter += 1
        
        return self.idCounter-1
        
    def reg_snake(self, snake, name, role, addr):
        with self.lock:
            if role == 'MASTER':
                self.mid = self.idCounter

            self.rewSnakes[self.idCounter] = snake
            self.rewAddrs[addr] = self.idCounter
            self.snakes[snake] = self.idCounter
            self.addrs[self.idCounter] = addr
            self.names[self.idCounter] = name
            self.scores[self.idCounter] = 0
            self.roles[self.idCounter] = role

            self.idCounter += 1
            self.all_food += 1

        return self.idCounter-1

    def remove_snake(self, snake):
        body = snake.body

        with self.lock:
            id = self.snakes[snake]
            del self.rewSnakes[id]
            del self.snakes[snake]
            del self.scores[id]
            self.roles[id] = 'VIEWER'
            self.all_food -= 1

        return body

    def get_snakes_size(self):
        with self.lock:
            return len(self.snakes)
    
    def get_snakes(self):
        with self.lock:
            return self.snakes
        
    def get_roles(self):
        with self.lock:
            return self.roles
        
    def get_role(self):
        with self.lock:
            return self.role
        
    def get_scores(self):
        with self.lock:
            return self.scores
        
    def update_score(self, snake):
        with self.lock:
            id = self.snakes[snake]
            self.scores[id] += 1
        
    def get_name_score(self, snake):
        with self.lock:
            id = self.snakes[snake]
            name = self.names[id]
            return name, self.scores[id]
        
    def get_all_food(self):
        with self.lock:
            length = len(self.snakes)
        
        return self.food_static+length
        
    def get_addrs(self):
        with self.lock:
            return self.addrs
