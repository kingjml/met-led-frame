"""
Weather Station LED Board
J.King 01/02/2021
"""
import board
import io
import time
import neopixel
import busio
import xmltok
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_ntp import NTP
import adafruit_fancyled.adafruit_fancyled as fancy

# Station names associated with each LED
# Note CXHM does not report snow so I use CTBF
STATION_LIST = ['CTZR', 'CXHA', 'CXRG','CWSN', 'CTBF', 'CTWL',
                'CWNC','CTKG', 'CTBO', 'CXKE', 'CTCK',
                'CWGD', 'CZEL', 'CTBF', 'CXTO','CTUX', 'CTPQ',
                'CWRK', 'CTPM', 'CXOA','CTNK','CTZN','CTSB',
                'COSM', 'CTZE','CTTR', 'CWLS', 'CXET', 'CTBT','CXPC']

# Colour constants
grad = [(0.0, 0xedf8b1),
        (0.5, 0x9ebcda),
        (1.0, 0x0000FF)]
levels = (0.25, 0.3, 0.15)
palette = fancy.expand_gradient(grad, 50)

BASE_URL = 'https://dd.weather.gc.ca/observations/swob-ml/'
VAR_STRING = 'avg_snw_dpth_pst5mts'
latest_var = [None]*len(STATION_LIST)

# Init pixels
pixels = neopixel.NeoPixel(board.D5, 30,
                           brightness=0.5,
                           auto_write=True,
                           pixel_order=neopixel.GRBW)
pixels.fill((255, 0, 0, 0))

# Check for WIFI creds
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Init WIFI
esp32_cs = DigitalInOut(board.D13)
esp32_ready = DigitalInOut(board.D11)
esp32_reset = DigitalInOut(board.D12)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
requests.set_socket(socket, esp)

print("Snow.Science Weather Board")
print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
print("IP address is", esp.pretty_ip(esp.ip_address))

# Get the time in UTC
ntp = NTP(esp)
while not ntp.valid_time:
    ntp.set_time()
    print("Failed to obtain time, retrying in 5 seconds...")
    time.sleep(5)
current_time = time.time()
now = time.localtime(current_time)
print(
    "It is currently {}/{}/{} at {}:{}:{} UTC".format(
        now.tm_mon, now.tm_mday, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec
    )
)

for idx, station in enumerate(STATION_LIST):
    station_url = '{:04}{:02}{:02}/{}/'.format(now.tm_year, now.tm_mon,
                                           now.tm_mday,station)
    file_url='{:04}-{:02}-{:02}-{:02}00-{}-AUTO-swob.xml'.format(now.tm_year,now.tm_mon,
                                                                now.tm_mday,now.tm_hour,station)
    file_url = BASE_URL+station_url+file_url

    print("Fetching obs from", file_url)
    r = requests.get(file_url)
    data_count = 0
    for elm in xmltok.tokenize(io.StringIO(r.text)):
        data_count -= 1
        if (elm[0] == 'ATTR') and (elm[2] == VAR_STRING):
            data_count = 2
        if data_count == 0:
            latest_var[idx] = float(elm[2])
    r.close()
print(latest_var)

for i, v in enumerate(latest_var):
    print(i)
    if v is not None:
        pix_val = (v - min(latest_var))/(max(latest_var)+1 - min(latest_var))
        pix_col = fancy.palette_lookup(palette, pix_val)
        pix_col = fancy.gamma_adjust(pix_col, brightness=levels)
        pixels[i] = pix_col.pack()
        print(v)
        
# TODO: Update every hour
print("Done!")