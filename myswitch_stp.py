
'''
File:    myswitch_fifo.py
Authors: Matt Goheen (mgoheen@wisc.edu), Mark Connell (mconnell2@wisc.edu)
Class:   CS640 Fall 2019

Assignment 1 Part 2 - Ethernet learning switch with Spanning Tree implementation
'''

from switchyard.lib.userlib import *
from SpanningTreeMessage import *
import time
import sys


STPBROADCASTTIME = 2.0
TIMEOUT= 10.0
BROADCAST = EthAddr('FF:FF:FF:FF:FF:FF')


def main(net):
    timeKeeper = TimeKeeper()
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    myAddressTable = AddressTable()
    myId = min(mymacs)
    rootInfoTable = RootInfoTable(myId)

    #startup behavior - broadcast STP packets
    packet = createSTP(myId)
    broadcast(my_interfaces,packet,net, None)
    timeKeeper.updateLastSTPBroadcast()

    #attempt to continuously receive packets
    while True:
        
        #if current node is NOT root node and 10+ seconds since last received STP packet, assign node to root
        if not isStillRoot(timeKeeper,myId,rootInfoTable) and timeKeeper.timeSinceLastSTPReceived() > TIMEOUT:
            log_debug(" *** Timeout - update root node to this node.")
            rootInfoTable = RootInfoTable(myId)

        #if current node is root node and 2+ seconds since last sending STP packets, send now, update timer
        if isStillRoot(timeKeeper,myId,rootInfoTable) and timeKeeper.timeSinceLastSTPBroadcast() >= STPBROADCASTTIME:
            log_debug(" *** Current node is root node - send packets every 2 seconds.")            
            packet = createSTP(myId)
            broadcast(my_interfaces,packet,net, None)
            timeKeeper.updateLastSTPBroadcast()

        #receive 
        try:
            timeKeeper.timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            log_debug(" **** No Packets received.")
            continue
        except Shutdown:
            return

        #Logic for STP packets
        #If STP, update info, update header, update timer send on its way        
        if isSTPPacket(packet):
            log_debug("In {} received STP packet {} on {}".format(net.name, packet, input_port))
            timeKeeper.updateLastSTPReceived()
            processSTPPacket(packet,input_port,rootInfoTable,myId,my_interfaces,net) #update root information, blocklist
            log_debug(" *** STP table info updated.")
            continue

        #Logic for non-STP packets
        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))
        if packet[0].dst in mymacs: #If addressed to me, do nothing
            log_debug("Packet intended for me") 
        elif packet[0].dst == BROADCAST: #If Broadcast, broadcast
            #broadcast(my_interfaces,packet,net,input_port)
            updateAndForwardPacket(my_interfaces,myId,packet,net,rootInfoTable,input_port) #flood out if we don't know where to go
        else:
            myAddressTable.updateTable(packet,input_port,timeKeeper.timestamp) #update forwarding table
            out_port = myAddressTable.getPort(packet) #check table for address
            if out_port is not None: 
                
                log_debug("Sending packet {} to {}".format(packet,out_port))
                net.send_packet(out_port,packet) #don't need to flood out if we know where we're going
                
            else:
                log_debug(" *** Address not known, flood out non-STP packet.")
                updateAndForwardPacket(my_interfaces,myId,packet,net,rootInfoTable,input_port) #flood out if we don't know where to go

    net.shutdown()

#TODO remove this? same as below.
def broadcast(interfaces,packet,net,input_port):   
    log_debug(" *** Broadcast invoked.")
    for intf in interfaces:
        if input_port != intf.name:
            log_debug ("Flooding packet {} to {}".format(packet, intf.name))
            net.send_packet(intf.name, packet) 


#updateAndForwardPacket will update STP packets and forward both STP and non-STP packets
def updateAndForwardPacket(interfaces,myId,packet,net,rootInfoTable,input_port):

    #if STP packet, update STP packet header
    if isSTPPacket(packet):
        stpIndex = packet.get_header_index(SpanningTreeMessage)
        current_hops= packet[stpIndex].hops_to_root
        packet[stpIndex].hops_to_root = current_hops + 1
        packet[stpIndex].switch_id = myId
        #packet[stpIndex].root = myId
        log_debug(" *** STP header updated. Flooding STP packets.")

        #flood STP packets on all interfaces other than input port
        for intf in interfaces:
            if input_port != intf.name:
                log_debug ("Flooding packet {} to {}".format(packet, intf.name))
                net.send_packet(intf.name, packet)
        return

    else:
        #floot non-STP packets on all interfaces that aren't blocked and aren't input port
        log_debug(" *** Flooding non-STP packets. Current block list: {} and input port {}".format(rootInfoTable.blockedPorts, input_port))
        for intf in interfaces:
            log_debug ("Flooding packet - checking {}.".format(intf.name))
            if (intf.name not in rootInfoTable.blockedPorts) and (input_port != intf.name):
                log_debug ("Flooding packet {} to {}".format(packet, intf.name))
                net.send_packet(intf.name, packet) 
    return

#isStillRoot determines if current switch is root node
def isStillRoot(timeKeeper,myId,rootInfoTable):
    if rootInfoTable.rootSwitchId == myId: return True
    return False    

def isSTPPacket(packet):
    if packet.has_header(SpanningTreeMessage): return True
    return False

