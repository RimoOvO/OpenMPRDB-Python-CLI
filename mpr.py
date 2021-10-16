# -*- coding: utf-8 -*-
import argparse
import configparser
import json
import os
import sys
import time
import traceback
import platform
import base64
import shutil
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
        gpg = gnupg.GPG(gnupghome='./gnupg', gpgbinary="./wingpg/gpg.exe")
        # print('Working in Windows.')
    elif systemName == 'Linux':
        gpg = gnupg.GPG(gnupghome='./gnupg')
        # print('Working in Linux.')
    else:
        gpg = gnupg.GPG(gnupghome='./gnupg', gpgbinary="./wingpg/gpg.exe")
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
    parser.add_argument('--max', default='50', help=argparse.SUPPRESS)
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
    parser.add_argument('-f1', '--function1', action='store_false', default=True,
                        help=argparse.SUPPRESS)  # for update>>pullSubmitFromTrustedServer() , to disable it
    parser.add_argument('-f2', '--function2', action='store_false', default=True,
                        help=argparse.SUPPRESS)  # for update>>generateReputationBase() , to disable it
    parser.add_argument('-f3', '--function3', action='store_false', default=True,
                        help=argparse.SUPPRESS)  # for update>>generateBanList() , to disable it
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
    # folder : TrustPublicKey
    if not os.path.exists('TrustPublicKey'):
        os.mkdir('TrustPublicKey')
    # folder : TrustPlayersList
    if not os.path.exists('TrustPlayersList'):
        os.mkdir('TrustPlayersList')
    # file : weight.json
    if not os.path.exists('weight.json'):
        with open('weight.json', 'w+') as f:
            f.write('{}')
    # file : players_map.json
    if not os.path.exists('players_map.json'):
        with open('players_map.json', 'w+') as f:
            f.write('{}')


def helpInfo():
    info = '''
    This is the help page for OpenMPRDB-Python-CLI. 

    Example:
      Example 1 : python mpr.py --key -n Steve -e steve@email.com -c y -p 12345678 -r keyForServer
      Example 2 : python mpr.py --key -m list
      Example 3 : python mpr.py --new -n Alex -r Stealing -s -0.8 -p 12345678

    --key 
      Generate a key pair : -n [Your Name] -e [Your Email] -c [Choice] -p [Passphrase] [-r [Remarks]]
      List all keys : -m list
        [Choice] : Whether to save passphrase and auto fill or not , input y or n.
                   If you saved passphrase , -p is no longer required in other functions.
        [Passphrase] : It had better be a long and hard to guess secret ,
                       When generating or deleting a key pair , a passphrase is always required.
        [Remarks] : Key notes, it's optional.

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
      
    --getkey
      Download server public key that you trusted from remote server. : -u [Server UUID] -w [Weight] -c [Choice]
      [Choice] : If you want to import the key : leave empty ; if you want to just download : use -c download or -c d
      [Weight] : It should be in range (0,5].

    --setweight
      Set weight for a specific server : -u [Server UUID] -w [Weight]
      [Weight] : It should be in range (0,5]

    --detail 
      Get a detail of a submit , from submit uuid : -u [Ubumit UUID]

    --listfrom
      List all submits from a server : -u [Server UUID]

    --update
      Update ban list.

        disable argument : (optional)
        pullSubmitFromTrustedServer() >> -f1
        generateReputationBase() >> -f2
        generateBanList() >> -f3

        Example,you only want to generate a new ban list , use :
        python mpr.py --update -f1 -f2 , to disable the first two functions
      
    '''
    print(info)
    return 0


def keyManagement():
    '''
    Solving argument --key and run specific function.
    '''
    arg_name = args.name
    arg_email = args.email
    arg_passphrase = args.passphrase
    arg_choice = str(args.choice)
    arg_mode = args.mode
    arg_comment = args.reason

    if arg_mode == 'list':
        listKeys()
        return 0
    if arg_name == 'None' or arg_email == 'None' or arg_passphrase == '' or arg_choice == 'None':
        print('Missing argument --name --email --passphrase or --choice')
        print('Check it in help page.')
    else:
        generateKeys(arg_name, arg_email, arg_passphrase,
                     arg_choice, arg_comment)

    return 0


