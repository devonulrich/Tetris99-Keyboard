import sys
import time
import asyncio

from pynput.keyboard import Key, KeyCode, Listener

from joycontrol.controller import Controller
from joycontrol.controller_state import ControllerState
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.memory import FlashMemory

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
        self.left = False
        self.right = False
        self.up = False
        self.down = False


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

        elif key == KeyCode.from_char('a'): # left
            self.left = True
        elif key == KeyCode.from_char('d'): # right
            self.right = True
        elif key == KeyCode.from_char('w'): # up
            self.up = True
        elif key == KeyCode.from_char('s'): # down
            self.down = True

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

        elif key == KeyCode.from_char('a'):
            self.left = False
        elif key == KeyCode.from_char('d'):
            self.right = False
        elif key == KeyCode.from_char('w'):
            self.up = False
        elif key == KeyCode.from_char('s'):
            self.down = False



# adapted from button_push() in controller_state.py
async def main_loop(controller_state, keyboard_state):
    button_state = controller_state.button_state

    for key in keyboard_state.keys:
        button_state.set_button(key, pushed=keyboard_state.keys[key])

    stick_state = controller_state.r_stick_state
    calib = stick_state.get_calibration()
    dx = keyboard_state.right - keyboard_state.left
    dy = keyboard_state.up - keyboard_state.down

    stick_state.set_h(calib.h_center + calib.h_max_above_center * dx)
    stick_state.set_v(calib.v_center + calib.v_max_above_center * dy)

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
        # currTime = time.time()
        # print(currTime - pastTime)
        # pastTime = currTime



if __name__ == '__main__':
    bt_addr = None
    # use a specific switch BT address if one is given
    if len(sys.argv) >= 2:
        bt_addr = sys.argv[1]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main(bt_addr))
