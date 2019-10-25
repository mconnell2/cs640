
'''
File:    myswitch_fifo.py
Authors: Matt Goheen (mgoheen@wisc.edu), Mark Connell (mconnell2@wisc.edu)
Class:   CS640 Fall 2019

Assignment 1 Part 1 - Ethernet learning switch in Python.
'''

from switchyard.lib.userlib import *

TIMEOUT= 30
BROADCAST = EthAddr('FF:FF:FF:FF:FF:FF')

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    myAddressTable = AddressTable()

	#attempt to continuously receive packets
    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return
 
        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

        #determine if packet is for this switch, broadcast, otherwise use/update forwarding table
        if packet[0].dst in mymacs:
            log_debug("Packet intended for me") 
        elif packet[0].dst == BROADCAST:
            broadcast(my_interfaces,packet,net,input_port)
        else:
            myAddressTable.updateTable(packet,input_port,timestamp)

            #if outgoing port found, send on that port, otherwise, broadcast
            out_port = myAddressTable.getPort(packet)
            if out_port is not None:
                log_debug("Sending packet {} to {}".format(packet,out_port))
                net.send_packet(out_port,packet)
            else:
                broadcast(my_interfaces,packet,net,input_port)  
        
    net.shutdown()


#broadcast will forward packets on all ports except for input port
def broadcast(interfaces,packet,net,input_port):
    for intf in interfaces:
        if input_port != intf.name:
            log_debug ("Flooding packet {} to {}".format(packet, intf.name))
            net.send_packet(intf.name, packet) 


#AddressTable objects will store a list of AddressNode objects to support forwarding tables
class AddressTable:
    def __init__(self):
        self.tableEntries = list()

    def getPort(self, packet):
        for tableEntry in self.tableEntries:
            if tableEntry.address==packet[0].dst and not tableEntry.isExpired():  #note, isExpired not implemented
                return tableEntry.port

    #not implemented for Part 1 learning switch
    def dropStale(self):        
        for tableEntry in self.tableEntries:
            if tableEntry.isExpired():
                self.tableEntries.remove(tableEntry)

    def updateTable(self,packet,input_port,timestamp):

        #if the packet src addr is in the table, update port and timestamp and return
        for tableEntry in self.tableEntries:
            if packet[0].src == tableEntry.address:
                tableEntry.port = input_port
                tableEntry.timestamp = timestamp
                return

        #if the packet source address is not in the table, add it  
        self.tableEntries.append(AddressNode(packet,input_port,timestamp))

        #FIFO policy - remove first added entry (don't have to search list for oldest timestamp)
        if len(self.tableEntries) > 5:
            self.tableEntries.pop(0)
        self.dropStale()
    

#AddressNode objects will store addr, port, and timestamp to support forwarding tables
class AddressNode:
    def __init__(self,packet,input_port,timestamp):
        self.port = input_port
        self.address = packet[0].src
        self.timestamp = timestamp
        self.next = None

    def isExpired(self):
        #not implemented for Part 1 simple learning switch
        return