def generateKeys(name, email, passphrase, choice, comment):
    '''
    Generate a new pair of keys.
    '''
    # generate keys
    input_data = gpg.gen_key_input(name_email=email, passphrase=passphrase, name_real=name,
                                   key_length=2048, name_comment=comment)
    print(input_data)
    # get fingerprint
    fingerprint_raw = gpg.gen_key(input_data)
    fingerprint = str(fingerprint_raw)
    # check status
    if fingerprint == '':
        print('Failed! Try again or check the folders gnupg and wingpg.')
        exit()
    # export keys to memory
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
        passphrase_64 = str(base64.b64encode((passphrase).encode("utf-8")))
        conf.set('mprdb', 'passphrase', passphrase_64[2:-1])
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
        passphrase_64 = conf.get('mprdb', 'passphrase')
        passphrase = base64.b64decode(passphrase_64).decode("utf-8")
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
    with open('public_key.asc', 'r') as f:
        for line in f:
            line = line.strip()
            public_key = public_key + line + '\n'

    message = ''
    with open('message.txt.asc', 'r') as f:
        for line in f:
            line = line.strip()
            message = message + line + '\n'

    data = json.dumps({'message': message, 'public_key': public_key},
                      sort_keys=True, indent=2, separators=(',', ': '))
    return data


@retry(stop_max_attempt_number=3)
def putData(url, data, headers):
    '''
    Request method: PUT
    '''
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
    '''
    Request method: GET
    '''
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
    '''
    Request method: DELETE
    '''
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

        info = {'Type': "Delete submit", 'ServerName': server_name, 'ServerUUID': server_uuid, 'Timestamp': ticks,
                'Time': eventtime, 'Comment': comment, 'SubmitUUID': submit_uuid}
        commit[submit_uuid] = info
        with open('submit-others.json', 'w+', encoding='utf-8') as fd:
            fd.write(json.dumps(commit, indent=4, ensure_ascii=False))

    if status == "NG":
        print("Server not found,or Unauthorized")
        print('Status : '+response.get("status"))
        print('Reason : '+response.get("reason"))

    return 0


def listServer():
    '''
    List servers that registered in remote server.
    Use --max to limit the amount to display.
    '''
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

    df = pd.DataFrame(response["servers"])
    # hide key "public_key" here, it's useless now
    df1 = df.loc[:, ['id', 'key_id', 'server_name', 'uuid']]
    print(df1)
    return 0


def weightServer(server_uuid, weight):
    '''
    Set weight for a specific server.
    '''
    if weight <= 0 or weight > 5:
        print('Invalid weight value . It should be in range (0,5] ')
        exit()

    with open("weight.json", 'r') as f:
        key_list = json.loads(f.read())

    key_list[server_uuid] = weight

    with open("weight.json", "w") as fp:
        fp.write(json.dumps(key_list, indent=4))
    return 0


