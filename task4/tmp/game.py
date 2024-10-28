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

        if role == 'MASTER':
            self.annoncer = threading.Thread(target=self.announce, args=(self.model,self.binder,))
            self.requester = threading.Thread(target=self.handing_requests, args=(self.model, self.binder))
        
        self.last_move_time = pg.time.get_ticks()

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

        self.role = role
        self.last_send_time = pg.time.get_ticks()

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

                strMes = str(mes[0])
                print(strMes)
                
                if 'join' in strMes:
                    if 'NORMAL' in strMes:
                        snake = Snake(model, BLUE)
                        rid = model.reg_snake(snake, mes[0].join.player_name, 'NORMAL', mes[1])
                        mes1 = model.get_ackMsg(rid, mes[0].msg_seq)
                        binder.send_other(mes1.SerializeToString(), mes[1])
                    elif 'VIEWER' in strMes:
                        rid = model.reg_viewer(mes[0].join.player_name, 'VIEWER', mes[1])
                        mes1 = model.get_ackMsg(rid, mes[0].msg_seq)
                        binder.send_other(mes1.SerializeToString(), mes[1])
                elif 'steer' in strMes:
                    direct = self.model.STDtoMY(mes[0].steer.direction)
                    name = self.model.rewAddrs[mes[1]]
                    with self.model.lock:
                        newSnake = self.model.rewSnakes[name]
                        _ = self.model.snakes.pop(newSnake)
                        newSnake.direction = direct
                        self.model.snakes[newSnake] = name
                        self.model.rewSnakes[name] = newSnake

    def handle_events(self):
        control = self.model.get_control()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key == control[0] and self.snake != None:
                    self.snake.change_direction((0, -1))
                elif event.key == control[0] and self.model.role == 'NORMAL':
                    self.sendDir((0, -1))
                    self.last_send_time = pg.time.get_ticks()
                elif event.key == control[1] and self.snake != None:
                    self.snake.change_direction((0, 1))
                elif event.key == control[1] and self.model.role == 'NORMAL':
                    self.sendDir((0, 1))
                    self.last_send_time = pg.time.get_ticks()
                elif event.key == control[2] and self.snake != None:
                    self.snake.change_direction((-1, 0))
                elif event.key == control[2] and self.model.role == 'NORMAL':
                    self.sendDir((-1, 0))
                    self.last_send_time = pg.time.get_ticks()
                elif event.key == control[3] and self.snake != None:
                    self.snake.change_direction((1, 0))
                elif event.key == control[3] and self.model.role == 'NORMAL':
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

        addrsWithNames = self.model.get_addrs()
        addrs = addrsWithNames.values()

        for addr in addrs:
            self.binder.send_other(mes.SerializeToString(), addr)

    def run(self):
        state_delay = self.model.get_state_delay()

        while self.running:
            self.need_to_send = True

            if self.role != 'MASTER':
                if not self.binder.messages.empty():
                    with self.binder.lock:
                        tmp = self.binder.messages.get()
                    self.model.changeModel(tmp, self)

            self.handle_events()

            snakes = self.model.get_snakes()
            current_time = pg.time.get_ticks()

            if self.role == 'MASTER':
                if current_time - self.last_move_time > state_delay:
                    for snake in snakes:
                        snake.move()
                        
                    self.last_move_time = current_time

                    self.check_food()

                    tempDel = []

                    snakeKeys = snakes.keys()

                    for snake in snakeKeys:
                        if snake.check_collision(snakeKeys):
                            tempDel.append(snake)

                    for snake in tempDel:
                        body = self.model.remove_snake(snake)
                        self.gen_food(body)
                        
                    self.sendStates()
                
                self.add_food()

            if self.role != 'MASTER':
                if current_time - self.last_send_time > state_delay / 10:
                    self.sendPing()

            self.view.draw_window(self.foods)

            pg.display.flip()
            self.clock.tick(self.model.fps)

            #if self.role == 'MASTER':
            #    if self.model.get_snakes_size() == 0:
            #        self.running = False
        
        pg.quit()
        self.binder.stop()
