import argparse
from http import client
import socket
import subprocess
import sys
import threading

command = False
execute = ""
output_destination = ""
verbose = False


def run_command(cmd: str) -> str:
    """ 
    Run the specified command in the host OS.
    :param cmd: command to run
    :return: output from command
    """
    cmd = cmd.strip()
    try:
        # run command and return received output
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except Exception as e:
        print(e)
        print(f'Failed to execute command: {cmd}')
        return 'Failed to execute command: {}\r\n'.format(cmd).encode()
    return output


def handle_client_connection(client_socket: socket.socket, client_address):
    """
    Handle requests from a connected client.
    :param client_socket: connected client object
    :param client_address: address of connected client
    :return: None
    """
    global output_destination
    global execute
    global command

    print(f'Connected to client at {client_address}')
    # check if we are supposed to write client input to a file
    if output_desination:
        file_input = ""
        print(f'Writing intput from a client at {client_address} to {output_destination}.')
        # keep reading data until none is left
        with open(output_destination, 'w') as of:
            while True:
                data = client_socket.recv(1024)
                if not data or data.decode() == '\r\n' or data.decode() == '\n':
                    break
            # write data to file
            of.write(data.decode())
        client_socket.send('Successfully saved file to {}.\r\n'.format(output_destination).encode())
        # check if execute command
        if execute:
            output = run_command(execute)
            client_socket.send(output)
        # check if command shell requested
        if command:
            while True:
                client_socket.send('terminal>'.encode())
                # receive data until LF
                cmd_buffer = ''
                while '\n' not in cmd_buffer:
                    cmd_buffer += client_socket.recv(1024).decode()
                # run comand and send output back to client
                if cmd_buffer.strip() == 'exit':
                    client_socket.send('Exit code received, closing terminal.\r\n'.encode())
                    break
                output = run_command(cmd_buffer)
                client_socket.send(output)
        client_socket.close()

    
def start_server(listen_host: str, listen_port: int):
    """
    Start listening on the specified host and port.
    :param listen_host: IP address to listen on (0.0.0.0 to listen on all interfaces)
    :param listen_port: Port to listen to
    :return:
    """
    # Start listening
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((listen_host, listen_port))
    server.listen()

    # wait for inbound connections
    while True:
        client_socket, addr = server.accept()
        # start new thread to handle this connection
        client_thread = threading.Thread(target=handle_client_connection, args=(client_socket, addr))
        client_thread.start()


def client_send(target_host: str, target_port: int, data=None):
    """
    Connect as a client to the specified target and send and receive arbitrary data.
    :param target_host: host to connect to
    :param target_port: port to connect to
    :param data: initial data to send
    :return: None
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # connect to target host
    try:
        client.connect((target_host, target_port))
        if data:
            client.send(data.decode())
        while True:
            # wait for response from target host
            recv_len = 1
            response = ''
            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data.decode()
                if recv_len < 4096:
                    break
            print(response)
            # get further input from user
            print('Enter further input or press CTRL-D for no input.')
            data = sys.stdin.read()
            if not data:
                data = ''
            data += '\n'
            client.send(data.encode())
    except Exception as e:
        print(e)
        print('[*] Exiting program.')
        client.close()


def print_verbose(message: str):
    """
    Print the specified message to STDOUT only if the verbose flag is set to True (default is False)
    :param message: message to print
    :return: None
    """
    global verbose
    if verbose:
        print(message)
    

def main():
    """
    Main logic.
    :return: None
    """
    # define global variables
    global command
    global execute
    global output_destination
    global verbose

    # parse command line arguments
    parser = argparse.ArgumentParser(
        description = 'A pure python replacement for Netcat (sort of) that also adds several new features.')
    parser.add_argument('-l', '--listen', action='store_true', help='Listen for incoming connetions')
    parser.add_argument('-e', '--execute', help='Execute the given command after receiving a connection')
    parser.add_argument('-c', '--command', action='store_true', help='Initialize a command shell')
    parser.add_argument('-o', '--outfile', help='Write inptu data to the given file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose messages')
    parser.add_argument('target_host', help='IP or hostname to connet to or listen on')
    parser.add_argument('port', type=int, help='')
    args = parser.parse_args()

    # assign input arguments
    listen = args.listen
    execute = args.execute
    command = args.command
    output_destiation = args.outfile
    verbose = args.verbose
    target_host = args.target_host
    port = int(args.port)

    if listen:
        print_verbose(f'Listening for incoming connections on TCP {target_host}:{port}')
        start_server(target_host, port)
    else:
        print_verbose(f'Connecting to TCP {target_host}:{port}. Enter input or press CTRL-D for no input.')
        # get data from STIN if provided
        data = sys.stdin.read()
        # connect to server
        client_send(target_host, port, data)

if __name__ == '__main__':
    main()