def serverInfoMap(id, info: str):
    '''
    By receving server id and return data which you want.
    id can be 16/32/36 bites , info is a string , it can be "public_key" "name" or "uuid".
    id --> info
    uuid>>public_key , shortid>>public_key , shortid>>name , shortid>>name , shortid>>uuid
    '''
    if len(id) == 36 and info == 'uuid':  # uuid to uuid , just return
        return id

    if len(id) == 32 and info == 'uuid':  # 32uuid to 36uuid
        id = id[:8] + '-' + id[8:12] + '-' + id[12:16] + '-' + \
            id[16:20] + '-' + id[20:]  # change 32 bits id to 36 bits
        return id  # return 36uuid

    url = "https://test.openmprdb.org/v1/server/list"
    res = getData(url)
    try:
        response = res.json()
    except:
        print('An error occurred when getting server list.')
        print(res)
        exit()

    if len(id) == 36 and info == 'public_key':  # uuid>>public_key
        uuid_dict = {}  # dict "uuid":"public_key"
        for items in response["servers"]:
            uuid = str(items["uuid"])
            public_key = str(items["public_key"])
            uuid_dict[uuid] = public_key
        return uuid_dict[id]

    if len(id) == 16 and info == 'public_key':  # shortid>>public_key
        keyid_dict = {}  # dict "key_id":"public_key"
        for items in response["servers"]:
            keyid = str(items["key_id"])
            public_key = str(items["public_key"])
            keyid_dict[keyid] = public_key
        return keyid_dict[id]

    if len(id) == 36 and info == 'name':  # shortid>>name
        uuid_name_dict = {}  # dict "uuid":"name"
        for items in response["servers"]:
            uuid = str(items["uuid"])
            name = str(items["server_name"])
            uuid_name_dict[uuid] = name
        return uuid_name_dict[id]

    if len(id) == 16 and info == 'name':  # shortid>>name
        keyid_name_dict = {}  # dict "key_id":"name"
        for items in response["servers"]:
            keyid = str(items["key_id"])
            name = str(items["server_name"])
            keyid_name_dict[keyid] = name
        return keyid_name_dict[id]

    if len(id) == 16 and info == 'uuid':  # shortid>>uuid
        keyid_uuid_dict = {}  # dict "key_id":"uuid"
        for items in response["servers"]:
            keyid = str(items["key_id"])
            uuid = str(items["uuid"])
            keyid_uuid_dict[keyid] = uuid
        return keyid_uuid_dict[id]


def downloadKey(server_uuid, public_key):
    '''
    Save server public key as a file and use server uuid as its file name.
    '''
    file_name = server_uuid
    with open(file_name, 'w') as f:
        f.write(public_key)
    return 0


def importKey(server_uuid):
    '''
    Import the server public key to local database.
    '''
    filepath = "./TrustPublicKey/" + server_uuid  # import key file
    key_data = open(filepath).read()
    import_result = gpg.import_keys(key_data)
    result = import_result.results
    result = result[0]
    print('Fingerprint: ' + result['fingerprint'])
    print('StateCode: ' + result['ok'])
    print('Result: ' + result['text'])
    return 0


def getServerKey():
    '''
    Download server public key that you trusted from remote server.
    mode : save or only download
    '''
    serverid = args.uuid  # can be long or short
    weight = float(args.weight)
    choice = args.choice

    if choice == 'download' or choice == 'd':  # check in download mode
        if args.uuid == 'None':
            print('Missing argument --uuid.')
            exit()
    elif args.uuid == 'None' or args.weight == 'None':  # check in normal mode
        print('Missing argument --uuid or --weight.')
        exit()

    # two kinds of uuid , long:36 and short:16
    if len(serverid) == 16:
        server_name = serverInfoMap(serverid, 'name')
        server_uuid = serverInfoMap(serverid, 'uuid')
    if len(serverid) == 36:
        server_name = serverInfoMap(serverid, 'name')
        server_uuid = serverid

    print("=====Confirm the Server Info=====")
    print("Server Name:" + server_name)
    print("Server UUID:" + server_uuid)
    print("Server key_id:" + serverid)
    print("Public key block:")
    print(serverInfoMap(server_uuid, 'public_key'))
    try:
        input("Press any key to continue , use Ctrl+C to cancel.")
    except:
        exit()

    if choice == 'd' or choice == 'download':  # only download key as a file
        downloadKey(server_uuid, serverInfoMap(server_uuid, 'public_key'))
        print('Public key has saved to file.')
        exit()

    if choice == 'None':  # save and import
        downloadKey(server_uuid, serverInfoMap(server_uuid, 'public_key'))
        try:
            shutil.move(server_uuid, "TrustPublicKey")
        except:
            print('Already saved.')
            os.remove(server_uuid)
        importKey(server_uuid)
        weightServer(server_uuid, weight)

    return 0


