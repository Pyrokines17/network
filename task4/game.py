from game_objects import *
from snakes_pb2 import *
from network import *
from model import *
from view import *

import random as rnd
import pygame as pg

import threading
import time

class Game:
    def __init__(self, role):
        self.binder = Binder()
        self.binder.start()

        self.view = View()
        self.model = Model(self.view, role, self.binder)

        if self.model.end:
            self.end = True
            return
        else:
            self.end = False

        self.view.model = self.model
        
        pg.init()
        pg.display.set_caption('Snakes') 

        self.annoncer = threading.Thread(target=self.announce, args=(self.model,self.binder,))
        self.requester = threading.Thread(target=self.handing_requests, args=(self.model, self.binder))
        
        self.screen = pg.display.set_mode(self.model.window)
        self.view.screen = self.screen
        self.clock = pg.time.Clock()

        self.running = True
        self.counter = 0
        self.foods = []

        if role == 'MASTER':
            self.snake = Snake(self.model, (128, 0, 128))
            self.model.reg_snake(self.snake, self.model.name, 'MASTER', ('127.0.0.1', 9999))
        else:
            self.snake = None

        #self.add_bots()

        if role == 'MASTER':
            self.annoncer.start()
            self.requester.start()

        self.binder.stopMul()

        self.depId = None
        self.last_ping_time = {}
        self.lock = threading.Lock()
        self.role = self.model.get_role()

        self.last_master_hb = pg.time.get_ticks()
        self.last_move_time = pg.time.get_ticks()
        self.last_send_time = pg.time.get_ticks()
        self.last_state_time = pg.time.get_ticks()

    def add_bots(self):
        for i in range(5):
            self.model.reg_snake(Snake(self.model), get_random_name(separator='-', style='lowercase'), 'NORMAL')

    def announce(self, model, binder):
        while self.running:
            gameMsg = model.get_annMsg()
            binder.send_other(gameMsg.SerializeToString(), (MULTICAST_GROUP, MULTICAST_PORT))
            time.sleep(1)

    def handing_requests(self, model, binder):
        mes = None
        mes1 = None

        while self.running:
            if not binder.messages.empty():
                with binder.lock:
                    mes = binder.messages.get()
                
                if mes[0].HasField('join'):
                    plType = mes[0].join.requested_role
                    if plType == NodeRole.NORMAL:
                        snake = Snake(model, BLUE)
                        if snake.fall == True:
                            mes1 = model.get_errorMsg('No free space for new snake', mes[0].msg_seq)
                            binder.send_other(mes1.SerializeToString(), mes[1])
                        else:
                            rid = model.reg_snake(snake, mes[0].join.player_name, 'NORMAL', mes[1])
                            mes1 = model.get_ackMsg(rid, mes[0].msg_seq)
                            binder.send_other(mes1.SerializeToString(), mes[1])
                    elif plType == NodeRole.VIEWER:
                        rid = model.reg_viewer(mes[0].join.player_name, 'VIEWER', mes[1])
                        mes1 = model.get_ackMsg(rid, mes[0].msg_seq)
                        binder.send_other(mes1.SerializeToString(), mes[1])
                elif mes[0].HasField('steer'):
                    direct = self.model.STDtoMY(mes[0].steer.direction)
                    with self.model.lock:
                        id = self.model.rewAddrs[mes[1]]
                        newSnake = self.model.rewSnakes[id]
                        _ = self.model.snakes.pop(newSnake)
                        newSnake.direction = direct
                        self.model.snakes[newSnake] = id
                        self.model.rewSnakes[id] = newSnake
                elif mes[0].HasField('ping'):
                    with self.lock:
                        self.last_ping_time[mes[0].sender_id] = pg.time.get_ticks()

    def handle_events(self):
        control = self.model.get_control()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                myRole = self.model.get_role()
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key == control[0] and self.snake != None:
                    self.snake.change_direction((0, -1))
                elif event.key == control[0] and myRole in ['NORMAL', 'DEPUTY']:
                    self.sendDir((0, -1))
                    self.last_send_time = pg.time.get_ticks()
                elif event.key == control[1] and self.snake != None:
                    self.snake.change_direction((0, 1))
                elif event.key == control[1] and myRole in ['NORMAL', 'DEPUTY']:
                    self.sendDir((0, 1))
                    self.last_send_time = pg.time.get_ticks()
                elif event.key == control[2] and self.snake != None:
                    self.snake.change_direction((-1, 0))
                elif event.key == control[2] and myRole in ['NORMAL', 'DEPUTY']:
                    self.sendDir((-1, 0))
                    self.last_send_time = pg.time.get_ticks()
                elif event.key == control[3] and self.snake != None:
                    self.snake.change_direction((1, 0))
                elif event.key == control[3] and myRole in ['NORMAL', 'DEPUTY']:
                    self.sendDir((1, 0))
                    self.last_send_time = pg.time.get_ticks()

    def sendDir(self, direct):
        mes = self.model.get_steerMsg(direct)
        self.binder.send_other(mes.SerializeToString(), self.model.conn)

    def sendPing(self):
        mes = self.model.get_pingMsg()
        self.binder.send_other(mes.SerializeToString(), self.model.conn)

    def check_food(self):
        snakes = self.model.get_snakes()

        for food in self.foods[:]:
            for snake in snakes:
                if snake.body[0] == food.position:
                    snake.grow()
                    self.foods.remove(food)
                    self.model.update_score(snake)
                    break

    def add_food(self):
        food_count = self.model.get_all_food()

        while len(self.foods) < food_count:
            self.foods.append(Food(self.model))

    def gen_food(self, coords):
        for coord in coords:
            ch = rnd.randint(0, 1)
            
            if ch == 1:
                self.foods.append(Food(self.model, coord))

    def sendStates(self):
        mes = self.model.get_stateMsg(self.model, self.foods)
        
        with self.model.lock:
            addrsWithNames = self.model.addrs
            addrs = addrsWithNames.values()
            for addr in addrs:
                self.binder.send_other(mes.SerializeToString(), addr)

    def run(self):
        state_delay = self.model.get_state_delay()

        #pg.mixer.music.load('wasd.mp3')
        #pg.mixer.music.play(-1)

        while self.running:
            if self.role != 'MASTER':
                if not self.binder.messages.empty():
                    self.last_master_hb = pg.time.get_ticks()
                    with self.binder.lock:
                        tmp = self.binder.messages.get()
                    if tmp[0].HasField('state'):
                        self.model.changeModel(tmp, self)
                    elif tmp[0].HasField('role_change'):
                        if tmp[0].role_change.receiver_role == NodeRole.DEPUTY:
                            self.model.changeRole(tmp[0])
                            self.role = self.model.get_role()
                        else:
                            with self.model.lock:
                                self.model.lastState = tmp[0].state.state.state_order
                                self.model.mid = tmp[0].sender_id
                                self.model.conn = tmp[1]

            self.handle_events()

            if self.role == 'MASTER':
                current_time = pg.time.get_ticks()

                if current_time - self.last_move_time > state_delay:
                    self.last_move_time = current_time
                    snakes = self.model.get_snakes()
                    snakeKeys = snakes.keys()

                    for snake in snakes:
                        snake.move()
                        
                    self.check_food()

                    tempDel = []

                    for snake in snakeKeys:
                        if snake.check_collision(snakeKeys):
                            tempDel.append(snake)

                    for snake in tempDel:
                        body = self.model.remove_snake(snake)
                        self.gen_food(body)
                        
                current_time = pg.time.get_ticks()

                if current_time - self.last_state_time > state_delay / 10:
                    self.last_state_time = current_time
                    self.sendStates()
                
                current_time = pg.time.get_ticks()

                if self.depId != None:
                    with self.lock:
                        diff = current_time - self.last_ping_time[self.depId]
                    if diff > state_delay * 0.8:
                        with self.model.lock:
                            self.model.roles[self.depId] = 'NORMAL'
                        self.depId = None
                else:
                    with self.lock:
                        for key in self.last_ping_time.keys():
                            diff = current_time - self.last_ping_time[key]
                            if diff < state_delay * 0.8:
                                with self.model.lock:
                                    if self.model.roles[key] != 'NORMAL':
                                        continue
                                    self.model.roles[key] = 'DEPUTY'
                                    addr = self.model.addrs[key]
                                mes = self.model.get_changeMsg('DEPUTY', key)
                                self.binder.send_other(mes.SerializeToString(), addr)
                                self.depId = key
                                break   
                
                self.add_food()

            if self.role == 'DEPUTY':
                current_time = pg.time.get_ticks()

                if current_time - self.last_master_hb > state_delay * 0.8:
                    with self.lock:
                        self.role = 'MASTER'
                    with self.model.lock:
                        self.model.role = 'MASTER'
                        self.model.roles[self.model.mid] = 'NORMAL'
                        self.model.roles[self.model.myId] = 'MASTER'
                        self.snake = self.model.rewSnakes[self.model.myId]
                    self.annoncer.start()
                    self.requester.start()
                    with self.model.lock:
                        addrs = self.model.addrs
                        keys = addrs.keys()
                        roles = self.model.roles
                        for key in keys:
                            if key != self.model.myId:
                                mes = self.model.get_changeMsg(roles[key], key)
                                self.binder.send_other(mes.SerializeToString(), addrs[key])
                    
            if self.role != 'MASTER':
                current_time = pg.time.get_ticks()

                if current_time - self.last_send_time > state_delay / 10:
                    self.last_send_time = current_time
                    self.sendPing()

            self.view.draw_window(self.foods)

            pg.display.flip()
            self.clock.tick(self.model.fps)
        
        pg.quit()
        self.binder.stop()
