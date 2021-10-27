# OpenMPRDB-Python-CLI

### Environment : Python 3

Using network proxy may cause some errors.

### Python components

1. requests

2. retrying

3. pandas

4. python-gnupg

install then manually or use pip install -r requirements.txt

### This is the help page for OpenMPRDB-Python-CLI. 

    Example:
      Example 1 : python mpr.py --key -n Steve -e steve@email.com -c y -p 12345678 -r keyForServer
      Example 2 : python mpr.py --key -m list
      Example 3 : python mpr.py --new -n Alex -r Stealing -s -0.8 -p 12345678

    --key 
      Generate a key pair : -n [Your Name] -e [Your Email] -c [Choice] -p [Passphrase] [-r [Remarks]]
      List all keys : -m list
      Delete a key pair : -m delete -u [Key Fingerprint]
      Import a key : -m import -n [File Name]
      Export a key : -m export -u [Key ID] -c [Export private key]
      Sign a file : -m sign [-n [Input File Name]] [-n2 [Output File Name]] [-u [KeyID]] [-p [Passphrase]]
      Vertigy a file : -m vertify -n [File Name]
        [Choice] : Whether to save passphrase and auto fill or not , input y or n.
                   If you saved passphrase , -p is no longer required in other functions.
        [Passphrase] : It had better be a long and hard to guess secret ,
                       When generating or deleting a key pair , a passphrase is always required.
        [Remarks] : Key notes, it's optional.
        [Key Fingerprint] : You will get it in key list.
        [Export private key] : Fill true or just leave empty , whether to export its private key.
        Sign a message : All args are optional , the default value : -n message.txt -n2 message.txt.asc -u YourServerKeyID -p SavedPassphrase

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
    
    --push
      Push local submits that your server created to remote server : [-n [BanList Path]]
      [BanList Path] : Optional, to define a ban list, the default is in mpr.ini 

    --update
      Update local and remote ban list.

        disable argument : (optional)
        pull Submit From Trusted Server >> -f1
        generate Reputation Base >> -f2
        generate Ban List >> -f3
        push local ban list >> -f4
        auto undo revoked submit >> -f5

    Example ,you only want to generate a new ban list ,  use 
    python mpr.py --update -f1 -f2 -f4 -f5 , to disable the other functions