def getDetailListFromServer(mode: str):
    '''
    List all submits from a server.
    mode can be normal or call
    If you call this function in main function , set mode to normal , it will display a list. 
    If you call this function in other function , set mode to call , is will return the submit dict.
    '''
    serverid = args.uuid
    server_uuid = serverInfoMap(serverid, "uuid")
    url = "https://test.openmprdb.org/v1/submit/server/" + server_uuid

    res = getData(url)
    try:
        response = res.json()
    except:
        print('An error occurred when getting data.')
        print(res)
        exit()

    if mode == 'call':
        return response

    try:
        df1 = pd.DataFrame(response["submits"])
    except:
        print("This server may not exist or may have been deleted.")
        print(res)
        exit()

    print(df1)
    return 0


def getSubmitDetail():
    '''
    Get a submit detail by a submit uuid
    '''
    submit_uuid = args.uuid
    url = "https://test.openmprdb.org/v1/submit/uuid/" + submit_uuid

    res = getData(url)
    try:
        response = res.json()
    except:
        print('An error occurred when getting data.')
        print(res)
        exit()

    print('Submit UUID: ' + response['uuid'])
    print('Server UUID: ' + response['server_uuid'])
    print('Content: \n' + response['content'])

    status = response.get("status")
    if status == "NG":
        print("400 Bad Request or 404 Not found")
        print("This submission may not exist or may have been deleted.")

    return 0


def deleteRevokedSubmit(local_submit, remote_submit, server_uuid):
    '''
    Delete the local submits that have been revoked in remote server.
    '''
    for items in local_submit:
        if items not in remote_submit:
            os.remove('TrustPlayersList/'+server_uuid+'/'+items)
            print('Revoked submit: '+items)
    return 0


def pullSubmitFromTrustedServer():
    '''
    Pull submits from trusted servers
    '''
    start = time.time()
    count = 0
    submit_count = 0
    server_count = 0

    file_dir = "TrustPublicKey"
    key_list = os.listdir(file_dir)  # list
    error_key = []
    error_code = []
    server_all_count = len(key_list)
    error_submit = []
    error_submit_server = []
    error_submit_server_count = 0

    # load the keys that prepared to pull
    for key in key_list:
        server_error = False
        server_count += 1
        submit_count = 0
        remote_submit = []
        print("=====================")
        print("Now loading server :" + key + " --<Server:" +
              str(server_count) + "/" + str(server_all_count) + ">")
        url = "https://test.openmprdb.org/v1/submit/server/" + key
        response = getData(url)

        print("HTTP status code: " + str(response.status_code))
        if response.status_code >= 400:
            print("An error occurred. Please try again later.")
            print("This key may be no longer available. Skip...")
            error_key.append(key)
            error_code.append(response.status_code)
            continue

        res = response.json()
        submits = res["submits"]
        submit_all_count = len(submits)
        local_submit = os.listdir('TrustPlayersList/' + key)

        for items in submits:  # decrypt
            submit_count += 1
            submit_uuid = items["uuid"]

            remote_submit.append(submit_uuid)
            if submit_uuid in local_submit:
                continue

            server_uuid = items["server_uuid"]
            content = items["content"]
            print("Now solving submit: " + submit_uuid + " --<Submit:" + str(submit_count) + "/" + str(
                submit_all_count) + ">" + " --<Server:" + str(server_count) + "/" + str(server_all_count) + ">")
            with open("temp.txt", 'w+', encoding='utf-8') as f:
                f.write(content)

            # result = subprocess.check_output("gpg --decrypt temp.txt", shell=True, stderr=subprocess.STDOUT,
            # stdin=subprocess.PIPE)  # gpg shell's output can't be got completely
            verify = False
            with open('temp.txt', 'rb') as f:
                verified = gpg.verify_file(f)
            if not verified:
                verify = False
            else:
                verify = True

            if verify:
                print("Good Signature. Saving....")
                path_name = './TrustPlayersList/' + server_uuid
                if not os.path.exists(path_name):
                    os.makedirs(path_name)
                try:
                    os.rename('temp.txt', submit_uuid)
                    shutil.move(submit_uuid, path_name)
                except:
                    print("Already Saved.Skip..")
                    os.remove(submit_uuid)
                count += 1
            else:
                print(str(submit_uuid) + " is not valid! skip...")
                error_submit.append(submit_uuid)
                error_submit_server.append(key)
                server_error = True
        if server_error:
            error_submit_server_count += 1
        deleteRevokedSubmit(local_submit, remote_submit, key)

    end = time.time()
    print("Pulled " + str(count) + " submit<s>.")
    print("Total time: " + str(end - start) + " second<s>.")
    print("=====================")

    # print error servers
    if len(error_key) >= 1:
        print("There was a problem pulling submissions from the following " +
              str(len(error_key)) + " server<s>")
        i = 0
        for items in error_key:
            print("Server UUID: " + str(items) +
                  " ,HTTPcode=" + str(error_code[i]))
            i += 1
    else:
        print("All servers responded correctly.")
    print("=====================")

    # print error submits
    if len(error_submit) >= 1:
        print("There was a problem verifying the signatures of the following " + str(
            len(error_submit)) + " submit<s>,from " + str(error_submit_server_count) + " server<s>")
        i = 0
        # solving the foling i-1
        error_submit_server.append(error_submit_server[0])
        print("\n")
        print("  >> from server: " + error_submit_server[0])
        for items in error_submit:
            if error_submit_server[i] != error_submit_server[i - 1]:
                print("  >> from server: " + error_submit_server[i])
            print("Submit UUID: " + str(items))
            i += 1
    else:
        print("All signatures have been verified well and saved.")

    return 0


