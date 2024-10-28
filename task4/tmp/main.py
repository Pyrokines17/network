import pygame_gui as pgui
import pygame as pg

from game import *

class MainMenu:
    def __init__(self):
        pg.init()

        self.screen = pg.display.set_mode((400, 350))
        pg.display.set_caption("Main Menu")
        self.manager = pgui.UIManager((400, 350))

        self.start_button = pgui.elements.UIButton(
            relative_rect=pg.Rect((100, 50), (200, 50)),
            text="Start new game",
            manager=self.manager
        )

        self.join_button = pgui.elements.UIButton(
            relative_rect=pg.Rect((100, 150), (200, 50)),
            text="Join to game",
            manager=self.manager
        )

        self.exit_button = pgui.elements.UIButton(
            relative_rect=pg.Rect((100, 250), (200, 50)),
            text="Exit",
            manager=self.manager
        )

        self.selected_option = None
        self.running = True

    def run(self):
        clock = pg.time.Clock()

        while self.running:
            time_delta = clock.tick(30)/1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False

                if event.type == pgui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.start_button:
                        self.selected_option = "play"
                        self.running = False
                    elif event.ui_element == self.join_button:
                        self.selected_option = "join"
                        self.running = False
                    elif event.ui_element == self.exit_button:
                        self.selected_option = "exit"
                        self.running = False

                self.manager.process_events(event)

            self.manager.update(time_delta)

            self.screen.fill((0, 0, 0))
            self.manager.draw_ui(self.screen)

            pg.display.update()

        pg.quit()

        return self.selected_option

if __name__ == '__main__':
    while True:
        menu = MainMenu()
        selected_option = menu.run()

        if selected_option == "play":
            game = Game('MASTER')
            game.run()
        elif selected_option == "join":
            game = Game('JOINER')
            
            if not game.end:
                game.run()
        else:
            break
