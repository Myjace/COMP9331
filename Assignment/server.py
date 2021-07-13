"""Server side"""
from socket import *
import threading
import time
import sys


# Class ------------------------------------------------------------------
class User:
    """Create a User class to record necessary info related to each user who login successfully"""
    def __init__(self, username, conn, addr, login_time, logout_time):
        self.username = username
        self.conn = conn
        self.addr = addr
        self.login_time = login_time
        self.logout_time = logout_time
        self.black_list = []


# Functions --------------------------------------------------------------
""" Functions to deal with transactions """


def authentication(username, password, conn, addr, login, blocked, users, time_block, online):
    """Login Authentication"""
    # Use a flag to count try times
    flag = 0
    e_type = 0

    while True:
        # Check whether this username is valid or not
        if username not in login.keys():
            reply = 'No such account'
            conn.send(reply.encode())
            e_type = 2
            break

        # Check whether this user has logged in or not
        if username in online.keys():
            reply = 'Already login, cannot login again'
            conn.send(reply.encode())
            e_type = 1
            break

        # Check whether this user is blocked or not
        if username in blocked:
            reply = 'Your account is blocked due to multiple login failure. Please try again later'
            conn.send(reply.encode())
            e_type = 1
            break

        if flag > 0:
            password = conn.recv(1024).decode()

        # Check whether username & password are correct
        if login[username] == password:
            # if correct, break this loop, login success
            reply = 'Welcome to the greatest messaging application ever!'
            conn.send(reply.encode())
            break
        else:
            # After 3 tries, block user
            if flag == 2:
                blocked.append(username)
                unblock_t(blocked, username, time_block)
                # print(blocked)
                reply = 'Invalid Password. Your account has been block. Please try again later'
                conn.send(reply.encode())
                e_type = 1
                break

            # Try time not exceed 3 times
            else:
                reply = 'Invalid Password. Please try again'
                conn.send(reply.encode())
                flag += 1

    if e_type == 0:
        # Once login successfully, create a new User object and add it to users list
        login_time = time.time()
        user = User(username, conn, addr, login_time, 0)
        users.append(user)
        if username not in online.keys():
            online[username] = conn
        return 1
    elif e_type == 2:
        return 2
    else:
        return 0


def unblock(blocked, username):
    """"Unblock user"""
    blocked.remove(username)


def unblock_t(blocked, username, time_block):
    """Implement unblock with a timer"""
    t = threading.Timer(time_block, unblock, (blocked, username,))
    t.start()


def handle_recv(conn, con, username, time_out):
    """Target function which to handle 'receiving transactions'"""
    global data
    while True:
        try:
            conn.settimeout(time_out)
            temp = conn.recv(1024).decode()
            if not temp:
                # If server cannot receive any data, shut down this connection
                conn.close()
                return
            notify(temp, con)
        except timeout:
            reply = 'timeout' + username
            print(username + ' timeout')
            notify(reply, con)
            conn.close()
            return


