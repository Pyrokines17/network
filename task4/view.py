from unique_names_generator import get_random_name

import pygame_gui as pgui
import pygame as pg

from snakes_pb2 import *
from model import *

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

RESOLUTIONS = [
    (1920, 1080),
    (1600, 900),
    (1366, 768),
    (1280, 720)
]

DEFAULT_SETTINGS = {
    'resolution': (1600, 900),
    'fps': 30,
    'food_count': 1,
    'state_delay': 1000,
    'tile_count': [40, 30],
    'name': 'MainPlayer',
    'control': 'WASD'
}

DEFAULT_SETTINGS_OTHER = {
    'resolution': (1600, 900),
    'fps': 30,
    'name': 'Player',
    'control': 'WASD'
}

SETTING_SIZE = (400, 500)
OTH_SETTING_SIZE = (400, 350)
CHOOSING_SIZE = (1280, 720)

class View:
    def __init__(self):
        self.model = None
        self.screen = None
        
    def get_settings(self):
        pg.init()
        
        screen = pg.display.set_mode(SETTING_SIZE)
        pg.display.set_caption('Settings')
        manager = pgui.UIManager(SETTING_SIZE)
        
        food_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 20), (150, 30)),
                                           text='Food count (0-100):', manager=manager)
        food_input = pgui.elements.UITextEntryLine(relative_rect=pg.Rect((250, 20), (100, 30)),
                                                   manager=manager)
        food_input.set_text(str(DEFAULT_SETTINGS['food_count']))
        
        delay_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 60), (160, 40)),
                                            text='State delay (100-3000):', manager=manager)
        delay_input = pgui.elements.UITextEntryLine(relative_rect=pg.Rect((250, 60), (100, 30)),
                                                    manager=manager)
        delay_input.set_text(str(DEFAULT_SETTINGS['state_delay']))

        resolution_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 120), (150, 30)),  
                                                    text='Resolution:', manager=manager)
        resolution_dropdown = pgui.elements.UIDropDownMenu(
            options_list=[f'{res[0]}x{res[1]}' for res in RESOLUTIONS],
            starting_option=f'{DEFAULT_SETTINGS["resolution"][0]}x{DEFAULT_SETTINGS["resolution"][1]}',
            relative_rect=pg.Rect((250, 120), (100, 30)),
            manager=manager
        )

        fps_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 160), (150, 30)),
                                            text='FPS:', manager=manager)
        fps_dropdown = pgui.elements.UIDropDownMenu(
            options_list=['30', '60'],
            starting_option=str(DEFAULT_SETTINGS['fps']),
            relative_rect=pg.Rect((250, 160), (100, 30)),
            manager=manager
        )

        width_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 220), (150, 30)),
                                            text='Width (10-100):', manager=manager)
        width_input = pgui.elements.UITextEntryLine(relative_rect=pg.Rect((250, 220), (100, 30)),
                                                    manager=manager)
        width_input.set_text(str(DEFAULT_SETTINGS['tile_count'][0]))

        height_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 260), (150, 30)),
                                            text='Height (10-100):', manager=manager)
        height_input = pgui.elements.UITextEntryLine(relative_rect=pg.Rect((250, 260), (100, 30)),
                                                    manager=manager)
        height_input.set_text(str(DEFAULT_SETTINGS['tile_count'][1]))

        name_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 300), (150, 30)),
                                            text='Name:', manager=manager)
        name_input = pgui.elements.UITextEntryLine(relative_rect=pg.Rect((250, 300), (100, 30)),
                                                    manager=manager)
        name_input.set_text(DEFAULT_SETTINGS['name'])

        control_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 340), (150, 30)),  
                                                    text='Control:', manager=manager)
        control_dropdown = pgui.elements.UIDropDownMenu(
            options_list=['WASD', 'Arrows'],
            starting_option=DEFAULT_SETTINGS['control'],
            relative_rect=pg.Rect((250, 340), (100, 30)),
            manager=manager
        )

        start_button = pgui.elements.UIButton(relative_rect=pg.Rect((150, 410), (100, 50)),
                                              text='Start', manager=manager)
        
        clock = pg.time.Clock()
        settings = None
        running = True

        while running:
            time_delta = clock.tick(30)/1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False

                if event.type == pgui.UI_BUTTON_PRESSED:
                    if event.ui_element == start_button:
                        try:
                            food_static = int(food_input.get_text())

                            if not (0 <= food_static <= 100):
                                raise ValueError('Food count must be between 0 and 100')
                        
                        except ValueError:
                            print('Invalid food count')
                            continue
                            
                        try:
                            state_delay = int(delay_input.get_text())

                            if not (100 <= state_delay <= 3000):
                                raise ValueError('State delay must be between 100 and 3000')
                        
                        except ValueError:
                            print('Invalid state delay')
                            continue

                        resolution_str = resolution_dropdown.selected_option[0]
                        resolution = tuple(map(int, resolution_str.split('x')))

                        fps = int(fps_dropdown.selected_option[0])

                        try:
                            width = int(width_input.get_text())

                            if not (10 <= width <= 100):
                                raise ValueError('Width must be between 10 and 100')
                        
                        except ValueError:
                            print('Invalid width')
                            continue

                        try:
                            height = int(height_input.get_text())

                            if not (10 <= height <= 100):
                                raise ValueError('Height must be between 10 and 100')

                        except ValueError:
                            print('Invalid height')
                            continue

                        name = name_input.get_text()
                        control = control_dropdown.selected_option[0]

                        settings = {
                            'resolution': resolution,
                            'fps': fps,
                            'food_count': food_static,
                            'state_delay': state_delay,
                            'tile_count': [width, height],
                            'name': name,
                            'control': control
                        }

                        running = False

                manager.process_events(event)

            manager.update(time_delta)
            screen.fill(BLACK)
            manager.draw_ui(screen)

            pg.display.update()
        
        pg.quit()

        return settings if settings else DEFAULT_SETTINGS
    
    def get_other_settings_part1(self):
        pg.init()
        
        screen = pg.display.set_mode(OTH_SETTING_SIZE)
        pg.display.set_caption('Settings')
        manager = pgui.UIManager(OTH_SETTING_SIZE)

        resolution_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 50), (130, 30)),  
                                                    text='Resolution:', manager=manager)
        resolution_dropdown = pgui.elements.UIDropDownMenu(
            options_list=[f'{res[0]}x{res[1]}' for res in RESOLUTIONS],
            starting_option=f'{DEFAULT_SETTINGS["resolution"][0]}x{DEFAULT_SETTINGS["resolution"][1]}',
            relative_rect=pg.Rect((200, 50), (150, 30)),
            manager=manager
        )

        fps_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 90), (130, 30)),
                                            text='FPS:', manager=manager)
        fps_dropdown = pgui.elements.UIDropDownMenu(
            options_list=['30', '60'],
            starting_option=str(DEFAULT_SETTINGS['fps']),
            relative_rect=pg.Rect((200, 90), (150, 30)),
            manager=manager
        )

        name_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 130), (130, 30)),
                                            text='Name:', manager=manager)
        name_input = pgui.elements.UITextEntryLine(relative_rect=pg.Rect((200, 130), (150, 30)),
                                                    manager=manager)
        name_input.set_text(get_random_name(separator='-', style='lowercase'))

        control_label = pgui.elements.UILabel(relative_rect=pg.Rect((50, 180), (130, 30)),  
                                                    text='Control:', manager=manager)
        control_dropdown = pgui.elements.UIDropDownMenu(
            options_list=['WASD', 'Arrows'],
            starting_option=DEFAULT_SETTINGS['control'],
            relative_rect=pg.Rect((200, 180), (150, 30)),
            manager=manager
        )

        start_button = pgui.elements.UIButton(relative_rect=pg.Rect((150, 250), (100, 50)),
                                              text='Start', manager=manager)
        
        clock = pg.time.Clock()
        settings = None
        running = True

        while running:
            time_delta = clock.tick(30)/1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False

                if event.type == pgui.UI_BUTTON_PRESSED:
                    if event.ui_element == start_button:
                        resolution_str = resolution_dropdown.selected_option[0]
                        resolution = tuple(map(int, resolution_str.split('x')))

                        fps = int(fps_dropdown.selected_option[0])
                        name = name_input.get_text()
                        control = control_dropdown.selected_option[0]

                        settings = {
                            'resolution': resolution,
                            'fps': fps,
                            'name': name,
                            'control': control
                        }

                        running = False

                manager.process_events(event)

            manager.update(time_delta)
            screen.fill(BLACK)
            manager.draw_ui(screen)

            pg.display.update()
        
        pg.quit()

        return settings if settings else DEFAULT_SETTINGS_OTHER
    
    def find_host(self, players):
        for player in players:
            r = player.role

            if r == NodeRole.MASTER or r == NodeRole.DEPUTY:
                return player.name
        
        return 'UNKNOWN'
    
    def toStr(self, game):
        base = game[0].announcement.games[0]
        gameName = base.game_name

        name = self.find_host(base.players.players)

        place = str(base.config.width)+'x'+str(base.config.height)
        food = str(base.config.food_static)
        delay = str(base.config.state_delay_ms)
        addr = game[1][0]+':'+str(game[1][1])

        return f'{gameName}({addr}): host -- {name}, place: {place}, static food: {food}, state delay -- {delay}'
    
    def getConfig(self, game):
        base = game.announcement.games[0]
        
        config = {
            'state_delay': base.config.state_delay_ms,
            'food_count': base.config.food_static,
            'tile_count': [base.config.width, base.config.height],
            'game_name': base.game_name
        }

        return config
    
    def get_other_settings_part2(self, resolution, binder):
        pg.init()

        screen = pg.display.set_mode(CHOOSING_SIZE)
        pg.display.set_caption('Choose host')
        manager = pgui.UIManager(CHOOSING_SIZE)

        games = binder.get_uniq_mulMessages()
        strGames = {}

        for game in games:
            strGames.update({self.toStr(game) : game})

        select = pgui.elements.UISelectionList(
            relative_rect=pg.Rect((0, 0), CHOOSING_SIZE),
            item_list=list(strGames.keys()),
            manager=manager
        )

        clock = pg.time.Clock()
        running = True

        last_time = pg.time.get_ticks()
        choise = None

        while running:
            current_time = pg.time.get_ticks()

            if current_time - last_time > 5000:
                last_time = current_time
                games = binder.get_uniq_mulMessages()
                strGames = {}

                for game in games:
                    strGames.update({self.toStr(game) : game})

                select.set_item_list(list(strGames.keys()))

            time_delta = clock.tick(30)/1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False

                if event.type == pgui.UI_SELECTION_LIST_NEW_SELECTION:
                    choise = select.get_single_selection()
                    running = False

                manager.process_events(event)
            
            manager.update(time_delta)
            screen.fill(BLACK)
            manager.draw_ui(screen)
            pg.display.update()

        pg.quit()

        if choise is None:
            raise ValueError("required settings were not found")

        temp = strGames[choise]
        config = self.getConfig(temp[0])

        return config, temp[1]
    
    def get_role(self):
        pg.init()

        screen = pg.display.set_mode((300, 200))
        pg.display.set_caption('Choose role')
        manager = pgui.UIManager((300, 200))

        role_label = pgui.elements.UILabel(relative_rect=pg.Rect((20, 35), (150, 30)),  
                                            text='Role:', manager=manager)
        role_dropdown = pgui.elements.UIDropDownMenu(
            options_list=['NORMAL', 'VIEWER'],
            starting_option='NORMAL',
            relative_rect=pg.Rect((150, 35), (100, 30)),
            manager=manager
        )

        start_button = pgui.elements.UIButton(relative_rect=pg.Rect((100, 100), (100, 50)),
                                              text='Start', manager=manager)
        
        clock = pg.time.Clock()
        role = None
        running = True

        while running:
            time_delta = clock.tick(30)/1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False

                if event.type == pgui.UI_BUTTON_PRESSED:
                    if event.ui_element == start_button:
                        role = role_dropdown.selected_option[0]
                        running = False

                manager.process_events(event)

            manager.update(time_delta)
            screen.fill(BLACK)
            manager.draw_ui(screen)

            pg.display.update()
        
        pg.quit()

        if role is None:
            role = 'NORMAL'

        return role

    def get_other_settings(self, binder):
        settings1 = self.get_other_settings_part1()
        res = settings1['resolution']

        settings2, addr = self.get_other_settings_part2(res, binder)

        settings1.update(settings2)
        role = self.get_role()
        settings1['role'] = role

        return settings1, addr
    
    def draw_stats(self): 
        shift = self.model.get_shift()
        window = self.model.get_window()
        game_place = self.model.get_game_place()

        count = self.model.get_snakes_size()
        tile_count = self.model.get_tile_count()
        host = self.model.get_host()
        font_size = window[0]//30
        snakes = self.model.get_snakes()
        all_food = self.model.get_all_food()
        font = pg.font.SysFont(None, font_size) 

        self.screen.fill(BLACK, (game_place[0], 0, 
                                 window[0]-game_place[0], window[1]))
        
        self.screen.blit(font.render('Game info:', True, WHITE),
                            (game_place[0]+20, shift[1]+20))
        
        self.screen.blit(font.render(f'Game size: {tile_count[0]}x{tile_count[1]}', True, WHITE),
                            (game_place[0]+20, shift[1]+50))
        
        self.screen.blit(font.render(f'Host: {host}', True, WHITE),
                            (game_place[0]+20, shift[1]+80))

        self.screen.blit(font.render('Players stats:', True, WHITE),
                            (game_place[0]+20, shift[1]+140))

        counter = 1

        for snake in snakes:
            name, score = self.model.get_name_score(snake)
            score_text = font.render(f'{name}: {score}', True, WHITE)
            self.screen.blit(score_text, (game_place[0]+20, shift[1]+140+30*counter))
            counter += 1
        
        counter += 1
        static_food = self.model.get_food_static()

        self.screen.blit(font.render(f'Count of snakes: {count}', True, WHITE),
                            (game_place[0]+20, shift[1]+140+30*counter))
        self.screen.blit(font.render(f'Max count of food: {all_food}', True, WHITE),
                            (game_place[0]+20, shift[1]+140+30*(counter+1)))
        self.screen.blit(font.render(f'Static food count: {static_food}', True, WHITE),
                            (game_place[0]+20, shift[1]+140+30*(counter+2)))
        
        self.screen.blit(font.render('Esc - exit', True, WHITE),
                            (game_place[0]+20, shift[1]+140+30*(counter+4)))

    def draw_window(self, foods):
        shift = self.model.get_shift()
        tile_place = self.model.get_tile_place()

        snakes = self.model.get_snakes()

        self.screen.fill(GREEN, 
                             (shift[0], shift[1], tile_place[0], tile_place[1]))
            
        for snake in snakes:
            snake.draw(self.screen)

        for food in foods:
            food.draw(self.screen)

        self.draw_stats()
