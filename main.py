#!/usr/bin/env python3
# coding: utf-8
import os
import sys
import json
import math
import urllib
import ffmpeg
from datetime import datetime

from PIL import Image
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.httpclient import HTTPClient
from tornado.websocket import WebSocketHandler
from tornado.options import define, options, parse_command_line
from tornado.web import Application, RequestHandler

define('port', default=8888, help='port to listen on', type=int)

STATIC_PATH = os.path.join(os.path.dirname(__file__), 'static')
EXCLUDES = []
DJS_PATH = os.path.join(STATIC_PATH, 'djs')
DJS = os.listdir(DJS_PATH)
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates')
PHOTOS_DIR = 'cur_photos'
PHOTOS_PATH = os.path.join(STATIC_PATH, PHOTOS_DIR)
PHOTOS = os.listdir(PHOTOS_PATH)
PHOTOS_COUNT = len(PHOTOS)
VIDEOS_PATH = os.path.join(STATIC_PATH, 'videos')
VIDEOS = os.listdir(VIDEOS_PATH)

TODAY_DJ = {
    (datetime(2021, 2, 25, 21), datetime(2021, 2, 26, 2)): 'тарханов.jpg',
    (datetime(2021, 2, 26, 14, 0), datetime(2021, 2, 26, 14, 45)): 'тарханов.jpg',
    (datetime(2021, 2, 26, 15, 0), datetime(2021, 2, 26, 19)): 'лукманов.jpg',
    (datetime(2021, 2, 26, 22, 0), datetime(2021, 2, 26, 3)): 'шевченко.jpg',
    (datetime(2021, 2, 27, 13, 0), datetime(2021, 2, 27, 13, 45)): 'фолклор.jpg',
    (datetime(2021, 2, 27, 14, 0), datetime(2021, 2, 27, 15)): 'ростилова.jpg',
    (datetime(2021, 2, 27, 15, 0), datetime(2021, 2, 27, 19)): 'телешева.jpg',
    (datetime(2021, 2, 27, 22, 0), datetime(2021, 2, 28, 3)): 'шпаковский.jpg',
    (datetime(2021, 2, 28, 3, 15), datetime(2021, 2, 28, 4)): 'шевченко.jpg',
    (datetime(2021, 2, 28, 4), datetime(2021, 2, 28, 5)): 'тарханов.jpg',
    (datetime(2021, 2, 28, 5, 15), datetime(2021, 2, 28, 6)): 'лукманов.jpg',
    (datetime(2021, 2, 28, 14), datetime(2021, 2, 28, 18)): 'тессье_эшпул.jpg',
    (datetime(2021, 2, 28, 20, 30), datetime(2021, 3, 1, 1, 30)): ['манькова.jpg', 'морозов.jpg'],
}

def get_vid_data(vid):
    data = ffmpeg.probe(os.path.join(VIDEOS_PATH, vid))
    formats = data['format']['format_name']
    return {
        'path': vid,
        'duration': math.ceil(float(data['format']['duration'])),
        'type': 'video/' + 'mp4' if 'mp4' in formats else 'webm'
    }
VIDEOS_DATA = [get_vid_data(vid) for vid in VIDEOS]
VIDEOS_COUNT = len(VIDEOS)
DJS_COUNT = len(DJS)
CUR_DJS_COUNT = 0
LOG_PATH = os.path.join(os.path.dirname(__file__), 'state.json')
PHOTO_TIMEOUT = 0.5 * 60
DJ_TIMEOUT = 0.6 * 60
CUR_DJ_TIMEOUT = 0.7 * 60
START_COUNTER = 1

SOCKETS = {'screen': None}


class MainHandler(RequestHandler):
    def get(self):
        self.render('index.html')


