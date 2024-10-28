from model import *
from view import *

import random as rnd
import pygame as pg

class Snake:
    def __init__(self, model, color=BLUE, flag=None, points=None, direct=None):
        tile_count = model.get_tile_count()
        tile_size = model.get_tile_size()
        
        self.tile_place = model.get_tile_place()
        self.tile_count = model.get_tile_count()
        self.tile_size = model.get_tile_size()
        self.shift = model.get_shift()
        self.model = model

        x = rnd.randint(1, tile_count[0]-2)
        y = rnd.randint(1, tile_count[1]-2)

        x1 = x*tile_size
        y1 = y*tile_size

        self.color = color

        if flag == None:
            self.body = [(x1, y1)]

            ch = rnd.randint(0, 3)

            match ch:
                case 0:
                    self.body.append((x1, y1+tile_size))
                    self.direction = (0, -1)
                case 1:
                    self.body.append((x1-tile_size, y1))
                    self.direction = (1, 0)
                case 2:
                    self.body.append((x1, y1-tile_size))
                    self.direction = (0, 1)
                case 3:
                    self.body.append((x1+tile_size, y1))
                    self.direction = (-1, 0)
        else:
            self.body = []
            first = True
            prewId = 0
            
            for coord in points:
                if first:
                    self.body.append((coord.x*tile_size, coord.y*tile_size))
                    first = False
                    continue
                prew = self.body[prewId]
                self.body.append((prew[0]+coord.x*tile_size, prew[1]+coord.y*tile_size))
                prewId += 1

            self.direction = model.STDtoMY(direct)

    def move(self):
        x_head, y_head = self.body[0]
        new_head = ((x_head+self.direction[0]*self.tile_size)%self.tile_place[0], 
                    (y_head+self.direction[1]*self.tile_size)%self.tile_place[1])
        self.body = [new_head] + self.body[:-1]

    def grow(self):
        self.body.append(self.body[-1])

    def change_direction(self, direction):
        if (-1*self.direction[0], -1*self.direction[1]) != direction:
            self.direction = direction

    def check_collision(self, snakes):
        head = self.body[0]

        if head in self.body[1:]:
            return True

        for snake in snakes:
            if snake == self:
                continue
            if head in snake.body:
                self.model.update_score(snake)
                return True
            
        return False

    def draw(self, screen):
        for segment in self.body:
            x = segment[0]+self.shift[0]
            y = segment[1]+self.shift[1]

            pg.draw.rect(screen, self.color, 
                         pg.Rect(x, y, self.tile_size, self.tile_size))
            
class Food:
    def __init__(self, model, coords=None):
        self.tile_count = model.get_tile_count()
        self.tile_size = model.get_tile_size()
        self.shift = model.get_shift()

        self.spawn(coords)

    def spawn(self, coords):
        if coords:
            self.position = (coords[0], coords[1])
        else:
            self.position = (rnd.randint(0, self.tile_count[0]-1)*self.tile_size, 
                            rnd.randint(0, self.tile_count[1]-1)*self.tile_size)
    
    def draw(self, screen):
        x = self.position[0]+self.shift[0]
        y = self.position[1]+self.shift[1]

        pg.draw.rect(screen, RED, 
                     pg.Rect(x, y, self.tile_size, self.tile_size))
        