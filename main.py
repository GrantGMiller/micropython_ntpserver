import network as net
import time
import ntptime

net.WLAN(net.AP_IF).active(False)

net.WLAN(net.STA_IF).active(True)
net.WLAN(net.STA_IF).connect('TLS_Testing', 'extronextron')

while net.WLAN(net.STA_IF).ifconfig()[0] == '0.0.0.0':
    print('Waiting to Connect')
    time.sleep(1)

'''Set the system RTC to the current time (using the built in micropython NTP client)'''
import ntptime
count = 0
success = False


while True:
    count += 1
    try:
        tup = ntptime.settime()
        success = True
    except Exception as e22:
        print(count, 'ntptime.settime() Exception:', e22)

    if success or count > 10:
        break
    time.sleep(1)

'''If you want to set the NTP Server to a certain time, use below'''
# from machine import RTC
#
# YEAR = 2019
# MONTH = 10
# DAY_OF_MONTH = 26
# HOUR = 23  # 0
# MIN = 59
# SEC = 0
# DAY_OF_WEEK = 6  # 0 is Monday
# # DAY_OF_YEAR =  # 0-366
#
# rtc = RTC()
# rtc.datetime((YEAR, MONTH, DAY_OF_MONTH, DAY_OF_WEEK, HOUR, MIN, SEC, 0))

import ntpserver
