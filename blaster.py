#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from random import randint
import time


def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    #parse blaster_params.txt file to determine blaster behavior; assume file structure and location
    file = open("blaster_params.txt", "r")
    firstLine = f.readline()
    splitLine = firstLine.split()  #default is whitespace
    
    #parse out lines in the file #TODO - do I need to validate these
    if splitLine[0] == "-b": blastee_IP = splitLine[1]
    if splitLine[2] == "-n": num = splitLine[3]
    if splitLine[4] == "-l": length = splitLine[5]
    if splitLine[6] == "-w": sender_window = splitLine[7]
    if splitLine[8] == "-rtt": RTT = splitLine[9]
    if splitLine[10] == "-r": recv_timeout = splitLine[11]
    if splitLine[12] == "-alpha": alpha = splitLine[13]
    
    #initialize estRTT and t_out with values from file
    estRTT = RTT
    t_out = 2 * estRTT

    #initialize sender window table for tracking SW and unACKd packets
    swTable = SendingWindowTable
    
    #stay in loop while blaster agent is running    
    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet(timeout=recv_timeout)  #TODO changed timeout here to value from file, OK?
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet")
            
            #TODO receive and parse an ACK package (check seq number? check first 8 bytes?)
            packet_sequence_number = 1 #TODO set to actual value
            
            #if we already ACK this packet, ignore this packet and continue
            if swTable.packetEntryIndexNumber(packet_sequence_number) == -1: continue
            
            #ACK for unACKed packet - retrieve the RTT for the packet and then remove from the table
            packet_rtt = time.perf_counter() - swTable.sentTimeForPacket(packet_sequence_number)
            swTable.removeFromPacketList(packet, packet_sequence_number)
                
            #ACK for unACKed packet - do estRTT and timeout calculations
            estRTT = ((1-alpha)* estRTT) + (alpha * (packet_rtt))
            t_out = 2 * estRTT
            if (rtt < min_rtt) or (min_rtt is None): min_rtt = rtt
            if (rtt > max_rtt) or (max_rtt is None): max_rtt = rtt
                        
            #if final ACK - do final calculations and print out stats to screen
            total_time = time.perf_counter() - first_packet_start_time
            throughput = (goodput_Bytes + reTx_Bytes) / total_time
            goodput = goodput_Bytes / total_time
            print_output(total_time, num_ret, num_tos, throughput, goodput, estRTT, t_out, min_rtt, max_rtt)
            
            
        else:
            log_debug("Didn't receive anything")
            
            #TODO - this is a coarse timeout? not sure! Maybe only count if first_packet_start_time is not None?
            #num_tos += 1
            
            log_debug("Check if sending window allows sending another packet.")
            #check SW C1: RHS - LHS <= SW to  and determine if a packet can be sent now
            if swTable.canSendAnotherPacket == TRUE: 

                #TODO this means we can send a new packet!
                #check if we have more new packets to send
                #send new packet

                #if this is the first packet sent, start tx counter
                if first_packet_start_time is None: first_packet_start_time = time.perf_counter()

                #if this is a first transmission of this packet
                #track number of bytes being sent:
                #goodput_Bytes is size of packet

                #add to unACKd packets table which also increments RHS
                swTable.addToPacketList(pkt, pkt_sequence_number)

                #then continue.

            log_debug("Cannot send new packet, or done sending new packets. Check if we can retransmit.")

            packetToRetransmitIndex = swTable.timedOutPacketIndex
            if packetToRetransmitIndex >=0:

                log_debug("We have a timed out packet. Attempt retransmit.")
                #increment count by one
                #num_ret += 1
                #reTx_Bytes  #TODO I should have a method to retrieve bytes from a packet

                #do I need to build anything? or just grab packet from tablet and resubmit? Simple enough.
                packetToRetransmit = swTable.sent_packets_list(index).packet  #TODO need getter?


            '''
            Creating the headers for the packet
            '''
            #TODO - do I need addresses?
            pkt = Ethernet() + IPv4() + UDP()
            pkt[1].protocol = IPProtocol.UDP
            
            #append sequence number (32 bits), length (16 bits), and payload (variable length)

            
            '''
            Do other things here and send packet
            '''

    net.shutdown()

