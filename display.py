#!/usr/bin/env python3
import epd2in9  # ws driver
import epdconfig
import time  # time functions
import locale
import requests
from io import BytesIO
from PIL import Image  # image functions
from PIL import ImageDraw  # image functions
from PIL import ImageFont  # image functions
import PIL.ImageOps
import svdr
import prometheus
from datetime import datetime, timedelta
import configparser

config = configparser.ConfigParser()
config.read("config.ini")
owmcityid = config['owm']['cityid']
owmappid = config['owm']['appid']
promhost = config['prometheus']['host']
promport = config['prometheus']['port']
promdssl = config['prometheus']['disablessl']
svdrhost = config['svdr']['host']
wfontfile = config['fonts']['wfont']
wfontsmallfile = config['fonts']['wfontsmall']
fontfile = config['fonts']['font']
fontmediumfile = config['fonts']['fontmedium']
fontvsmallfile = config['fonts']['fontvsmall']

# openweather api
def owr_update():
    """Get weatherupdate from openweathermap
 
    Returns:
    int: wcondition
    float: wtemp
    float:  wpressure
    int: whum
    float: wwindspeed
    int:  wclouds
    timestamp: wtime
    timestamp: wsunrise
    timestamp: wsunset
    timestamp: owrtime

    """
    owr = requests.get('http://api.openweathermap.org/data/2.5/weather?id=' 
                       + owmcityid + '&units=metric&APPID='
                       + owmappid)
    if owr.status_code == 200:
        owrj = owr.json()
        wcondition = owrj["weather"][0]["id"]
        wtemp = int(round(owrj["main"]["temp"]))
        wpressure = owrj["main"]["pressure"]
        whum = owrj["main"]["humidity"]
#        wvis = owrj["visibility"] # scheinbar nicht immer vorhanden
        wwindspeed = owrj["wind"]["speed"]
#        wwinddeg = owrj["wind"]["deg"] # scheinbar nicht immer vorhanden
        wclouds = owrj["clouds"]["all"]
        wtime = owrj["dt"]
        wsunrise = owrj["sys"]["sunrise"]
        wsunset = owrj["sys"]["sunset"]
        owrtime = time.time()
    return (wcondition, wtemp, wpressure, whum, wwindspeed, wclouds,
            wtime, wsunrise, wsunset, owrtime)


class owr_forecast:
    def __init__(self):
        # forecast api provides 3hour forecast 5 days so id 0 is next hour
        # and 1 nextfull+3 hours and 2 nextfull+6v and so on,
        # id 39 should be nexthour+117
        self.owr = requests.get('http://api.openweathermap.org/data/2.5/forecast?id='
                                + owmcityid + '&units=metric&APPID='
                                + owmappid)
        if self.owr.status_code == 200:
            self.owrj = self.owr.json()
            self.owrtime = time.time()
            self.count = self.owrj["cnt"]  # int

    def forecast(self, hour):
        self.wcondition = self.owrj["list"][hour]["weather"][0]["id"]  # int
        self.wtemp = self.owrj["list"][hour]["main"]["temp"]  # float
        self.wtempmax = self.owrj["list"][hour]["main"]["temp_max"]  # float
        self.wtempmin = self.owrj["list"][hour]["main"]["temp_min"]  # float
        self.wpressure = self.owrj["list"][hour]["main"]["pressure"]  # float
        self.whum = self.owrj["list"][hour]["main"]["humidity"]  # int
        self.wwindspeed = self.owrj["list"][hour]["wind"]["speed"]  # float
        self.wwinddeg = self.owrj["list"][hour]["wind"]["deg"]  # float
        self.wclouds = self.owrj["list"][hour]["clouds"]["all"]  # int
        self.wtime = self.owrj["list"][hour]["dt"]  # timestamp
#        self.wsnow = self.owrj["list"][hour]["snow"]["3h"]  # float

def clear_display():
    ws = epd2in9.EPD()
    ws.init(ws.lut_full_update)
    whole_image = Image.new('1', (ws.width, ws.height), 255)
    image_width, image_height = whole_image.size
    draw = ImageDraw.Draw(whole_image)
    draw.rectangle((0, 0, image_width, image_height), fill=255)
    ws.Clear(0xFF)


