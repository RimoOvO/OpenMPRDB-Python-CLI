# -*- coding: utf-8 -*-
import argparse
import configparser
import json
import os
import sys
import time
import traceback
import platform

import gnupg
import pandas as pd
import requests
from retrying import retry


def checkArgument():
    '''
    If no argument set , print help info and exit.
    '''
    if len(sys.argv) == 1:
        helpInfo()
        exit()
    return 0


def preSetup():
    '''
    Create necessary files and folder
    '''
    # message temp file
    if not os.path.exists('message.txt'):
        with open('message.txt', 'w+') as f:
            f.write('')
    # gnupg
    if not os.path.exists('gnupg'):
        os.mkdir('gnupg')
    global gpg
    systemName = platform.system()
    if systemName == 'Windows':
        gpg = gnupg.GPG(gnupghome='./gnupg',gpgbinary="./wingpg/gpg.exe")
        print('Working in Windows.')
    elif systemName == 'Linux':
        gpg = gnupg.GPG(gnupghome='./gnupg')
        print('Working in Linux.')
    else:
        gpg = gnupg.GPG(gnupghome='./gnupg',gpgbinary="./wingpg/gpg.exe")
        print('Working in ' + systemName)
    # set pandas display
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 100)
    pd.set_option('display.width', 1000)
    # configparser
    global conf
    conf = configparser.ConfigParser()
    # argsparser 1/4
    global parser
    parser = argparse.ArgumentParser(
        description="This is the help info for OpenMPRDB-Python-CLI.")
    # register sub keys 2/4
    parser.add_argument('-u', '--uuid', default='None', help=argparse.SUPPRESS)
    parser.add_argument('--max', default='45', help=argparse.SUPPRESS)
    parser.add_argument('-n', '--name', default='None', help=argparse.SUPPRESS)
    parser.add_argument('-r', '--reason', default='None',
                        help=argparse.SUPPRESS)
    parser.add_argument('-s', '--score', default='None',
                        help=argparse.SUPPRESS)
    parser.add_argument('-p', '--passphrase', default='',
                        help=argparse.SUPPRESS)
    parser.add_argument('-e', '--email', default='None',
                        help=argparse.SUPPRESS)
    parser.add_argument('-c', '--choice', default='None',
                        help=argparse.SUPPRESS)
    parser.add_argument('-m', '--mode', default='manual',
                        help=argparse.SUPPRESS)
    parser.add_argument('-w', '--weight', default='None',
                        help=argparse.SUPPRESS)
    # register main keys 3/4
    parser.add_argument('--key', action='store_true', default=False,
                        help='>>Used to generate key pair and get lists.With key "-n name -e email -i choice -p passphrase".Choice input y to save and auto fill passphrase in the future,n will not.To get a list of keys, use key "-m list"')
    parser.add_argument('--reg', action='store_true', default=False,
                        help='>>Used to register to a remote server.With key "-n server_name",and optional key "-p passphrase"')
    parser.add_argument('--new', action='store_true', default=False,
                        help='>>Used to submit a new submission.With key "-n player_name/uuid -r reason -s score",and optional key "-p passphrase"')
    parser.add_argument('--delete', action='store_true', default=False,
                        help='>>Used to delete a submission that have submitted.With key “-u submit_uuid -r reason”,and optional key "-p passphrase"')
    parser.add_argument('--shut', action='store_true', default=False,
                        help='>>Used to delete yourself from the remote server.With key "-r reason",and optional key "-p passphrase"')
    parser.add_argument('--list', action='store_true', default=False,
                        help='>>Used to get all registered servers.With an optional key "--max number",it means how many servers to list.')
    parser.add_argument('--detail', action='store_true', default=False,
                        help='>>Used to get a detail of a submission.With key "-u submit_uuid"')
    parser.add_argument('--listfrom', action='store_true', default=False,
                        help='>>Used to get all submission from a specific server.With key "-u server_uuid"')
    parser.add_argument('--update', action='store_true', default=False,
                        help='>>Used to auto update the ban list.No key required.')
    parser.add_argument('--getkey', action='store_true', default=False,
                        help='>>Used to download public key from remote server.With key "-u ServerUUID -w Weight -c Choice",choice input 1 will save and import the key,choose 3 will only save the key as a file and save to the MPRDB folder.')
    parser.add_argument('--setweight', action='store_true', default=False,
                        help='>>Used to set or change weight for a specific server.With key "-u ServerUUID -w Weight"')
    # load args 4/4
    global args
    args = parser.parse_args()


