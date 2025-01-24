#!/usr/bin/env python3

import argparse
import glob
import nacl.encoding
import nacl.secret
import nacl.utils
import nacl.pwhash
import uuid
import yaml
from dataclasses import dataclass
from datetime import datetime, UTC
from dateutil.parser import parse
from os import remove, chdir, getcwd, remove, stat
from os.path import exists, isdir, expanduser
from time import time_ns


def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        help="Command: generate/verify/info",
        choices=["generate", "verify", "info"],
    )
    parser.add_argument("path", help="path of keyfile")
    parser.add_argument("--verbose", "-v", help="More verbosity", action="count", default=0)
    parser.add_argument("--password", "-p", help="Protect with password", action="store_true", default=False)
    args = parser.parse_args()

    if args.verbose > 0:
        print(f"# Verbosity = {args.verbose}")
        print(f"# Command = {args.command}")
        print(f"# Path = {args.path}")
        print(f"# Password required = {args.password}")
    return args

def check_path_for_creation(args: dict):
    if exists(args.path):
        print(f"The file {args.path} already exist. "
              "Do not destroy a key that is in use of existing campaign archives. ")
        while (True):
            print("Do you want to overwrite Y/N? ", end='')
            answer = input()
            if answer == 'N' or answer == 'n':
                exit(1)
            if answer == 'Y' or answer == 'y':
                break
    else:
        try:
            with open(args.path, 'wb') as f:
                f.write(b'test')
            remove(args.path)
        except:
            print(f"Could not create/write to {args.path}")
            exit(1)

def check_path_for_reading(args: dict):
    if not exists(args.path):
        print(f"Could not find {args.path}")
        exit(1)

def generate_key(args: dict, hint: str, pwd: bytes=None) -> dict:
    doc = {}
    d = datetime.now(UTC)
    doc['time'] = d.isoformat()
    doc['hint'] = hint

    # Generate a secret key
    key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)

    # Encrypt hint for verification
    box = nacl.secret.SecretBox(key)
    nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
    doc['hint_encrypted'] = box.encrypt(bytes(hint, 'utf-8'), nonce).hex()

    # Generate a UUID for the key
    doc['id'] = uuid.uuid4().hex

    if pwd:
        kdf = nacl.pwhash.argon2i.kdf
        salt = nacl.utils.random(nacl.pwhash.argon2i.SALTBYTES)
        pkey = kdf(nacl.secret.SecretBox.KEY_SIZE, pwd, salt,
                 opslimit=nacl.pwhash.argon2i.OPSLIMIT_INTERACTIVE, 
                 memlimit=nacl.pwhash.argon2i.MEMLIMIT_INTERACTIVE)
        pbox = nacl.secret.SecretBox(pkey)
        pnonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        doc['key'] = pbox.encrypt(key, pnonce).hex()
        doc['salt'] = salt.hex()
    else:
        doc['key'] = key.hex()

    return doc

def write_key(args: dict, key: dict) -> None:
    # Writing the key to a YAML file
    with open(args.path, 'w') as file:
        yaml.dump(key, file)

def info_key(args:dict, do_verify: bool=False):
    with open(args.path, 'r') as file:
        doc = yaml.safe_load(file)
    print(f"created on: {datetime.fromisoformat(doc['time'])}")
    print(f"      hint: {doc['hint']}")
    print(f"      uuid: {doc['id']}")
    if 'salt' in doc:
        print(f"      encryption: password")
    else:
        print(f"      encryption: none")


    if do_verify:
        key = bytes.fromhex(doc['key'])
        if 'salt' in doc:
            salt = bytes.fromhex(doc['salt'])
            print("Password protected key. Type password: ", end='')
            pwd = bytes(input(), 'utf-8')
            kdf = nacl.pwhash.argon2i.kdf
            pkey = kdf(nacl.secret.SecretBox.KEY_SIZE, pwd, salt,
                            opslimit=nacl.pwhash.argon2i.OPSLIMIT_INTERACTIVE, 
                            memlimit=nacl.pwhash.argon2i.MEMLIMIT_INTERACTIVE)
            pbox = nacl.secret.SecretBox(pkey)
            key = pbox.decrypt(key)

        box = nacl.secret.SecretBox(key)
        encrypted_hint = bytes.fromhex(doc['hint_encrypted'])
        hint = box.decrypt(encrypted_hint).decode('utf-8')
        if hint == doc['hint']:
            print("Key is valid")
        else:    
            print("Key is invalid")

if __name__ == "__main__":
    args = setup_args()

    if args.command == "generate":
        check_path_for_creation(args)
        print("Type a hint for this key: ", end='')
        hint = input()
        if args.password:
            print("Type a password for this key: ", end='')
            pwd = bytes(input(), 'utf-8')
        else:
            pwd = None
        key = generate_key(args, hint, pwd)
        write_key(args, key)
    
    elif args.command == "verify":
        info_key(args, do_verify=True)

    elif args.command == "info":
        info_key(args)
    
else:
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    args.verbose = 0
    args.command = "Need to be set manually"
    args.path = "Need to be set manually"
    print("We are in import mode")
