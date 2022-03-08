#!/usr/bin/env python
"""
    This is a Python script which is used to automate AStream clients for SABR evaluation.
"""
import socket
import numpy as np
import paramiko
import logging
import threading
import time
socket.setdefaulttimeout(5)
logging.basicConfig()

AStreamDir = "/proj/QoESDN/AStream"
user = "clarkzjw"
home = "/users/clarkzjw"
zipf_dist = dict()

# Configure runtime environment
MAX_TRIALS = 1
key_name = "id_ed25519.pub"
port = 22

# The following lists are constructed in the main method.
server_ip = []
client_ip = []
cache_ip = []

client_ports = []

client_hosts = []
client_hosts1 = []
client_hosts2 = []
client_hosts3 = []
client_hosts4 = []

client_hosts_zipf = []


def gen_zipf(a, n):
    s = np.random.zipf(a, n)
    result = (s / float(max(s))) * n
    return np.floor(result)


'''
    This API is used to reset caches before every run
'''


def dash_server(ipaddress, run):
    global user

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ipaddress, username=user, key_filename='{}/.ssh/{}'.format(home, key_name))
    except paramiko.AuthenticationException:
        print("[- server] Authentication Exception! ...")

    except paramiko.SSHException:
        print("[- server] SSH Exception! ...")

    works = ipaddress.strip('\n') + ',' + user
    print('[+ server] ' + works)
    stdin, stdout, stderr = ssh.exec_command(
        "mongorestore --collection cache1 --db cachestatus bolaodump/cachestatus/cache1.bson")

    print("stdout: {}".format(stdout.read().decode('ascii')))
    print("stderr: {}".format(stdout.read().decode('ascii')))
    ssh.close()


'''
    This API is used to run different clients with and without SABR modifications
'''


def dash_client(ipaddress, ports, zipf_index, mpd_ip):
    global user
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print("ipaddress: " + ipaddress)
        keyname = '{}/.ssh/{}'.format(home, key_name)
        print("keyname: " + keyname)
        ssh.connect(ipaddress, username=user)
    except paramiko.AuthenticationException as err:
        print("[- client] Authentication Exception: " + str(err))
    except paramiko.SSHException as err:
        print("[- client] SSH Exception: " + str(err))

    works = ipaddress.strip('\n') + ',' + user
    print('[+ client] ' + works)
    # Insert relevant player command here
    print("zipf_index " + str(int(zipf_index) + 1))
    cl_command = "cd " + AStreamDir + "; sudo python2 dist/client/dash_client.py -m http://" + str(
        mpd_ip) + "/BigBuckBunny_2s_mod" + str(int(zipf_index) + 1) + \
        "/ftp.itec.aau.at/datasets/DASHDataset2014/BigBuckBunny/2sec/BigBuckBunny_2s_mod" + str(int(zipf_index) + 1)\
        + ".mpd -p basic > /dev/null &"
    try:
        print("exec ssh command: " + cl_command)
        stdin, stdout, stderr = ssh.exec_command(cl_command)

        print("stdout: {}".format(stdout.read().decode('ascii')))
        print("stderr: {}".format(stdout.read().decode('ascii')))
        ssh.close()
    except EOFError as err:
        print("error: " + str(err))
        quit()


def build_ports(port):
    for i in range(0, len(client_ip)):
        client_ports.append(int(port))


if __name__ == "__main__":
    # Create Node Lists
    # key_name = input('Please enter the name of the private SSH key used (e.g. my_chameleon_key.pem): ')
    # client_ip = input('Please enter a space-delimited list of client IPs: ').split()
    # cache_ip = input('Please enter a space-delimited list of cache IPs: ').split()
    # server_ip = input('Please enter a space-delimited list of server IPs: ').split()
    client_ip = '10.10.2.1 10.10.2.1 10.10.2.1 10.10.2.1'.split()
    cache_ip = "10.10.1.1".split()
    server_ip = "10.10.1.1".split()

    # Create Client IP Sublists
    for i in client_ip:
        client_hosts.append(i)
        client_hosts_zipf.append(i)
    for i in client_ip[0:int(len(client_ip) / 4)]:
        client_hosts1.append(i)
    for i in client_ip[int(len(client_ip) / 4):int(len(client_ip) / 4)]:
        client_hosts2.append(i)
    for i in client_ip[int(len(client_ip) / 2):len(client_ip) - int(len(client_ip) / 4)]:
        client_hosts3.append(i)
    for i in client_ip[len(client_ip) - int(len(client_ip) / 4):len(client_ip)]:
        client_hosts4.append(i)
    # Create Client Port list
    build_ports(port)  # Build ports list with global port
    for client in client_hosts_zipf:
        zipf_dist[client] = gen_zipf(2, 49)
        print(zipf_dist[client], client)
        zipf_index = 0
    for no_of_trials in range(MAX_TRIALS):
        for repeat in range(4):
            count = 0
            while count < len(client_ip):
                concat = str(client_ip[count])
                if (concat in client_hosts1) and ((count % 2) == 0):
                    mpd_ip = cache_ip[0]
                elif (concat in client_hosts2) and ((count % 2) != 0):
                    mpd_ip = cache_ip[1]
                elif (concat in client_hosts3) and ((count % 2) == 0):
                    mpd_ip = cache_ip[2]
                elif (concat in client_hosts4) and ((count % 2) != 0):
                    mpd_ip = cache_ip[3]
                else:
                    mpd_ip = server_ip[0]
                threading.Thread(target=dash_client, args=(concat, client_ports[count], zipf_index, mpd_ip)).start()
                time.sleep(1)
                count += 1
            time.sleep(3)
            zipf_index += 1
        if MAX_TRIALS > 1:
            print("Trial {} complete!".format(no_of_trials))
            time.sleep(310.0)
    if zipf_index >= 43:
        zipf_index = 0
        for client in range(0, len(client_hosts_zipf)):
            str_zipf = str(client_hosts_zipf[client]) + str(client_ports[client])
            zipf_dist[str_zipf] = zipf_collect[z_index]
            z_index += 1
    # try:
    #
    # except Exception as e:
    #     print('[-] General Exception: ' + str(e))
