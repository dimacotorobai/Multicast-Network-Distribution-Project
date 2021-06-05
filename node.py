import copy
import os
import socket
import sys
import time

#from _thread import *
from threading import Thread
from config import *


#Defined a lambda function to clear the screen
clear = lambda: os.system('cls')

#define A Receiver Thread
def recv_thread(connection, node_list, server_list, id):
    try:
        while True:
            #Set socket timeout for inactive sockets
            connection.settimeout(30.0)
            data = connection.recv(1024)
            #print(data)
            data = eval(data.decode('utf-8'))

            print('Received: ', data)
            if data[0] == id:
                print("Message: ", data[1])
                print('')
            else:
                print('Forwarding: ', data)
                for element in node_list:
                    if data[0] == element[0]:
                        print('Found: ',data, ", ", element)
                        data[2] = element[3]
                
                #print('New Data: ', data)

                for msg_sock in server_list:
                    if data[2] == msg_sock[1]:
                        #print("Found Socket")
                        print('Sending: ', data)
                        print('')
                        send = str(data).encode()
                        msg_sock[0].send(send)
                        #time.sleep(2.0)
            #Sleep Thread
            #time.sleep()
    except:
        print("Socket Timeout")
        #print("Closed: ", connection)
        connection.close()

    




#Node Class
class Node:
    def __init__(self, config):
        #Extract Config File
        self.type = config[0]
        self.id = config[1]
        self.local_port = config[2]
        self.s_ports = config[3]
        self.c_ports = config[4]
        self.c_costs = config[5]
    
    def print(self):
        #Print the Node Information
        print('Node Type: ', self.type)
        print('Node Id: ', self.id)
        print('Node Local Port: ', self.local_port)
        print('Node Server Ports: ', self.s_ports)
        print('Node Client Ports: ', self.c_ports)
        print('Node Client Costs: ', self.c_costs)

    def server_init(self):
        #Initialize Socket
        self.mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #Socket w/ IPv4 & TCP
        self.host = '127.0.0.1'                                             #Loopback Address
        self.mysocket.bind((self.host, self.local_port))                    #Bind Address and Port to Socket
        self.mysocket.listen(5)                                             #List to Incoming Connections

        #Create A List of Sockets
        self.server_list = []
        for port in self.s_ports:
            s_new = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s_new.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s_new.bind((self.host, port + self.id*10 + 100*0))              #Id defines the client ports // self.id defines ten ports per node // 100*x used to switch ports bc rapid relaunch might have open ports
            self.server_list.append([s_new, 0])                                  #Append the new socket to the list                                

    def server_connect(self):
        if self.type == 'S':
            #Empty List Just for Consistensy with others
            self.client_list = []

            #Connect to all Server Ports
            for i in range(len(self.server_list)):                          
                self.server_list[i][0].connect((self.host, self.s_ports[i]))   #Source Connects to All Servers
                self.server_list[i][0].send(str(self.id).encode())
                msg = self.server_list[i][0].recv(1024)
                msg = msg.decode('utf-8')
                self.server_list[i][1] = eval(msg)

        else:
            #Accept all Client Connections
            self.client_list = []                                           #Create an empty Client List
            for client in self.c_ports:
                c, addr = self.mysocket.accept()                            #Accept Clients
                node_id = c.recv(1024)
                node_id = node_id.decode('utf-8')
                self.client_list.append([c, addr, eval(node_id)])                 #Append Clients to Client List
                c.send(str(self.id).encode())
                print('Connected From: ', addr)

            #Connect to all Server Ports
            for i in range(len(self.s_ports)):
                self.server_list[i][0].connect((self.host, self.s_ports[i]))   #Connect to the Servers in Server List
                self.server_list[i][0].send(str(self.id).encode())
                msg = self.server_list[i][0].recv(1024)
                msg = msg.decode('utf-8')
                self.server_list[i][1] = eval(msg)

        print('Connections Done !!!\n\n')

    def create_tree(self):
        #Non Last Node
        if len(self.s_ports) != 0:
            print('Waiting for Node Costs')
            list_len = len(self.s_ports)
            self.node_list = []

            #Receive the Node List from Server
            for i in range(list_len - 1, -1, -1):
                msg = self.server_list[i][0].recv(1024)
                msg = msg.decode('utf-8')
                if self.type != 'R':
                    data = eval(msg)
                    #Append Received Node List to Local Node List
                    for d in data:
                        found = 0
                        for k in self.node_list:
                            if d[0] == k[0]:
                                found = 1
                                if d[2] < k[2]:
                                    index = self.node_list.index(k)
                                    k = d.copy()
                                    self.node_list[index] = k

                        if found == 0:
                            self.node_list.append(d)

            self.node_list.append([self.id, self.local_port, 0, 0])


            if self.type == 'F':
                #print('Sending Info')

                #Number of Clients
                list_len = len(self.c_costs)    

                #Print Table    
                #print('Table: ', self.node_list)

                for i in range(list_len - 1, -1, -1):
                    #Set Hop and Cost
                    list_sent = copy.deepcopy(self.node_list)   #Copy all layers of list into new list so its not a reference
                    #print("Table Before Send: ", list_sent)

                    #Determine Link Cost
                    node_id = self.client_list[i][2]
                    true_cost = 0
                    for cost in self.c_costs:
                        if node_id == cost[0]:
                            true_cost = cost[1]
                            break

                    #Update Table Entries for each link
                    for data in list_sent:
                        data[2] = data[2] + true_cost
                        data[3] = self.id

                    #print('Address: ', self.client_list[i][1])
                    #print('List Sent: ', list_sent)
                    #print('')

                    #List - String, and Send
                    msg = str(list_sent)
                    msg = msg.encode()
                    self.client_list[i][0].send(msg)
            
            elif self.type == 'R':
                #Number of Clients
                list_len = len(self.c_costs)    

                #Print Table    
                #print('Table: ', self.node_list)

                for i in range(list_len - 1, -1, -1):
                    #Set Hop and Cost
                    list_sent = copy.deepcopy(self.node_list)   #Copy all layers of list into new list so its not a reference
                    #print("Table Before Send: ", list_sent)

                    #Determine Link Cost
                    node_id = self.client_list[i][2]
                    true_cost = 0
                    for cost in self.c_costs:
                        if node_id == cost[0]:
                            true_cost = cost[1]
                            break

                    #Update Table Entries for each link
                    for data in list_sent:
                        data[2] = data[2] + true_cost
                        data[3] = self.id

                    #print('Address: ', self.client_list[i][1])
                    #print('List Sent: ', list_sent)
                    #print('')

                    #List - String, and Send
                    msg = str(list_sent)
                    msg = msg.encode()
                    self.client_list[i][0].send(msg)
        
        #Last Node    
        else:
            #Create Table Entry of Last Node
            list_len = len(self.c_costs)
            self.node_list = []
            add = [self.id, self.local_port, 0, 0]
            self.node_list.append(add)

            #Print Table of Entries
            #print('Table: ', self.node_list)

            #Set Next Node and Add Cost to the Hop
            for i in range(list_len - 1, -1, -1):
                #Set Hop and Cost
                list_sent = copy.deepcopy(self.node_list)   #Copy all layers of list into new list so its not a reference
                #print("Table Before Send: ", list_sent)
                
                #Determine Link Cost
                node_id = self.client_list[i][2]
                true_cost = 0
                for cost in self.c_costs:
                    if node_id == cost[0]:
                        true_cost = cost[1]
                        break


                #Update Table Entries for each link
                for data in list_sent:
                    data[2] = data[2] + true_cost
                    data[3] = self.id

                #print('Address: ', self.client_list[i][1])
                #print('List Sent: ', list_sent)
                #print('')

                #List - String, and Send
                msg = str(list_sent)
                msg = msg.encode()
                self.client_list[i][0].send(msg)


    def running(self):
        try:
            if self.type == 'S':
                print('Running')

                while True:
                    #Take Message
                    message = input("Input a message: ")

                    #Make Message Queue
                    msg_queue = []
                    for node in self.node_list:
                        msg_queue.append([node[0], message, node[3]])

                    #Send Message Queue to appropriate sockets

                    for msg in msg_queue:
                        for msg_sock in self.server_list:
                            if msg[2] == msg_sock[1]:
                                print("Found Socket")
                                print('Sending: ', msg)
                                send = str(msg).encode()
                                msg_sock[0].send(send)
                                time.sleep(0.5)

                    print('All Messages Sent')
            else:
                #Create Receiver Threads
                threads = []
                for client in self.client_list:
                    #print("Creating Thread for ", self.id, " Thread:", client[2])
                    t = Thread(target = recv_thread, args = (client[0], self.node_list, self.server_list, self.id))
                    t.start()
                    threads.append(t)

                #wait for threads to join
                for t in threads:
                    t.join()
        except:
            print('All Sockets Disconnected')


    def print2(self):
        print('Info')
        for info in self.client_list:
            print("Address: ", info[1])
            print('Node: ', info[2])

    def show_table(self):
        print('TABLE')
        for entry in self.node_list:
            print(entry)

        print('\n')

    def node_disconnect(self):
        for server in self.server_list:
            server[0].close()


        
#Main Function
def main():
    #Clear Window
    clear()

    #Select a Config File
    if sys.argv[1] == 'A':
        config = ConfigA
    elif sys.argv[1] == 'B':
        config = ConfigB
    elif sys.argv[1] == 'C':
        config = ConfigC
    elif sys.argv[1] == 'D':
        config = CondigD
    elif sys.argv[1] == 'E':
        config = CondigE
    elif sys.argv[1] == 'F':
        config = CondigF
    elif sys.argv[1] == 'G':
        config = CondigG
    else:
        exit()
    
    #Create Node
    N1 = Node(config=config)
    #N1.print()
    N1.server_init()
    N1.server_connect()
    #N1.print2()
    N1.create_tree()
    N1.show_table()
    N1.running()
    N1.node_disconnect()

#Module Start if it is run directly
if __name__ == '__main__':
    main()