def display():
    owrid = {
            200: 'O',  # thunderstorm with light rain
            201: 'O',  # thunderstorm with rain
            202: 'O',  # thunderstorm with heavy rain
            210: 'O',  # light thunderstorm
            211: 'O',  # thunderstorm
            212: 'O',  # heavy thunderstorm
            221: 'O',  # ragged thunderstorm
            230: 'O',  # thunderstorm with light drizzle
            231: 'O',  # thunderstorm with drizzle
            232: 'O',  # thunderstorm with heavy drizzle
            300: 'X',  # light intensity drizzle
            301: 'X',  # drizzle
            302: 'X',  # heavy intensity drizzle
            310: 'X',  # light intensity drizzle rain
            311: 'X',  # drizzle rain
            312: 'X',  # heavy intensity drizzle rain
            313: 'X',  # shower rain and drizzle
            314: 'X',  # heavy shower rain and drizzle
            321: 'X',  # shower drizzle
            500: 'Q',  # light rain
            501: 'R',  # moderate rain
            502: 'R',  # heavy intensity rain
            503: 'R',  # very heavy rain
            504: 'R',  # extreme rain
            511: 'W',  # freezing rain
            520: 'X',  # light intensity shower rain
            521: 'X',  # shower rain
            522: 'X',  # heavy intensity shower rain
            531: 'X',  # ragged shower rain
            600: 'W',  # light snow
            601: 'W',  # snow
            602: 'W',  # heavy snow
            611: 'W',  # sleet
            612: 'W',  # shower sleet
            615: 'W',  # light rain and snow
            616: 'W',  # rain and snow
            620: 'W',  # light shower snow
            621: 'W',  # shower snow
            622: 'W',  # heavy shower snow
            701: 'M',  # mist
            711: 'M',  # smoke
            721: 'M',  # haze
            731: 'M',  # sand, dust whirls
            741: 'M',  # fog
            751: 'M',  # sand
            761: 'M',  # dust
            762: 'M',  # volcanic ash
            771: 'M',  # squalls
            781: 'M',  # tornado
            800: 'B',  # clear sky	 'B'
            801: 'H',  # few clouds	 'H'
            802: 'N',  # scattered clouds
            803: 'Y',  # broken clouds
            804: 'Y'  # overcast clouds
            #    900	tornado
            #    901	tropical storm
            #    902	hurricane
            #    903	cold
            #    904	hot
            #    905	windy
            #    906	hail
            #    951	calm
            #    952	light breeze
            #    953	gentle breeze
            #    954	moderate breeze
            #    955	fresh breeze
            #    956	strong breeze
            #    957	high wind, near gale
            #    958	gale
            #    959	severe gale
            #    960	storm
            #    961	violent storm
            #    962	hurricane
    }
    owridnight = {
            800: 'C',  # clear sky	 'B'
            801: 'I'  # few clouds	 'H'
    }
    LANG = locale.getdefaultlocale()
    locale.setlocale(locale.LC_TIME, LANG)
    clear_display()
    clear_display()
    wcondition, wtemp, wpressure, whum, wwindspeed, wclouds, wtime, wsunrise, wsunset, owrtime = owr_update()
    prom = prometheus.my_prometheus(promhost, promport, promdssl)
    prom.prom_query("")
    promtemp = float(prom.lasttemp)
    wfont = ImageFont.truetype(wfontfile, 48)
    wfontsmall = ImageFont.truetype(wfontsmallfile, 24)
    font = ImageFont.truetype(fontfile, 48)
    fontmedium = ImageFont.truetype(fontmediumfile, 40)
    fontvsmall = ImageFont.truetype(fontvsmallfile, 13)
    tchannel = 'unbekannt.bmp'
    tstartdate = ''
    tstarttime = ''
    ttext = ''
    wsc = epdconfig.RaspberryPi()
    ws = epd2in9.EPD()
    ws.init(ws.lut_partial_update)
    whole_image = Image.new('1', (ws.width, ws.height), 255)
    draw = ImageDraw.Draw(whole_image)
    image_width, image_height = whole_image.size
    forecast = owr_forecast()
    clearrunningtime = time.time()
    refreshrunningtime = time.time()
    while (True):
        # read new temperature after 15min
        if time.time()-refreshrunningtime > 900:
            wcondition, wtemp, wpressure, whum, wwindspeed, wclouds, wtime, wsunrise, wsunset, owrtime = owr_update()
            prom.prom_query("")
            promtemp = float(prom.lasttemp)
            refreshrunningtime = time.time()
        #clear screen after 1h
        if time.time()-clearrunningtime > 3600:
            clear_display()
            ws.init(ws.lut_partial_update)
            clearrunningtime = time.time()
        # whole image blank
        draw.rectangle((0, 0, image_width, image_height), fill=255)
        # draw 3 separating lines
        draw.line([(0, 74), (196, 74)], fill=0)
        draw.line([(0, 148), (196, 148)], fill=0)
        draw.line([(0, 222), (196, 222)], fill=0)
        # draw time
        draw.text((3, 7), time.strftime('%H:%M'), font=font, fill=0)
        # draw actual weather
        # separate night only for supporting conditions
        if (799 < wcondition < 802):
            if (time.strftime('%d') == time.strftime('%d',
                                                     time.localtime(wtime))):
                if (wsunrise < time.time() < wsunset):
                    draw.text((3, 79), owrid[wcondition], font=wfont, fill=0)
                else:
                    draw.text((3, 79),
                              owridnight[wcondition], font=wfont, fill=0)
            else:
                draw.text((3, 79), owridnight[wcondition], font=wfont, fill=0)
        else:
            draw.text((3, 79), owrid[wcondition], font=wfont, fill=0)
        if (round(promtemp) < 0):
            draw.text((58, 85), str(round(promtemp)), font=fontmedium, fill=0)
        else:
            draw.text((70, 85), str(round(promtemp)), font=fontmedium, fill=0)
        if (-10 < wtemp < 10):
            draw.text((90, 85), '*', font=wfontsmall, fill=0)
        else:
            draw.text((108, 85), '*', font=wfontsmall, fill=0)
        draw.text((14, 131),
                  time.strftime('%H:%M - %d.%m.%y', time.localtime(wtime)),
                  font=fontvsmall, fill=0)
        # check if forecast is older than 30min
        if time.time()-forecast.owrtime > 1800:
            forecast = owr_forecast()
        # draw forecast curve
        x = 3
        high = -100
        low = 100
        for i in range(0, forecast.count):
            forecast.forecast(i)
            if forecast.wtemp < low:
                low = int(round(forecast.wtemp))
            if forecast.wtemp > high:
                high = int(round(forecast.wtemp))
        scala = 60/(high-low)
        draw.text((3, 150), str(high), font=fontvsmall, fill=0)
        draw.text((3, 210), str(low), font=fontvsmall, fill=0)
        for i in range(0, forecast.count):
            if i < forecast.count-1:
                forecast.forecast(i)
                first = forecast.wtemp
                forecast.forecast(i+1)
                second = forecast.wtemp
                draw.line([(x, int(round(150+((high-first)*scala)))),
                           (x+3, int(round(150+((high-second)*scala))))],
                          fill=0)
            x = x+3
        # vdr next timer
        try:
            timer = svdr.svdr(svdrhost, 6419, 10)
            timer.send("lstt")
            timer.get_next_timer()
            tchannel = timer.nexttimer.channel
            tstartdate = timer.nexttimer.start.strftime('%a. %d.%m.')
            tstarttime = timer.nexttimer.start.strftime('%H:%M')
            ttext = timer.nexttimer.text
            timer.close_connection
        except:
            pass
        logo = Image.open(tchannel)
        logo = logo.convert('1')
        draw.text((60, 235), tstartdate, font=fontvsmall, fill=0)
        draw.text((72, 255), tstarttime, font=fontvsmall, fill=0)
        draw.text((3, 278), ttext, font=fontvsmall, fill=0)
        # push drawing into memory and show it
        ws.display(ws.getbuffer(whole_image))
        wsc.delay_ms(10000)


if __name__ == '__main__':
    display()