def generateReputationBase():
    '''
    Generate local reputation base
    '''
    reputation = {}
    start = time.time()
    count = 0

    # load weight file
    with open("weight.json", 'r') as f:
        weight = json.loads(f.read())

    file_dir = "TrustPlayersList"
    server_list = os.listdir(file_dir)  # server list

    for server in server_list:
        submit_list = os.listdir(file_dir + "/" + server)  # submit list

        if weight.get(server) is None:
            print("Server : " + server + " has no weight set.")
            input("Press any key to exit")
            exit()
        else:
            # The weight of each trusted server is different
            pownum = float(weight.get(server))

        for submit in submit_list:
            submit_dir = file_dir + "/" + server + "/" + submit
            with open(submit_dir, 'r', encoding='utf-8') as f:
                content = f.read()
            uuid_index = content.find("player_uuid:")
            if content[uuid_index + 12] == " ":  # with space
                player_uuid = content[uuid_index + 13:uuid_index + 49]
            if content[uuid_index + 12] != " ":  # without space
                player_uuid = content[uuid_index + 12:uuid_index + 48]
            point_index = content.find("points:")
            if content[point_index + 7] == " ":  # with space
                i = 0
                while True:  # get point number,accept decimals
                    i += 1
                    point_end_index = point_index + 7 + i
                    if content[point_end_index] == "." or content[point_end_index] == "-":
                        continue
                    try:
                        int(content[point_end_index])
                    except:
                        break
                # point before being weighted
                player_point_ori: float = float(
                    content[point_index + 8:point_end_index])
                # point after being weighted
                player_point = float(
                    content[point_index + 8:point_end_index]) * pownum
            if content[point_index + 7] != " ":  # without space
                i = 0
                while True:  # get point number,accept decimals
                    i += 1
                    point_end_index = point_index + 6 + i
                    # Handle decimal points and minus signs
                    if content[point_end_index] == "." or content[point_end_index] == "-":
                        continue
                    try:
                        int(content[point_end_index])
                    except:
                        break
                player_point_ori = float(
                    content[point_index + 7:point_end_index])
                player_point = float(
                    content[point_index + 7:point_end_index]) * pownum
                # print(player_point)

            # If the player is not in the local reputation library, create a new record.
            # If it is, add it to the original value.
            if reputation.get(player_uuid) is None:
                reputation[player_uuid] = player_point
                sump = player_point
            else:
                sump = reputation[player_uuid]
                sump = sump + player_point
                reputation[player_uuid] = sump
            print('  >>From submit : '+submit)
            print("Solving player: " + player_uuid)
            print("With points: " + str(player_point_ori) + ", Magnification: " + str(pownum) + "x, Total points: " + str(
                sump))
            print("\n")
            count += 1

    with open("reputation.json", "w+") as fp:
        fp.write(json.dumps(reputation, indent=4))

    end = time.time()
    print("=====================")
    print("Solved " + str(count) + " submit<s>.")
    print("Total time: " + str(end - start) + " second<s>.")
    print("=====================")
    return 0