#createSTP will create a STP packet
def createSTP(myId):
    packet = Packet()
    packet += Ethernet()
    packet[0].src = myId
    packet[0].dst = BROADCAST
    packet[0].ethertype = 0x8809  #SLOW
    packet += SpanningTreeMessage(root_id=myId, switch_id=myId)
    return packet

#processSTPPacket does the bulk of processing - determining when to update root information, blocked ports, and forwarding packets
def processSTPPacket(packet,input_port,rootInfoTable,myId,my_interfaces,net):

    #locate STP message in the packet and gather information
    stpIndex = packet.get_header_index(SpanningTreeMessage)
    packetRoot = packet[stpIndex].root
    packetHops = packet[stpIndex].hops_to_root
    log_debug(" *** Process STP Packet with root: {}, hops to root: {}, vs switch known root: {}.".format(packetRoot, packetHops, rootInfoTable.rootSwitchId))
  
    #found packet with root node, update root information and forward
    if input_port == rootInfoTable.rootInterface or packetRoot < rootInfoTable.rootSwitchId:
        log_debug(" *** Packet on root port or packet root has lower ID. Update root information, and forward.")
        rootInfoTable.hopsFromRoot = packetHops
        rootInfoTable.rootSwitchId = packetRoot
        rootInfoTable.rootInterface = input_port
        updateAndForwardPacket(my_interfaces,myId,packet,net,rootInfoTable,input_port)

    #else if packet root is higher than known root, remove port from blocking list
    elif packetRoot > rootInfoTable.rootSwitchId:
        log_debug(" *** Packet has non-root node. Remove port from blocking list.")
        rootInfoTable.removeFromBlocklist(input_port)

    #elise if packet root is same as known root, further processing
    elif packetRoot == rootInfoTable.rootSwitchId:        
        log_debug(" *** Packet has same root node is same as known root. Enter Same Root protocol.")

        #if packet hops to root is smaller, or, packet hops to root is same and switch ID is lower, do updates
        tempHops = packetHops + 1        
        if tempHops < rootInfoTable.hopsFromRoot or (tempHops==rootInfoTable.hopsFromRoot and rootInfoTable.rootSwitchId > packet[stpIndex].switch_id()):
            log_debug(" *** Same Root protocol. Update root info and forward.")        
            rootInfoTable.removeFromBlocklist(input_port)
            rootInfoTable.addToBlocklist(rootInfoTable.rootInterface)
            rootInfoTable.rootInterface = input_port
            rootInfoTable.hopsFromRoot = packetHops
            updateAndForwardPacket(my_interfaces,myId,packet,net,rootInfoTable,input_port)
        else:
            log_debug(" *** Same Hop protocol. Don't update root, block this port: {}".format(input_port))
            rootInfoTable.addToBlocklist(input_port)


#AddressTable objects will store a list of AddressNode objects to support forwarding tables
class AddressTable:
    def __init__(self):
        self.tableEntries = list()

    def getPort(self, packet):
        for tableEntry in self.tableEntries:
            if tableEntry.address==packet[0].dst and not tableEntry.isExpired():  #note, expired entries is not part of current implementation
                return tableEntry.port

    #TODO remove this and expired stuff?
    def dropStale(self):
        for tableEntry in self.tableEntries:
            if tableEntry.isExpired():  #note, expired entries is not part of current implementation
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
        #expired addresses is not part of current implementation
        return


#RootInfoTable object will store information about the root node in the network
class RootInfoTable:
    def __init__(self,myId):
        self._rootInterface = None
        self._rootSwitchId = myId
        self.blockedPorts = list()  #blocked ports used for normal (non-STP) packets
        self._hopsFromRoot = 0
    
    def removeFromBlocklist(self, port):
        if self.blockedPorts.count(port) > 0:
            self.blockedPorts.remove(port)
            log_debug(" *** Removed {} to block list.".format(port))

    def addToBlocklist(self, port):
        if self.blockedPorts.count(port) == 0:
            self.blockedPorts.append(port)
            log_debug(" *** Added {} to block list.".format(port))

    @property
    def hopsFromRoot(self):
        return self._hopsFromRoot

    @hopsFromRoot.setter
    def hopsFromRoot(self, value):
        self._hopsFromRoot = int(value)

    @property
    def rootSwitchId(self):
        return self._rootSwitchId

    @rootSwitchId.setter
    def rootSwitchId(self, value):
        self._rootSwitchId = value

    @property
    def rootInterface(self):
        return self._rootInterface

    @rootInterface.setter
    def rootInterface(self, value):
        self._rootInterface = value


#TimeKeeper ojbects will track last broadcast and received times and calculate the time since those events
class TimeKeeper:
    def __init__(self):        
        self.lastSTPBroadcast = time.perf_counter()
        self.lastSTPReceived = time.perf_counter()
    
    def timeSinceLastSTPBroadcast(self):
        return time.perf_counter() - self.lastSTPBroadcast

    def updateLastSTPBroadcast(self):
        self.lastSTPBroadcast = time.perf_counter()
    
    def timeSinceLastSTPReceived(self):
        return time.perf_counter() - self.lastSTPReceived

    def updateLastSTPReceived(self):
        self.lastSTPReceived = time.perf_counter()
