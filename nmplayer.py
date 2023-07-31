import os          , sys    ,\
       subprocess  , select ,\
       time        , math   ,\
       json        ,         \
       mimetypes   , mpd
from os.path import *
from http.server import *

pathprefix="/var/www/mpd"

def scaleclamp(n, x1, y1, x2, y2):
    n  = float(n)
    x1 = float(x1)
    y1 = float(y1)
    x2 = float(x2)
    y2 = float(y2)
    n  = sorted((x1, n, y1))[1]
    n -= x1
    n /= (y1 - x1)
    n *= (y2 - x2)
    n += x2
    return int(n)

#class Artist():
#    def __init__(self, name):
#        self.name = name
#
#class Album():
#    def __init__(self, name, artistid):
#        self.name = name
#        self.artistid = artistid
#
#class Track():
#    def __init__(self, name, albumid, filepath):
#        self.name = name
#        self.albumid = albumid
#        self.filepath = filepath
#
#
#print("Scanning for tracks...")
#artists = []
#albums  = []
#tracks  = []
#for artist in os.listdir("tracks/"):
#    artistid = len(artists)
#    artists.append(Artist(artist))
#    #print(("Artist id % 3d:  " %artistid) + artist)
#    for album in os.listdir("tracks/%s/" % artist):
#        albumid = len(albums)
#        albums.append(Album(album, artistid))
#        #print(("Album id  % 3d:    "%albumid) +album)
#        for track in os.listdir("tracks/%s/%s/" % (artist, album)):
#            trackid = len(tracks)
#            tracks.append(Track(track, albumid, "tracks/%s/%s/%s" % (artist, album, track)))
#            #print(("Track id  % 3d:      "%trackid) +track)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("GET request from %s:%s to %s" % (self.client_address[0], self.client_address[1], self.path))

        filepath = pathprefix + "/www" + self.path

        if self.path[:4] == "/do/":
            action = list(filter(None, self.path.split("/")))
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            #self.wfile.write("Action: %s\n" % action[1])
            if action[1] == 'getartists':
                r = {}
                for k,v in enumerate(artists):
                    r[k] = v.name
                self.wfile.write(json.dumps(r))
            elif action[1] == 'getalbums':
                r = {}
                for k,v in enumerate(albums):
                    if v.artistid == int(action[2]):
                        r[k] = v.name
                self.wfile.write(json.dumps(r))
            elif action[1] == 'gettracks':
                r = {}
                for k,v in enumerate(tracks):
                    if v.albumid == int(action[2]):
                        r[k] = v.name
                self.wfile.write(json.dumps(r))
            elif action[1] == 'update':
                r = client.status()
                r['songdata'] = client.currentsong()
                r['nextsongdata'] = "fixme" #client.playlistid(r['nextsongid'])[0]
                r['volume'] = scaleclamp(r['volume'], 40, 100, 0, 20)
                self.wfile.write(json.dumps(r).encode())
            elif action[1] == 'prev':
                client.previous()
            elif action[1] == 'play' or action[1] == 'pause':
                client.pause()
            elif action[1] == 'next':
                client.next()
            elif action[1] == 'setvolume':
                action[2] = scaleclamp(r['volume'], 0, 20, 40, 100)
                if action[2] == 40:
                    action[2] = 0
                client.setvol(action[2])
            elif action[1] == 'volumeup':
                r = client.status()
                vol = scaleclamp(r['volume'], 40, 100, 0, 20)
                vol += 1
                vol = scaleclamp(vol, 0, 20, 40, 100)
                client.setvol(vol)
            elif action[1] == 'volumedown':
                r = client.status()
                vol = scaleclamp(r['volume'], 40, 100, 0, 20)
                vol -= 1
                vol = scaleclamp(vol, 0, 20, 40, 100)
                if vol == 40:
                    vol = 0
                client.setvol(vol)
            elif action[1] == 'getplaylist':
                self.wfile.write(json.dumps(client.playlistinfo()).encode('utf-8'))
            elif action[1] == 'getalltracks':
                self.wfile.write(json.dumps(client.listallinfo()).encode('utf-8'))
            elif action[1] == 'changetrack':
                client.playid(action[2])
            elif action[1] == 'seekpercent':
                song = client.currentsong()
                client.seek(song['pos'], int(float(action[2]) / 100 * float(song['time'])))
            return


        if os.path.isdir(filepath):
            filepath += "/index.html"

        if not os.path.exists(filepath):
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write("404 File Not Found: %s" % filepath)
        elif not os.path.abspath(filepath).startswith(pathprefix + "/www/"):
            self.send_response(403)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write("403 Forbidden: %s\nThis incident has been logged." % filepath)
            print("403 -- %s:%s tried to access %s, but the request was blocked since the target file was not located in the www folder." % (self.client_address[0], self.client_address[1], filepath))
        else:
            if os.path.abspath(filepath).endswith(".png") or os.path.abspath(filepath).endswith(".ico"):
                fh = open(filepath, "rb")
            else:
                fh = open(filepath, "r")
            self.send_response(200)
            self.send_header("Content-type", mimetypes.guess_type(filepath)[0])
            self.end_headers()
            if os.path.abspath(filepath).endswith(".png") or os.path.abspath(filepath).endswith(".ico"):
                self.wfile.write(fh.read())
            else:
                self.wfile.write(fh.read().encode())

server = HTTPServer(('', 8080), Handler)
server.timeout = 0  # Make handle_request() not blocking
print('Started httpserver on port 8080')

client = mpd.MPDClient()           # create client object
client.timeout = 10                # network timeout in seconds (floats allowed), default: None
client.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
client.connect("localhost", 6600)  # connect to localhost:6600

cursong = "-"
cursongrefreshtimer = 1
keepalivetimer = 500

running = True
while running:
    try:
        server.handle_request()
    except KeyboardInterrupt:
        print(" quitting...")
        running = False

    keepalivetimer -= 1
    if keepalivetimer < 0:
        keepalivetimer = 500
        client.status()

client.close()
client.disconnect()