def backup(banlistIsNew: bool):
    '''
    Backup old ban list to folder ./backup
    If banlist is new created , it will not be backup
    '''
    if banlistIsNew == True:
        return 0

    timepoint = str(time.strftime("%Y%m%d-%H%M%S", time.localtime()))
    if not os.path.exists("backup"):
        os.makedirs("backup")
    filename = "banned-players-backup-" + timepoint + ".json"
    os.rename('banned-players.json', filename)
    shutil.copy(filename, "backup/")
    os.rename(filename, 'banned-players.json')
    return 0


def playersMapGet(player_uuid):  # uuid to name
    '''
    Get player name from local players_map.json , to increase of efficiency
    '''
    players_map = {}
    with open('players_map.json', 'r') as f:
        players_map = json.loads(f.read())
    player_name = players_map.get(player_uuid, '-1')
    return player_name


def playersMapSave(player_uuid, player_name):  # save uuid and name to file
    '''
    Save the player that isnt in the players_map.json , to increase of efficiency
    '''
    players_map = {}
    with open('players_map.json', 'r') as f:
        players_map = json.loads(f.read())
    players_map[player_uuid] = player_name
    with open('players_map.json', 'w+') as d:
        d.write(json.dumps(players_map, indent=4, ensure_ascii=False))
    return 0


def newList(banlist):
    # create new ban list
    conf.read('mprdb.ini')
    file_server_banlist = conf.get('mprdb', 'banlist_path')

    with open("banned-players.json", "w+", encoding='utf-8') as fp:
        fp.write(json.dumps(banlist, indent=4, ensure_ascii=False))
    try:
        shutil.copy('banned-players.json', file_server_banlist)
        print('Copying file to server folder...')
    except:
        print('Unable to copy file to server folder.')
    return 0


def searchOnline(player_uuid, i, changed, banlist, banlistIsNew):  # return (name or code,i)
    '''
    player uuid to player name , from mojang
    if ban list changed and mojang site crashed , return code -2 , and save ban list
    if ban list not changed and mojang site crashed , return code -3
    if player not found , return code -1
    if player found , return player name
    '''
    url = "https://sessionserver.mojang.com/session/minecraft/profile/" + \
        player_uuid  # get player name
    try:
        res = getData(url)
    except:
        if changed:
            backup(banlistIsNew)
            newList(banlist)
            return "-2", i
        else:
            return "-3", i

    if res.text == "":
        i += 1
        return '-1', i
    else:
        result = res.json()
        player_name = result["name"]
    return player_name, i


