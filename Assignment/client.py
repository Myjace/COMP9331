"""Client side"""
from socket import *
import threading
import sys

# Functions --------------------------------------------------------------
private = []
name_to_address = {}


def private_server(local_port):
    """Create a new socket to serve as a private server"""
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind(('localhost', local_port))
    sock.listen(5)

    active = True
    flag = 0

    while active:
        conn, addr = sock.accept()
        private_message = conn.recv(1024).decode()
        if private_message.split()[0] == 'stopprivate':
            flag = 1
            active = False
        print(private_message)

    if flag == 1:
        sock.close()


def private_send(out_string, username):
    """Send private message to another client"""
    seq = out_string.split()
    user = seq[1]
    command = seq[0]
    if user in private:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect(name_to_address[user])
        if command == 'private':
            message = username + '(private): '
            for i in range(2, len(seq)):
                message += seq[i] + ' '
            sock.send(message.encode())
            reply = sock.recv(1024).decode()
            print(reply)
        elif command == 'stopprivate':
            messgae = username + ' want to stop private connection with you'
            sock.send(messgae.encode())
            sock.close()
            private.remove(user)
    else:
        print('You have not established private connection with this user.')


def handle_recv(sock):
    """ Target function which to handle 'receiving transactions' """
    global in_string
    while True:
        in_string = sock.recv(1024).decode()
        if not in_string:
            break
        if in_string != out_string:
            if (in_string == 'timeout') or (in_string == 'logout'):
                # If reply is 'timeout' or 'logout', close current socket and shut down
                sock.close()
                sys.exit()
            """
                If the header of reply is addr, 
                it means that sever return the IP address and Port number
            """
            if in_string.split()[0] == 'Accept':
                # Process the reply message
                sender = in_string.split()[1]
                sender_ip = in_string.split()[2]
                sender_port = int(in_string.split()[3])
                local_port = int(in_string.split()[4])
                name_to_address[sender] = (sender_ip, sender_port)

                # Start a new thread to serve as a private recv server
                thread_private = threading.Thread(target=private_server, args=(local_port,))
                thread_private.setDaemon(True)
                thread_private.start()

            elif in_string.split()[0] == 'Link':
                # Process the reply message
                object = in_string.split()[1]
                object_ip = in_string.split()[2]
                object_port = int(in_string.split()[3])
                name_to_address[object] = (object_ip, object_port)
                private.append(object)

            # Create a new thread to communicate with
            print(in_string)


def handle_send(sock, commands, username):
    """ Target function which to handle 'sending transactions' """
    global out_string
    while True:
        out_string = input()
        try:
            """Use error detection to avoid empty input"""
            if out_string.split()[0] not in commands:
                print('Error. Invalid command')
            elif (out_string.split()[0] == 'private') or (out_string.split()[0] == 'stopprivate'):
                thread_p_send = threading.Thread(target=private_send, args=(out_string, username))
                thread_p_send.start()
            else:
                out_string = username + ': ' + out_string
                sock.send(out_string.encode())
        except:
            """Empty input is also invalid command"""
            print('Error. Invalid command')


# Main Function ----------------------------------------------------------

"""Define 2 global strings as received message and sending message"""
in_string = ''
out_string = ''


def main():
    """Main function"""

    # Create a command list to store all possible commands
    commands = ['message', 'broadcast', 'whoelse', 'whoelsesince', 'block', 'unblock', 'logout', 'startprivate', 'private', 'stopprivate']

    # Get parameters from command line
    host = sys.argv[1]
    port = int(sys.argv[2])

    # Create socket
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((host, port))

    # Authentications
    while True:
        # Input Username and Password
        username = input('Username: ')
        password = input('Password: ')

        message = username + ' ' + password

        # Send Username and Password to server to check login
        sock.send(message.encode())

        while True:
            # Receive reply from server
            reply = sock.recv(1024).decode()
            print(reply)

            # If server reply a message with 'Welcome' head, login success - run rest program
            if reply.split()[0] == 'Welcome':
                e_type = 1
                break
            # Else if reply is 'No such account'
            elif reply.split()[0] == 'No':
                e_type = 2
                break
            # Else if reply is 'Your account is blocked', shut down program
            elif reply.split()[0] == 'Your':
                sys.exit()
            elif reply.split()[0] == 'Already':
                sys.exit()
            elif reply.split()[2] == 'Your':
                sys.exit()
            # Else login fail, re-input password
            else:
                password = input('Password: ')
                sock.send(password.encode())
        if e_type == 1:
            break
        else:
            continue

    # Create thread for current client
    thread_recv = threading.Thread(target=handle_recv, args=(sock,))
    thread_send = threading.Thread(target=handle_send, args=(sock, commands, username))
    # thread_recv.setDaemon(True)
    thread_send.setDaemon(True)
    thread_recv.start()
    thread_send.start()


if __name__ == "__main__":
    main()