import sys
import time
import asyncio

from pynput.keyboard import Key, KeyCode, Listener

from joycontrol.controller import Controller
from joycontrol.controller_state import ControllerState
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.memory import FlashMemory

class Direction:
    CENTER = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

class KeyboardState:
    def __init__(self):
        # key order: up, down, left, right, space, c, enter
        self.keys = {
			'a': False,
			'down': False,
			'left': False,
			'right': False,
			'up': False,
			'r': False,
			'l': False
		}
        self.direction = Direction.CENTER
        self.last_dir_change = 0


    def key_down(self, key):
        global direction
        if key == Key.up:
            self.keys['a'] = True
        elif key == Key.down:
            self.keys['down'] = True
        elif key == Key.left:
            self.keys['left'] = True
        elif key == Key.right:
            self.keys['right'] = True
        elif key == Key.space:
            self.keys['up'] = True
        elif key == KeyCode.from_char('c'):
            self.keys['r'] = True
        elif key == Key.enter:
            # press both R and L
            self.keys['r'] = True
            self.keys['l'] = True

        elif key == KeyCode.from_char('a'):
            self.direction = Direction.LEFT
            self.last_dir_change = time.time()
        elif key == KeyCode.from_char('d'):
            self.direction = Direction.RIGHT
            self.last_dir_change = time.time()
        elif key == KeyCode.from_char('w'):
            self.direction = Direction.UP
            self.last_dir_change = time.time()
        elif key == KeyCode.from_char('s'):
            self.direction = Direction.DOWN
            self.last_dir_change = time.time()

        elif key == Key.esc:
            # quit
            return False

    def key_up(self, key):
        if key == Key.up:
            self.keys['a'] = False
        elif key == Key.down:
            self.keys['down'] = False
        elif key == Key.left:
            self.keys['left'] = False
        elif key == Key.right:
            self.keys['right'] = False
        elif key == Key.space:
            self.keys['up'] = False
        elif key == KeyCode.from_char('c'):
            self.keys['r'] = False
        elif key == Key.enter:
            self.keys['r'] = False
            self.keys['l'] = False



# adapted from button_push() in controller_state.py
async def main_loop(controller_state, keyboard_state):
    button_state = controller_state.button_state

    for key in keyboard_state.keys:
        button_state.set_button(key, pushed=keyboard_state.keys[key])

    stick_state = controller_state.r_stick_state
    if keyboard_state.direction == Direction.LEFT:
        stick_state.set_left()
    elif keyboard_state.direction == Direction.RIGHT:
        stick_state.set_right()
    elif keyboard_state.direction == Direction.UP:
        stick_state.set_up()
    elif keyboard_state.direction == Direction.DOWN:
        stick_state.set_down()
    else:
        stick_state.set_center()

    # reset to center after moving in any direction
    if time.time() - keyboard_state.last_dir_change >= 0.25:
        keyboard_state.direction = Direction.CENTER

    await controller_state.send()
    # await asyncio.sleep(1/60)



async def _main(bt_addr):
    # set up controller's flash memory data
    f = open('spi', 'rb')
    spi_flash = FlashMemory(f.read())
    f.close()

    # connect via bluetooth
    factory = controller_protocol_factory(Controller.PRO_CONTROLLER, spi_flash=spi_flash)
    transport, protocol = await create_hid_server(factory,
        reconnect_bt_addr=bt_addr, ctl_psm=17, itr_psm=19)

    controller_state = protocol.get_controller_state()
    await controller_state.connect()
    print("Connected.")

    # start key listener thread
    keyboard_state = KeyboardState()
    listener = Listener(on_press=keyboard_state.key_down, on_release=keyboard_state.key_up,
        suppress=True)
    listener.start()

    # await button_push(controller_state, 'home', sec=5)
    pastTime = time.time()
    while listener.running:
        await main_loop(controller_state, keyboard_state)
        # For debugging: display how long it takes to send the controller state
        currTime = time.time()
        print(currTime - pastTime)
        pastTime = currTime



if __name__ == '__main__':
    bt_addr = None
    # use a specific switch BT address if one is given
    if len(sys.argv) >= 2:
        bt_addr = sys.argv[1]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main(bt_addr))