def handle_send(conn, con, online, users):
    """Target function which to handle 'sending transactions'"""
    global data
    while True:
        if con.acquire():
            # wait to be notified
            con.wait()
            if data:
                # try:
                # Process receiving data
                seq = data.split()
                # print(seq)
                if len(seq) > 1:
                    command = seq[1]
                    sender = seq[0].replace(':', '')
                    res = []

                    # If command is 'broadcast <message>'
                    if command == 'broadcast':
                        for i in range(len(seq)):
                            if i != 1:
                                res.append(seq[i])
                        sen = ' '
                        result = sen.join(res)
                        # print(sender)
                        # print(online.keys())
                        for u in online.keys():
                            if u != sender:
                                for r in users:
                                    if r.username == u:
                                        if sender not in r.black_list:
                                            online[u].send(result.encode())
                        con.release()
                        # conn.send(result.encode())
                        # con.release()

                    # If command is 'message <user> <message>'
                    elif command == 'message':
                        for i in range(len(seq)):
                            if (i != 1) and (i != 2):
                                res.append(seq[i])
                        sen = ' '
                        result = sen.join(res)
                        for u in users:
                            if u.username == seq[2]:
                                if sender in u.black_list:
                                    reply = 'You cannot send message to ' + seq[2]
                                    online[sender].send(reply.encode())
                                    break
                                else:
                                    online[seq[2]].send(result.encode())
                                    break
                        con.release()

                    # If command is 'whoelse'
                    elif command == 'whoelse':
                        for u in online.keys():
                            if u != sender:
                                online[sender].send(u.encode())
                        con.release()

                    # If command is 'whoelsesince <time>'
                    elif seq[1] == 'whoelsesicne':
                        current_time = time.time()
                        duration = int(seq[2])
                        for u in users:
                            if u.username != sender:
                                if (current_time - u.login_time) <= duration:
                                    online[sender].send(u.username.encode())
                        con.release()

                    # If command is 'logout'
                    elif command == 'logout':
                        online[sender].send(command.encode())
                        # Remove this user from online list
                        del online[sender]
                        # Broadcast the user logout message
                        message = sender + ' logout.'
                        for u in online.keys():
                            online[u].send(message.encode())
                        # Change the logout_time record
                        for u in users:
                            if u.username == sender:
                                u.logout_time = time.time()
                                break
                        con.release()

                    # If command is 'block <user>'
                    elif command == 'block':
                        if seq[2] != sender:
                            flag = 0
                            for u in users:
                                if u.username == sender:
                                    if seq[2] not in u.black_list:
                                        u.black_list.append(seq[2])
                                        flag += 1
                                        break
                            if flag != 1:
                                reply = 'Cannot find this user.'
                                online[sender].send(reply.encode())
                            else:
                                reply = 'You have blocked ' + seq[2]
                                online[sender].send(reply.encode())
                            con.release()
                        else:
                            reply = 'Cannot block yourself.'
                            online[sender].send(reply.encode())
                            con.release()

                    # If command is 'unblock <user>'
                    elif command == 'unblock':
                        if seq[2] != sender:
                            flag = 0
                            for u in users:
                                if u.username == sender:
                                    if seq[2] in u.black_list:
                                        u.black_list.remove(seq[2])
                                        flag += 1
                                        break
                            if flag != 1:
                                reply = 'You did not block this user.'
                                online[sender].send(reply.encode())
                            else:
                                reply = 'You have unblocked ' + seq[2]
                                online[sender].send(reply.encode())
                            con.release()
                        else:
                            reply = 'Cannot unblock yourself.'
                            online[sender].send(reply.encode())
                            con.release()

                    # If command is 'startprivate <user>'
                    elif command == 'startprivate':
                        # Check object is not sender itself
                        if seq[2] != sender:
                            for u in users:
                                if u.username == seq[2]:
                                    if (sender in u.black_list) or (u.username not in online.keys()):
                                        reply = 'You cannot stratprivate with this user'
                                        online[sender].send(reply.encode())
                                        con.release()
                                    else:
                                        # addr[0] is IP address
                                        # addr[1] is Port Number
                                        object_ip = u.addr[0]
                                        object_port = str(u.addr[1] + 1)
                                        for s in users:
                                            if s.username == sender:
                                                sender_ip = s.addr[0]
                                                sender_port = str(s.addr[1])
                                                break
                                        from_message = 'Accept ' + sender + ' ' + sender_ip + ' ' + sender_port + ' ' + object_port
                                        obj_message = 'Link ' + seq[2] + ' ' + object_ip + ' ' + object_port
                                        online[sender].send(obj_message.encode())
                                        online[seq[2]].send(from_message.encode())
                                        con.release()
                        else:
                            reply = 'You cannot startprivate with yourself'
                            online[sender].send(reply.encode())
                            con.release()
                    else:
                        conn.send(data.encode())
                        con.release()
                        return
                else:
                    del online[seq[0][7:]]
                    con.release()
                    return

                # except:
                #     con.release()
                #     return


def notify_all(string, con):
    """Use this function to change data and tell other lock to do operations"""
    global data
    # Acquire lock
    if con.acquire():
        data = string
        # Abandon current occupation of resource
        # Broadcast other thread to run after wait()
        con.notifyAll()
        # Release lock
        con.release()


def notify(string, con):
    """Use this function to change data and tell other lock to do operations"""
    global data
    # Acquire lock
    if con.acquire():
        data = string
        # Abandon current occupation of resource
        # Broadcast other thread to run after wait()
        con.notify()
        # Release lock
        con.release()


# Main Function ----------------------------------------------------------
data = ''   # Define a global data as received message/sending message


def main():
    """Main function"""

    # If condition satisfied, do some operations - LOCK
    con = threading.Condition()

    # Create a list to record all users
    users = []

    # Create a dictionary to record all online users
    online = {}

    # Create a list to record blocked users
    blocked = []

    # Transform login txt into a dictionary
    login = {}

    with open('credentials.txt', 'r') as file:
        for line in file:
            row = line.split()
            login[row[0]] = row[1]

    host = 'localhost'

    # Get parameters from command line
    port = int(sys.argv[1])
    time_block = int(sys.argv[2])
    time_out = int(sys.argv[3])

    # Create socket
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(10)
    print('Server is listening...')

    # Main loop - continuously server for multiple clients
    while True:

        # Accept client connection
        conn, addr = sock.accept()
        # addr[0] is IP address of client and addr[1] is the port number
        print('Server has connected with ' + addr[0] + ': ' + str(addr[1]))

        # Authentication
        a = 0
        while True:
            # Receive username & password from client input
            request = conn.recv(1024).decode()
            username = request.split()[0]
            password = request.split()[1]
            result = authentication(username, password, conn, addr, login, blocked, users, time_block, online)
            if result == 1:
                a = 1
                break
            elif result == 2:
                continue
            else:
                break

        if a == 1:
            # If authentication success, then implement other functions
            # Presence Broadcast
            string = 'Welcome ' + username + ' goes online.'
            notify_all(string, con)
            # print(data)
            # Show how many users online
            print(str((threading.activeCount() + 1) / 2) + ' user(s) online.')
            conn.send(data.encode())

            # Create threads for new clients
            # Different threads deal with different transactions
            thread_recv = threading.Thread(target=handle_recv, args=(conn, con, username, time_out))
            thread_send = threading.Thread(target=handle_send, args=(conn, con, online, users))
            thread_recv.start()
            thread_send.start()


if __name__ == "__main__":
    main()