def helpInfo():
    info = '''
    This is the help info for OpenMPRDB-Python-CLI. 
      Tip : if you saved passphrase , -p is no longer required.
    
    Example:
      Example 1 : python mpr.py --key -n Steve -e steve@email.com -c y -p 12345678
      Example 2 : python mpr.py --key -m list
      Example 3 : python mpr.py --new -n Alex -r Stealing -s -0.8 -p 12345678

    --key 
      Generate a key pair : -n [Your Name] -e [Your Email] -c [Choice] -p [Passphrase]
      List all keys : -m list
        [Choice] : Whether to save passphrase and auto fill or not , input y or n.
        [Passphrase] : It had better be a long and hard to guess secret ,
                       When generating or deleting a key pair , a passphrase is always required.
    
    --reg
      Register to remote server : -n [Your Server Name] [-p [Passphrase]]

    --new 
      New submit : -n [Player Name or UUID] -r [Reason] -s [Score] [-p [Passphrase]]
        [Score] : It should be a number in range [-1,0) and (0,1]
    
    --delete
      Delete a submit you reported : -u [Submit UUID] -r [Reason] [-p [Passphrase]]
    
    --shut
      Delete your server from remote server : -r [Reason] [-p [Passphrase]]

    --list
      List servers that registered from remote server : [--max [Max amount to show]]  
    '''
    print(info)


def keyManagement():
    '''
    Solving argument --key and run specific function.
    '''
    arg_name = args.name
    arg_email = args.email
    arg_passphrase = args.passphrase
    arg_choice = str(args.choice)
    arg_mode = args.mode

    if arg_mode == 'list':
        listKeys()
        return 0
    if arg_name == 'None' or arg_email == 'None' or arg_passphrase == '' or arg_choice == 'None':
        print('Missing argument --name --email --passphrase or --choice')
        print('Check it in help page.')
    else:
        generateKeys(arg_name, arg_email, arg_passphrase, arg_choice)

    return 0


def generateKeys(name, email, passphrase, choice):
    '''
    Generate a new pair of keys.
    '''
    # generate keys
    input_data = gpg.gen_key_input(name_email=email, passphrase=passphrase, name_real=name,
                                   key_length=2048)
    # export keys to memory
    fingerprint_raw = gpg.gen_key(input_data)
    fingerprint = str(fingerprint_raw)
    ascii_armored_public_keys = gpg.export_keys(fingerprint)
    ascii_armored_private_keys = gpg.export_keys(
        fingerprint, True, passphrase=passphrase)
    # export keys to files
    with open('public_key.asc', 'w+') as f:
        f.write(ascii_armored_public_keys)
    with open('private_key.asc', 'w+') as d:
        d.write(ascii_armored_private_keys)
        # edit file mprdb.ini
    print('Done! Your keys have been saved.Your keyID: '+fingerprint[-16:])
    if choice == 'y':
        conf.read('mprdb.ini')
        conf.set('mprdb', 'save_passphrase', 'True')
        conf.set('mprdb', 'passphrase', passphrase)
        # KeyID is the last 16 bits of fingerprint
        conf.set('mprdb', 'serverkeyid', fingerprint[-16:])
        conf.write(open('mprdb.ini', 'w'))
        print('Your passphrase will be auto filled in the future.')
    if choice == 'n':
        conf.read('mprdb.ini')
        conf.set('mprdb', 'save_passphrase', 'False')
        conf.set('mprdb', 'passphrase', '')
        # KeyID is the last 16 bits of fingerprint
        conf.set('mprdb', 'serverkeyid', fingerprint[-16:])
        conf.write(open('mprdb.ini', 'w'))
    return 0


def listKeys():
    '''
    List all keys that have been saved,
    '''
    public_keys = gpg.list_keys()
    private_keys = gpg.list_keys(True)

    print("Public Keys:")
    df = pd.DataFrame(public_keys)
    df1 = df.loc[:, ['keyid', 'length', 'uids',
                     'trust', 'date', 'fingerprint']]
    print(df1)

    print("Private Keys:")
    df = pd.DataFrame(private_keys)
    df1 = df.loc[:, ['keyid', 'length', 'uids',
                     'trust', 'date', 'fingerprint']]
    print(df1)
    return 0


def loadPassphrase():
    '''
    Load passphrase.If saved,just load; if not saved,load from argument.
    '''
    conf.read('mprdb.ini')
    if conf.get('mprdb', 'save_passphrase') == 'True':
        passphrase = conf.get('mprdb', 'passphrase')
        print('Loading passphrase succeed.')
    elif args.passphrase != '':
        passphrase = args.passphrase
    else:
        print('Missing argument --passphrase.')
        exit()
    return passphrase


