#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import getopt
from requests import get
import subprocess
import time
import signal
from stem import Signal
from stem.control import Controller
from packaging import version


## CONF

USE_TOR_BRIDGES = True
DNS_SERVER = '8.8.8.8'
CHECK_TOR_IP_URL = "https://check.torproject.org/"

## END CONF


TOR_BRIDGES = ""
if USE_TOR_BRIDGES:
    TOR_BRIDGES = \
"""
ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy
UseBridges 1

Bridge obfs4 202.61.193.92:47247 EB229EE634C843DE16D295CE5281F7B8E0767E07 cert=y5/y9//2GGu8CS9P/9t84AXLmxLCIXQLExGshK2w1asEf1G/NSaEN49KT7GY2nsvCkl1Yw iat-mode=0
Bridge obfs4 120.51.68.71:443 1B2E6BDA9DA29A9EB2D04E07BD4DA0BA16D8467A cert=j060gm7IebArIA5ExPw7pOfphXUW8Tuyg3pyATH/Xs2ZGMUb0wv5HAO0xjLVuONnObtObQ iat-mode=0
Bridge obfs4 135.181.105.141:443 A7878416619C89A4BDC53CC180790576D61FA523 cert=OzNDqJ1iQRnpP3j91wWZtEwjYN3F6wCvKyC/7ltbQJSmByqzQVXgvfdoP6LODL9I0/hPJw iat-mode=0
"""


class bcolors:

    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[31m'
    YELLOW = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    BGRED = '\033[41m'
    WHITE = '\033[37m'


def t():
    current_time = time.localtime()
    ctime = time.strftime('%H:%M:%S', current_time)
    return '[' + ctime + ']'


def sigint_handler(signum, frame):
    print("User interrupt ! shutting down")
    stop_torghost()


def logo():
    print(bcolors.RED + bcolors.BOLD)
    print("""
      _____           ____ _               _
     |_   _|__  _ __ / ___| |__   ___  ___| |_
       | |/ _ \| '__| |  _| '_ \ / _ \/ __| __|
       | | (_) | |  | |_| | | | | (_) \__ \ |_
       |_|\___/|_|   \____|_| |_|\___/|___/\__|
	{V} - github.com/SusmithKrishnan/torghost
	    - github.com/internetghost0/torghost

    """.format(V=VERSION))
    print(bcolors.ENDC)


def usage():
    logo()
    print("""
    Torghost usage:
    -s    --start       Start Torghost
    -r    --switch      Request new tor exit node
    -x    --stop        Stop Torghost
    -h    --help        print(this help and exit)

    """)
    sys.exit()


def ip():
    while True:
        try:
            checkTorPage = get(CHECK_TOR_IP_URL).text
            if 'Congratulations. This browser is configured to use Tor.' in checkTorPage:
                # parse IP from tor website
                pattern = 'Your IP address appears to be:  <strong>'
                checkTorPage = checkTorPage[(checkTorPage.find(pattern) + len(pattern)):]
                pattern = '</strong></p>'
                ipTxt = checkTorPage[:checkTorPage.find(pattern)]
                return f'You have tor IP ({ipTxt})'
            else:
                return 'You have regular IP'
        except:
            continue


def check_root():
    if os.geteuid() != 0:
        print("You must be root; Say the magic word 'sudo' or 'doas'")
        sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)

TorrcCfgString = \
f"""
VirtualAddrNetwork 10.0.0.0/10
AutomapHostsOnResolve 1
TransPort 9040
DNSPort 5353
ControlPort 9051
RunAsDaemon 1

{TOR_BRIDGES}
"""

resolvString = f'nameserver {DNS_SERVER}'

Torrc = '/etc/tor/torghostrc'
resolv = '/etc/resolv.conf'

def start_torghost():
    os.system('sudo cp /etc/resolv.conf /etc/resolv.conf.bak')
    if os.path.exists(Torrc) and TorrcCfgString in open(Torrc).read():
        print(t() + ' Torrc file already configured')
    else:

        with open(Torrc, 'w') as myfile:
            print(t() + ' Writing torcc file ')
            myfile.write(TorrcCfgString)
            print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    if resolvString in open(resolv).read():
        print(t() + ' DNS resolv.conf file already configured')
    else:
        with open(resolv, 'w') as myfile:
            print(t() + ' Configuring DNS resolv.conf file.. '),
            myfile.write(resolvString)
            print(bcolors.GREEN + '[done]' + bcolors.ENDC)

    print(t() + ' Stopping tor service '),
    os.system('sudo systemctl stop tor')
    os.system('sudo fuser -k 9051/tcp > /dev/null 2>&1')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Starting new tor daemon '),
    os.system('sudo -u debian-tor tor -f /etc/tor/torghostrc > /dev/null'
              )
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' setting up iptables rules'),

    iptables_rules = \
        """
	NON_TOR="192.168.1.0/24 192.168.0.0/24"
	TOR_UID=%s
	TRANS_PORT="9040"

	iptables -F
	iptables -t nat -F

	iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
	iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353
	for NET in $NON_TOR 127.0.0.0/9 127.128.0.0/10; do
	 iptables -t nat -A OUTPUT -d $NET -j RETURN
	done
	iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT

	iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
	for NET in $NON_TOR 127.0.0.0/8; do
	 iptables -A OUTPUT -d $NET -j ACCEPT
	done
	iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
	iptables -A OUTPUT -j REJECT
	""" \
        % subprocess.getoutput('id -ur debian-tor')

    os.system(iptables_rules)
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Fetching current IP...')
    print(t() + ' CURRENT IP : ' + bcolors.GREEN + ip() + bcolors.ENDC)


def stop_torghost():
    print(bcolors.RED + t() + 'STOPPING torghost' + bcolors.ENDC)
    print(t() + ' Flushing iptables, resetting to default'),
    os.system('mv /etc/resolv.conf.bak /etc/resolv.conf')
    IpFlush = \
        """
	iptables -P INPUT ACCEPT
	iptables -P FORWARD ACCEPT
	iptables -P OUTPUT ACCEPT
	iptables -t nat -F
	iptables -t mangle -F
	iptables -F
	iptables -X
	"""
    os.system(IpFlush)
    os.system('sudo fuser -k 9051/tcp > /dev/null 2>&1')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Restarting Network manager'),
    # before
    # os.system('service network-manager restart')
    os.system('systemctl restart NetworkManager')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    #print(t() + ' Fetching current IP...')
    #print(t() + ' CURRENT IP : ' + bcolors.GREEN + ip() + bcolors.ENDC)


def switch_tor():
    print(t() + ' Requesting new circuit...'),
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Fetching current IP...')
    print(t() + ' CURRENT IP : ' + bcolors.GREEN + ip() + bcolors.ENDC)



def main():
    check_root()
    if len(sys.argv) <= 1:
        usage()
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'srxh', [
            'start', 'stop', 'switch', 'help'])
    except (getopt.GetoptError):
        usage()
        sys.exit(2)
    for (o, a) in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-s', '--start'):
            start_torghost()
        elif o in ('-x', '--stop'):
            stop_torghost()
        elif o in ('-r', '--switch'):
            switch_tor()
        else:
            usage()


if __name__ == '__main__':
    main()
