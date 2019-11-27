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

    #initialize LHS and RHS for sender_window calculations
    LHS = 1
    RHS = 1
	
	#initialize estRTT and t_out with values from file
	estRTT = RTT
	t_out = 2 * estRTT
		
    #initialize sender window table for tracking SW and unACKd packets
	swTable = SendingWindowTable
	
    #stay in loop while blaster agent is running	
    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet(timeout=recv_timeout)  #TODO changed timeout here to value from file
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet")
			
			#TODO receive and parse an ACK package (check seq number? check first 8 bytes?)
			
			#if we already ACK this packet, ignore this packet and continue
			if swTable.packetIsInTable(packet) == False: continue
			
			#new ACK - retrieve the RTT for the packet and then remove from the table
			packet_rtt = time.perf_counter() - swTable.sentTimeForPacket(packet)
			swTable.removeFromPacketList(packet)
				
			#new ACK - do estRTT and timeout calculations
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
			
			log_debug("So, attempt to send something now, right?")
			#check SW C1: RHS - LHS <= SW to  and determine if a packet can be sent now
			SendingWindowTable.canSendAnotherPacket == FALSE: continue

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
			#TODO - this is a coarse timeout? not sure! Maybe only count if first_packet_start_time is not None?
			#num_tos += 1
			
			#if this is the first packet, start tx counter:
			#first_packet_start_time = time.perf_counter()
			
			#if this is a first transmission:
			#track number of bytes being sent:
			#goodput_Bytes
			
			#increment RHS
			RHS += 1
			
			
			#if we are retransmitting a packet, increment count by one:
			#num_ret += 1
			#reTx_Bytes
			
			

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
		

		
#sentPacket objects will store info about packets that are in the sender window awaiting ACK
#TODO packet number and seq number can be the same. Double check whether this is byte oriented.
class sentPacket:
    def __init__(self,packet_number, packet_sequence_number):
        self.packet_number = packet_number
        self.packet_sequence_number = packet_sequence_number
        self.time_sent = time.perf_counter()
        #TODO do we need more details? payload? for validatig upon receiving? probably not.

	#packet will be added when it is sent, along with sending time stamp
	#packet will be removed when it is acknowledged

#SendingWindowTable will track unACKd packets and provide sending window calculations
class SendingWindowTable:
    def __init__(self,sending_window):
		self.sent_packets_list = list
		SW = sending_window  #count
		LHS = 1
		RHS = 1

	#called after packet is sent - will add packet if necessary (first time) and update time stamp
    def addToPacketList(self, packet_number, time_sent):
        
		#if packet isn't already in table, create sentPacket object, add to table with time, increment RHS
		if packetIsInTable == False:self.blockedPorts.count(packet_number) == 0:
            self.sent_packets_list.append(sentPacket(packet_number, time_sent))
		    self.updateRHS()
		
		#otherwise, update the time sent stamp for 
		#Don't think we need this - question to Varun
		   
    #removeFromPacketList when we receive an ACK - remove from table and update LHS
    def removeFromPacketList(self, packet_number):
        #if packet is in table, 
        if self.blockedPorts.count(packet_number) > 0:
             self.blockedPorts.remove(packet_number)

    #determine if packet is in table
    #TODO should this return the index in list, instead of True/False, so we cna remove things
    def packetIsInTable(self, packet):
	    #this code isn't right.
        if self.sent_packets.count > 0: return True
		else: return False

	#returns time a packet was sent; use for calculating RTT
	def sentTimeForPacket(self, packet):
		#return the time it was sent.
		return
			 
    #canSend checks if sending window and current in flight un'ACKd packets allow for sending
	def canSendAnotherPacket(self):
        if (RHS - LHS) < SW: return True
		else: return False
	
	def recalculateLHS(self):
	    #loop through all packets in table
		#determine the packet with the lowest #
		#assign that to LHS
	    #check SW C1: RHS - LHS <= SW to  and determine if a packet can be sent now
			#if (RHS - LHS) == SW: continue
        return
    
    #updateRHS will increment RHS. This should be called for each packet sent.
    def updateRHS(self):
        RHS += 1 
        return