def generateRegisterJson():
    '''
    Generate register json in a correct format

    Read file line by line and add '\n' in the end , then join them in one line.
    '''
    public_key = ''
    with open('public_key.asc','r') as f:
        for line in f:
            line=line.strip()
            public_key = public_key + line + '\n'
    
    message = ''
    with open('message.txt.asc','r') as f:
        for line in f:
            line=line.strip()
            message = message + line + '\n'

    data = json.dumps({'message': message, 'public_key': public_key},
                      sort_keys=True, indent=2, separators=(',', ': '))
    return data


@retry(stop_max_attempt_number=3)
def putData(url, data, headers):
    response = requests.put(url, data=data, headers=headers, timeout=5)
    return response


def registerServer():
    '''
    Register yourself into remote server
    '''
    # load server name and passphrase
    server_name = args.name
    passphrase = loadPassphrase()
    # write message info : server_name
    with open("message.txt", 'r+', encoding='utf-8') as f:
        f.truncate(0)
        f.write("server_name:" + server_name)
    # get keyid
    conf.read('mprdb.ini')
    keyid = conf.get('mprdb', 'ServerKeyId')
    # sign message
    with open('message.txt', 'rb') as f:
        gpg.sign_file(f, keyid=keyid, output='message.txt.asc',
                      passphrase=passphrase)
    # check output file exists
    if not os.path.exists('message.txt.asc'):
        print('Failed to sign file. Check your key and passphrase.')
        exit()
    # put data
    data = generateRegisterJson()
    url = "https://test.openmprdb.org/v1/server/register"
    headers = {"Content-Type": "application/json"}
    res = putData(url, data, headers)

    try:
        response = res.json()
    except:
        print('An error occurred when putting data.')
        print(res)
        exit()

    # check status and edit mprdb.ini
    status = response.get("status")
    if status == "OK":
        uuid = response.get("uuid")
        print("OK! The UUID of the current device is: "+uuid)
        conf.read('mprdb.ini')
        conf.set('mprdb', 'ServerName', server_name)
        conf.set('mprdb', 'ServerUUID', uuid)
        conf.write(open('mprdb.ini', 'w'))
    if status == "NG":
        print("400 Bad Request")
        print('Status : '+response.get("status"))
        print('Reason : '+response.get("reason"))
    return 0


@retry(stop_max_attempt_number=3)
def getData(url):
    response = requests.get(url)
    return response


def getPlayerName(uuid):
    # get player name from uuid
    url = "https://sessionserver.mojang.com/session/minecraft/profile/" + uuid
    response = getData(url)
    if response.text == "":
        print("Player not found from this UUID!")
        exit()
    else:
        result = response.json()
        player_name = result["name"]
    return player_name


def getPlayerUUID(name):
    # get player uuid from name
    url = "https://playerdb.co/api/player/minecraft/" + name
    response = getData(url)

    try:
        result = response.json()
    except:
        print('An error occurred when getting data.')
        print(response)
        exit()

    if result["code"] == "player.found":
        player_uuid = result["data"]["player"]["id"]
    else:
        print("Player not found from this name!")
        exit()
    return player_uuid


