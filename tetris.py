import sys
import time
import asyncio

from pynput.keyboard import Key, KeyCode, Listener

from joycontrol import *
from joycontrol.controller import Controller
from joycontrol.controller_state import ControllerState, button_push
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.memory import FlashMemory

# keyboard order: up, down, left, right, space, c, enter
keys = {
    'a': False,
    'down': False,
    'left': False,
    'right': False,
    'up': False,
    'r': False,
    'l': False
}

direction = 0

def key_down(key):
    global direction
    if key == Key.up:
        keys['a'] = True
    elif key == Key.down:
        keys['down'] = True
    elif key == Key.left:
        keys['left'] = True
    elif key == Key.right:
        keys['right'] = True
    elif key == Key.space:
        keys['up'] = True
    elif key == KeyCode.from_char('c'):
        keys['r'] = True
    elif key == Key.enter:
        # press both R and L
        keys['r'] = True
        keys['l'] = True
    elif key == KeyCode.from_char('a'):
        direction = (direction + 1) % 5
    elif key == Key.esc:
        # quit
        return False

def key_up(key):
    if key == Key.up:
        keys['a'] = False
    elif key == Key.down:
        keys['down'] = False
    elif key == Key.left:
        keys['left'] = False
    elif key == Key.right:
        keys['right'] = False
    elif key == Key.space:
        keys['up'] = False
    elif key == KeyCode.from_char('c'):
        keys['r'] = False
    elif key == Key.enter:
        keys['r'] = False
        keys['l'] = False

# adapted from button_push() in controller_state.py
async def main_loop(controller_state):
    button_state = controller_state.button_state

    for key in keys:
        button_state.set_button(key, pushed=keys[key])

    stick_state = controller_state.r_stick_state
    if direction == 0:
        stick_state.set_center()
    elif direction == 1:
        stick_state.set_right()
    elif direction == 2:
        stick_state.set_down()
    elif direction == 3:
        stick_state.set_left()
    else:
        stick_state.set_up()

    await controller_state.send()
    # await asyncio.sleep(1/60)

async def _main(bt_addr):
    # connect via bluetooth
    # TODO: add some error handling for opening the spi file
    spi_flash = FlashMemory(open("spi", "rb").read())

    factory = controller_protocol_factory(Controller.PRO_CONTROLLER, spi_flash=spi_flash)
    transport, protocol = await create_hid_server(factory,
        reconnect_bt_addr=bt_addr, ctl_psm=17, itr_psm=19)

    controller_state = protocol.get_controller_state()
    await controller_state.connect()
    print("Connected.")

    # start key listener thread
    listener = None
    try:
        listener = Listener(on_press=key_down, on_release=key_up, suppress=True)
    except:
        raise
    finally:
        listener.start()

    # await button_push(controller_state, 'home', sec=5)
    pastTime = time.time()
    while listener.running:
        await main_loop(controller_state)
        # currTime = time.time()
        # print(currTime - pastTime)
        # pastTime = currTime

if __name__ == '__main__':
    bt_addr = None
    if len(sys.argv) >= 2:
        bt_addr = sys.argv[1]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main(bt_addr))