def generateBanList():
    '''
    Generate a new ban list , the old will be backup in ./backup
    If the server path is correct , the banned-players.json will be copied here
    then edit it and send back.
    If the server path is not correct ,a new banned-players.json will be generated.
    '''
    conf.read('mprdb.ini')
    min_point_toban = float(conf.get('mprdb', 'min_point_toban'))
    file_reputation = "reputation.json"
    file_server_banlist = conf.get('mprdb', 'banlist_path')
    source = conf.get('mprdb', 'ban_source')
    expires = conf.get('mprdb', 'ban_expires')
    reason = conf.get('mprdb', 'ban_reason')
    changed = False
    banlistIsNew = False

    try:
        shutil.copy(file_server_banlist, os.getcwd())
        print('Server ban list found,using list: '+file_server_banlist)
    except:
        print('Server ban list not found! Generating...')
        banlistIsNew = True  # if it is new , it will not be backup , because it's empty
        with open('banned-players.json', 'w+') as f:
            f.write('[]')

    # load old ban list and local reputation
    with open(file_reputation, "r", encoding='utf-8') as f:
        reputation = json.loads(f.read())
    with open('banned-players.json', "r", encoding='utf-8') as d:
        banlist = json.loads(d.read())

    already_exist_player = []  # Prevent duplication
    for items in banlist:  # type(items)=dict
        already_exist_player.append(items["uuid"])

    banamount = 0  # For progress bar
    for player_uuid in reputation:
        if reputation[player_uuid] <= min_point_toban and player_uuid not in already_exist_player:
            banamount += 1

    i = 0
    # if a player in local reputation with a low point , and he isn't in the old ban list
    # he will be add to the new ban list
    for player_uuid in reputation:
        if reputation[player_uuid] <= min_point_toban and player_uuid not in already_exist_player:
            if playersMapGet(player_uuid) != '-1':
                player_name = playersMapGet(player_uuid)
                i += 1
            else:
                player_name, i = searchOnline(
                    player_uuid, i, changed, banlist, banlistIsNew)
                if player_name == '-3':
                    print(
                        "An error occurred while searching the player.Try again later.")
                    print('Nothing changed.')
                    exit()
                if player_name == '-2':
                    print(
                        "An error occurred while searching the player.Try again later.")
                    print('Solved '+str(i)+' item<s>.')
                    exit()
                if player_name == '-1':
                    print("Player: " + player_uuid + " not found! < " +
                          str(i)+" / "+str(banamount)+" >")
                    continue
                playersMapSave(player_uuid, player_name)
                i += 1

            print("Now adding player: " + player_name + " ,UUID: " +
                  player_uuid + " to ban list. < "+str(i)+" / "+str(banamount)+" >")
            created = str(time.strftime("%Y-%m-%d %H:%M:%S",
                          time.localtime())) + " +0800"
            info = {'uuid': player_uuid, 'name': player_name, 'created': created,
                    'source': source, 'expires': expires, 'reason': reason}
            # print(info)
            banlist.append(info)  # new ban list
            # print(banlist)
            changed = True
    if changed:
        print('Solved '+str(i)+' item<s>.')
        backup(banlistIsNew)
        newList(banlist)
    else:
        print('Nothing changed.')

    return 0


def updateMainController():
    '''
    Update main controller.
    if you want to disable one or more following function(s) , use -f1 -f2 -f3 to disable them

    disable argument : 
    pull Submit From Trusted Server >> -f1
    generate Reputation Base >> -f2
    generate Ban List >> -f3

    Example,you only want to generate a new ban list ,  use python mpr.py --update -f1 -f2 , to disable the first two functions
    '''
    f1 = f2 = f3 = True

    f1 = args.function1
    f2 = args.function2
    f3 = args.function3

    if f1:
        pullSubmitFromTrustedServer()
    if f2:
        generateReputationBase()
    if f3:
        generateBanList()

    return 0


if __name__ == "__main__":
    checkArgument()
    preSetup()
    if args.key == True:
        keyManagement()
    elif args.reg == True:
        registerServer()
    elif args.new == True:
        newSubmit()
    elif args.delete == True:
        deleteSubmit()
    elif args.shut == True:
        deleteServer()
    elif args.list == True:
        listServer()
    elif args.getkey == True:
        getServerKey()
    elif args.setweight == True:
        server_uuid = args.uuid
        weight = float(args.weight)
        weightServer(server_uuid, weight)
        print('Set server seight: ' + server_uuid + ' to ' + args.weight)
    elif args.listfrom == True:
        getDetailListFromServer('normal')
    elif args.detail == True:
        getSubmitDetail()
    elif args.update == True:
        updateMainController()
    else:
        print('The main argument is missing!')