def newSubmit():
    '''
    Put new submit to remote server
    '''
    # check arguments
    if args.name == 'None' or args.reason == 'None' or args.score == 'None':
        print('Missing parameter : --name or --reason or --score')
        exit()

    # load arguments and set variables
    player_info = args.name  # set player name or player uuid to player_info
    comment = args.reason
    passphrase = args.passphrase
    try:
        score = float(args.score)
    except:
        print('Score invalid ! Please input it in range [-1,0) and (0,1]')
        exit()

    player_name = ''
    player_uuid = ''
    conf.read('mprdb.ini')
    server_uuid = conf.get('mprdb', 'serveruuid')
    server_name = conf.get('mprdb', 'servername')

    # if input player's uuid , get player's name , conversely
    if len(player_info) == 36 or len(player_info) == 32:
        player_name = getPlayerName(player_info)
        player_uuid = player_info
    else:
        player_uuid = getPlayerUUID(player_info)
        player_name = player_info
    # check if score in range
    if score < -1 or score > 1 or score == 0:
        print('Score invalid ! Please input it in range [-1,0) and (0,1]')
    # get timestamp
    ticks = str(int(time.time()))

    # confirm the submit
    print("=====Confirm The Submit=====")
    print("Server UUID:" + server_uuid)
    print("Timestamp:" + ticks)
    print("Player Name:" + player_name)
    print("Player UUID:" + player_uuid)
    print("Points:" + str(score))
    print("Comment:" + comment)
    print("=============================")
    try:
        input("Press any key to submit , use Ctrl+C to cancel.")
    except:
        exit()

    # write message
    with open("message.txt", 'r+', encoding='utf-8') as f:
        f.truncate(0)
        f.write("uuid: " + server_uuid + '\n')
        f.write("timestamp: " + ticks + '\n')
        f.write("player_uuid: " + player_uuid + '\n')
        f.write("points: " + str(score) + '\n')
        f.write("comment: " + comment)

    conf.read('mprdb.ini')
    keyid = conf.get('mprdb', 'ServerKeyId')
    passphrase = loadPassphrase()

    # sign message
    with open('message.txt', 'rb') as f:
        gpg.sign_file(f, keyid=keyid, output='message.txt.asc',
                      passphrase=passphrase)

    url = "https://test.openmprdb.org/v1/submit/new"
    headers = {"Content-Type": "text/plain"}
    with open("message.txt.asc", "r", encoding='utf-8') as f:
        data = f.read()
        data = data.encode('utf-8')

    res = putData(url, data, headers)
    try:
        response = res.json()
    except:
        print('An error occurred when putting data.')
        print(res)
        exit()

    if not os.path.exists('submit.json'):
        with open('submit.json', 'w+') as f:
            f.write('{}')
    commit = {}

    status = response.get("status")
    if status == "OK":
        submit_uuid = response.get("uuid")
        print("Submitted successfully! The UUID submitted this time is: "+submit_uuid)
        eventtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        with open('submit.json', 'r', encoding='utf-8') as f:
            commit = json.loads(f.read())
        info = {'Name': player_name, 'PlayerUUID': player_uuid, 'Points': score, 'Timestamp': ticks, 'Time': eventtime,
                'Comment': comment, 'SubmitUUID': submit_uuid, 'ServerUUID': server_uuid, 'ServerName': server_name}
        commit[submit_uuid] = info

        with open('submit.json', 'w+', encoding='utf-8') as fd:
            fd.write(json.dumps(commit, indent=4, ensure_ascii=False))
    if status == "NG":
        print("400 Bad Request or 401 Unauthorized")
        print('Status : '+response.get("status"))
        print('Reason : '+response.get("reason"))

    return 0


def deleteSubmit():
    '''
    Delete a submit that has been submitted.
    '''
    delete_uuid = args.uuid
    comment = args.reason

    with open('submit.json', 'r', encoding='utf-8') as f:
        submit = json.loads(f.read())

    # exit if not found
    if not submit.get(delete_uuid):
        print('Commit not found!')
        exit()

    if not os.path.exists('submit-others.json'):
        with open('submit-others.json', 'w+') as f:
            f.write('{}')

    # load local server name and server uuid from local file
    conf.read('mprdb.ini')
    server_uuid = conf.get('mprdb', 'serveruuid')
    server_name = conf.get('mprdb', 'servername')

    print("=====Confirm the submit you want to delete=====")
    print("Server UUID:" + server_uuid)
    print("Server name:" + server_name)
    print('Delete reason: '+comment)
    df = pd.DataFrame.from_dict(submit[delete_uuid], orient='index')
    print(df)

    try:
        input("Press any key to continue , use Ctrl+C to cancel.")
    except:
        exit()

    # writing message
    ticks = str(int(time.time()))
    with open("message.txt", 'r+') as f:
        f.truncate(0)
        f.write("timestamp: " + ticks)
        f.write("\n")
        f.write("comment: " + comment)

    conf.read('mprdb.ini')
    keyid = conf.get('mprdb', 'ServerKeyId')
    passphrase = loadPassphrase()
    # sign message
    with open('message.txt', 'rb') as f:
        gpg.sign_file(f, keyid=keyid, output='message.txt.asc',
                      passphrase=passphrase)

    with open("message.txt.asc", "r") as f:
        data = f.read()
    url = "https://test.openmprdb.org/v1/submit/uuid/" + delete_uuid
    headers = {"Content-Type": "text/plain"}

    res = deleteData(url, data, headers)

    try:
        response = res.json()
    except:
        print('An error occurred when deleting this submit.')
        print(res)
        exit()

    commit = {}
    with open('submit-others.json', 'r', encoding='utf-8') as f:
        commit = json.loads(f.read())

    # check status
    status = response.get("status")
    if status == "OK":
        submit_uuid = response.get("uuid")
        print("Deleted commit successfully! The UUID submitted this time is: "+submit_uuid)
        eventtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        info = {'Type': "Delete server", 'ServerName': server_name, 'ServerUUID': server_uuid,
                'Points withdrawn': submit[delete_uuid]["Points"],
                'Original reason': submit[delete_uuid]["Comment"],
                'Playername': submit[delete_uuid]["Name"], 'Timestamp': ticks, 'Time': eventtime,
                'Reason for revocation': comment, 'SubmitUUID': submit_uuid}
        commit[submit_uuid] = info
        with open('submit-others.json', 'w+', encoding='utf-8') as fd:
            fd.write(json.dumps(commit, indent=4, ensure_ascii=False))

    if status == "NG":
        print("Submit not found in remote server , or Unauthorized")
        print('Status : '+response.get("status"))
        print('Reason : '+response.get("reason"))
    
    return 0


