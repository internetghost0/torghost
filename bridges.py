#!/bin/env python3

## Script for easy copypasting raw bridges from https://bridges.torproject.org/bridges/?transport=obfs4
## and make it proper conf for torghost or torrc
##
## Usage:
## create file `bridges.txt` and put bridges from torghost.org there
## after that script will output proper config
## put that config in ./torghost.py (TOR_BRIDGES variable)


def get_bridges_from_file(filename='./bridges.txt'):
    bridges = []

    # read bridges from file
    with open(filename, 'r') as f:
        bridges = f.readlines()

    # remove all leading and trailing whitespace
    bridges = map(lambda line: line.strip(), bridges)

    #filter all lines that does not start with 'obfs4'
    bridges = filter(lambda line: line.startswith('obfs4'), bridges)

    # throw an error if variable has no bridges
    bridges = list(bridges)
    if len(bridges) == 0:
        raise Exception(f"Error: `{filename}` contains 0 bridges that starts with `obfs4`")

    # add 'Bridge' word to all bridges
    bridges = map(lambda line: f'Bridge {line}', bridges)

    # list -> string
    bridges = '\n'.join(bridges)

    # building proper config for torrc
    bridges = f'''# get bridges from => https://bridges.torproject.org/bridges/?transport=obfs4

# obfs4proxy is a tool that attempts to circumvent censorship by transforming the Tor traffic between the client and the bridge.
# install it and edit exec path if needed

ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy
UseBridges 1

{bridges}
'''
    # write the result to a file
    # with open('bridges_clean.txt', 'w') as f:
    #     f.write(bridges)

    # print the result
    print(bridges)

if __name__ == '__main__':
    try:
        get_bridges_from_file()
    except Exception as err:
        print('Script for easy copypasting raw bridges from https://bridges.torproject.org/bridges/?transport=obfs4')
        print('and make it proper conf for torghost or torrc')
        print()
        print('please create a `bridges.txt` file and put bridges from torproject there')
        print('-------------------------------------------------------------------------')
        print(err)