#print_output prints transmission statistics
def print_output(total_time, num_ret, num_tos, throughput, goodput, estRTT, t_out, min_rtt, max_rtt):
    print("Total TX time (s): " + str(total_time))
    print("Number of reTX: " + str(num_ret))
    print("Number of coarse TOs: " + str(num_tos))
    print("Throughput (Bps): " + str(throughput))
    print("Goodput (Bps): " + str(goodput))
    print("Final estRTT(ms): " + str(estRTT))
    print("Final TO(ms): " + str(TO))
    print("Min RTT(ms):" + str(min_rtt))
    print("Max RTT(ms):" + str(max_rtt))
        
        
#sentPacketEntry objects will store info about packets that are in the sender window awaiting ACK
#TODO Double check whether this is byte oriented.
class sentPacketEntry:
    def __init__(self, packet, packet_sequence_number):
        self.packet = packet
        self.packet_sequence_number = packet_sequence_number
        self.time_sent = time.perf_counter()
        #TODO should we just parse the packet_sequence_number from the packet? or unncessarily complicated?

#SendingWindowTable will track unACKd packets and provide sending window calculations
class SendingWindowTable:
    def __init__(self,sending_window):
        self.sent_packets_list = list
        SW = sending_window  #count
        LHS = 1
        RHS = 1

    #called after packet is sent - will add packet if necessary (first time) and time stamp
    #TODO do I need both packet and sequence number? Or pull out sequence number from packet?
    def addToPacketList(self, packet, packet_sequence_number):
        
        #if packet isn't already in table, create sentPacket object, add to table with time, increment RHS
        if self.packetEntryIndexNumber(packet_sequence_number) == -1:
            self.sent_packets_list.append(sentPacketEntry(packet, packet_sequence_number))
            RHS += 1
           
    #removeFromPacketList when we receive an ACK - remove from table and update LHS
    #TODO do I need both packet and sequence number? Or pull out sequence number from packet?
    #TODO should I remove packet? do we need to validate bytes in packet, or just seq no?
    def removeFromPacketList(self, packet, packet_sequence_number):
        
        #if packet is in table, remove it and update LHS
        index = self.packetEntryIndexNumber(packet_sequence_number)
        if index >= 0:
             self.sent_packets_list.remove(index)
             self.recalculateLHS(self)

    #packetEntryIndexNumber returns -1 if packet is not in table, otherwise returns index position
    def packetEntryIndexNumber(self, packet_sequence_number):

        for packetEntry in sent_packets_list:
            if packetEntry.packet_sequence_number == packet_sequence_number:
                return sent_packets_list.index(packetEntry)
        
        return -1

    #returns time a packet was sent; use for calculating RTT
    def sentTimeForPacket(self, packet_sequence_number):
        
        #find packet in table, then find time sent
        index = self.packetEntryIndexNumber(packet_sequence_number)
        return sent_packets_list(index).time_sent()  #TODO need getter?
             
    #canSend checks if sending window and current in flight un'ACKd packets allow for sending
    def canSendAnotherPacket(self):
        if (RHS - LHS) < SW: return True
        else: return False
        
    def recalculateLHS(self):

        #set up initial value
        lowest_sequence_number = 0

        #check each packet in table to find lowest sequence number
        for packetEntry in sent_packets_list:
            table_sequence_number = packetEntry.packet_sequence_number
            if (table_sequence_number < lowest_sequence_number) or (lowest_sequence_number == 0):
                lowest_sequence_number = table_sequence_number
        
        #update LHS based on lowest value from table
        LHS = lowest_sequence_number    

    #timedOutPacketIndex identifies the first packet in table that has timed out
    def timedOutPacketIndex(self, timeout):

        current_time = time.perf_counter()
        for packetEntry in sent_packets_list:
            if current_time > packetEntry.time_sent:
                return sent_packets_list.index(packetEntry)
        
        return -1