@retry(stop_max_attempt_number=3)
def deleteData(url, data, headers):
    response = requests.delete(url, data=data, headers=headers, timeout=5)
    return response

def deleteServer():
    '''
    Delete yourself from the remote server.
    '''
    comment = args.reason

    if not os.path.exists('submit-others.json'):
        with open('submit-others.json', 'w+') as f:
            f.write('{}')

    # load local server name and server uuid from local file
    conf.read('mprdb.ini')
    server_uuid = conf.get('mprdb', 'serveruuid')
    server_name = conf.get('mprdb', 'servername')

    print("=====Confirm to delete server=====")
    print("Server UUID:" + server_uuid)
    print("Server name:" + server_name)
    print("Comment:" + comment)
    try:
        input("Press any key to continue , use Ctrl+C to cancel.")
    except:
        exit()
    
    # writing message
    ticks = str(int(time.time()))
    with open("message.txt", 'r+') as f:
        f.truncate(0)
        f.write("timestamp: " + ticks)
        f.write("\n")
        f.write("comment: " + comment)
    
    conf.read('mprdb.ini')
    keyid = conf.get('mprdb', 'ServerKeyId')
    passphrase = loadPassphrase()

    # sign message
    with open('message.txt', 'rb') as f:
        gpg.sign_file(f, keyid=keyid, output='message.txt.asc',
                      passphrase=passphrase)

    with open("message.txt.asc", "r") as f:
        data = f.read()
    url = "https://test.openmprdb.org/v1/server/uuid/" + server_uuid
    headers = {"Content-Type": "text/plain"}

    res = deleteData(url, data, headers)

    try:
        response = res.json()
    except:
        print('An error occurred when deleting server from remote server.')
        print(res)
        exit()

    commit = {}
    with open('submit-others.json', 'r', encoding='utf-8') as f:
        commit = json.loads(f.read())

    # check status
    status = response.get("status")
    if status == "OK":
        submit_uuid = response.get("uuid")
        print("Deleted server successfully! The UUID submitted this time is: "+submit_uuid)
        eventtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        info={'Type': "Delete submit", 'ServerName': server_name, 'ServerUUID': server_uuid, 'Timestamp': ticks,
             'Time': eventtime, 'Comment': comment, 'SubmitUUID': submit_uuid}
        commit[submit_uuid]=info
        with open('submit-others.json','w+',encoding='utf-8') as fd:
            fd.write(json.dumps(commit, indent=4, ensure_ascii=False))

    if status == "NG":
        print("Server not found,or Unauthorized")
        print('Status : '+response.get("status"))
        print('Reason : '+response.get("reason"))

    return 0

def listServer():
    max = str(args.max)
    url = "https://test.openmprdb.org/v1/server/list" + "?limit=" + max

    print("Getting servers list...")
    print("The last " + max + " servers will be displayed.")
    res = getData(url)
    
    try:
        response = res.json()
    except:
        print('An error occurred when getting server list.')
        print(res)
        exit()

    df = pd.DataFrame(res["servers"])
    df1 = df.loc[:, ['id', 'key_id', 'server_name', 'uuid']]  # hide key "public_key" here, it's useless now
    print(df1)
    return 0

if __name__ == "__main__":
    checkArgument()
    preSetup()

    if args.key == True:
        keyManagement()
    if args.reg == True:
        registerServer()
    if args.new == True:
        newSubmit()
    if args.delete == True:
        deleteSubmit()
    if args.shut == True:
        deleteServer()
    if args.list == True:
        listServer()