class ImgHandler(RequestHandler):
    def get(self):
        with open(LOG_PATH, 'r') as fh:
            try:
                state = json.load(fh)
            except json.JSONDecodeError:
                state = {
                    'photo': PHOTOS[0],
                    'video': VIDEOS[0],
                    'dj': DJS[0],
                    'cur_dj': TODAY_DJ[0],
                    'counter': START_COUNTER,
                }

        response = {
            'pause': 0,
            'src': None,
            'type': 'photo',
            'height': 0,
            'width': 0
        }

        if state['counter'] in [5, 15]:
            #
            # dj
            #
            for idx in range(DJS_COUNT):
                try:
                    dj_index = DJS.index(state['dj'])
                except ValueError:
                    dj = DJS[idx]
                else:
                    dj = DJS[(dj_index+1+idx) % DJS_COUNT]
                if dj not in EXCLUDES:
                    break
            #
            state['counter'] += 1
            state['dj'] = dj
            response['pause'] = DJ_TIMEOUT
            response['src'] = f'djs/{dj}'
            response['type'] = 'photo'
        elif state['counter'] in [1, 10]:
            #
            # current dj
            #
            now = datetime.now()
            cur_djs = [d for d in TODAY_DJ.keys() if d[0] < datetime.now() < d[1]]
            if len(cur_djs) == 0:
                for idx in range(DJS_COUNT):
                    try:
                        dj_index = DJS.index(state['dj'])
                    except ValueError:
                        dj = DJS[idx]
                    else:
                        dj = DJS[(dj_index+1+idx) % DJS_COUNT]
                    if dj not in EXCLUDES:
                        break
                #
                state['counter'] += 1
                state['dj'] = dj
                response['pause'] = DJ_TIMEOUT
                response['src'] = f'djs/{dj}'
                response['type'] = 'photo'
            else:
                cur_dj = TODAY_DJ.get(cur_djs[0])
                if isinstance(cur_dj, list):
                    global CUR_DJS_COUNT
                    CUR_DJS_COUNT = (CUR_DJS_COUNT + 1) % len(cur_dj)
                    cur_dj = cur_dj[CUR_DJS_COUNT]

                state['counter'] += 1
                state['cur_dj'] = cur_dj
                response['pause'] = CUR_DJ_TIMEOUT
                response['src'] = f'djs/{cur_dj}'
                response['type'] = 'photo'
        elif state['counter'] == 20:
            #
            # Video
            #
            for idx in range(VIDEOS_COUNT):
                try:
                    video_index = VIDEOS.index(state['video'])
                except ValueError:
                    cur_video = VIDEOS_DATA[idx]
                else:
                    cur_video = VIDEOS_DATA[(video_index+1+idx) % VIDEOS_COUNT]
                if cur_video not in EXCLUDES:
                    break
            state['counter'] = START_COUNTER
            state['video'] = cur_video['path']
            response['pause'] = cur_video['duration']
            response['src'] = f'static/videos/{cur_video["path"]}'
            response['type'] = cur_video['type']
        else:
            #
            # just photo
            #
            for idx in range(PHOTOS_COUNT):
                try:
                    photo_index = PHOTOS.index(state['photo'])
                except ValueError:
                    photo = PHOTOS[idx]
                else:
                    photo = PHOTOS[(photo_index+1+idx) % PHOTOS_COUNT]
                if photo not in EXCLUDES:
                    break
            state['counter'] += 1
            state['photo'] = photo
            response['pause'] = PHOTO_TIMEOUT
            response['src'] = f'{PHOTOS_DIR}/{photo}'
            response['type'] = 'photo'

        if response['type'] == 'photo':
            with Image.open(os.path.join(STATIC_PATH, response['src'])) as img:
                response['width'], response['height'] = img.size
        self.write(response)
        with open(LOG_PATH, 'w') as fh:
            json.dump(state, fh)


class WSChatHandler(WebSocketHandler):
    def open(self):
        print('Socket opened')

    def on_message(self, message):
        data = json.loads(message)
        if data['type'] == 'init':
            SOCKETS[data['init']] = self
        elif data['type'] == 'conn':
            print(data)
        if SOCKETS['screen'] is not None:
            SOCKETS['screen'].write_message(message)

    def on_close(self):
        print('Websocket closed')


class DJConsoleHandler(RequestHandler):
    def get(self):
        self.render('dj.html')


def main():
    """Construct and serve the tornado application."""
    parse_command_line()

    APP = Application(
        handlers=[
            (r'/', MainHandler),
            (r'/get', ImgHandler),
            (r'/chat', WSChatHandler),
            (r'/dj', DJConsoleHandler)
        ],
        template_path=TEMPLATE_PATH,
        static_path = STATIC_PATH
    )
    http_server = HTTPServer(APP)
    http_server.listen(options.port, address='0.0.0.0')
    print('Listening on http://localhost:%i' % options.port)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
