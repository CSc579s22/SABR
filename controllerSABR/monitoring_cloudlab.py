# Copyright (C) 2013, Delft University of Technology, Faculty of Electrical Engineering,
# Mathematics and Computer Science, Network Architectures and Services, Niels van Adrichem
#
# This file is part of OpenNetMon.
#
# OpenNetMon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenNetMon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenNetMon.  If not, see <http://www.gnu.org/licenses/>.

# Special thanks go to James McCauley and all people connected to the POX project,
# without their work and provided samples OpenNetMon could not have been created in the way it is now.

"""
OpenNetMon.Monitoring

Requires openflow.discovery and opennetmon.forwarding
"""
import struct
import time
from collections import defaultdict
from collections import namedtuple
from datetime import datetime

import pox.lib.packet as pkt
import pox.lib.util as util
import pox.openflow.libopenflow_01 as of
import pymongo
from pox.opennetmon.forwarding import ofp_match_withHash
from pox.core import core
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.recoco import Timer
from pox.lib.revent import *
from pox.lib.revent import *
# include as part of the betta branch
from pox.openflow.of_json import *
# include as part of the betta branch
from pox.openflow.of_json import *

log = core.getLogger()
switches = {}

monitored_paths = {}
monitored_pathsById = {}
monitored_pathsByMatch = {}
monitored_pathsBySwitch = {}

pathIterator = {}
barrier = {}

'''
The following contains the list of DPIDs for all switches in the network

'''
switch_dpid = ["b2-a9-42-49-8e-48"]

prev_stats = defaultdict(lambda: defaultdict(lambda: None))

Payload = namedtuple('Payload', 'pathId timeSent')


def _install_monitoring_path(prev_path, adj):
    match = ofp_match_withHash()
    match.dl_src = struct.pack("!Q", prev_path.src)[2:]  # convert dpid to EthAddr
    match.dl_dst = struct.pack("!Q", prev_path.dst)[2:]
    match.dl_type = pkt.ethernet.IP_TYPE
    match.nw_proto = 253  # Use for experiment and testing
    match.nw_dst = IPAddr("224.0.0.255")  # IANA Unassigned multicast addres
    match.nw_src = IPAddr(prev_path.__hash__())  # path hash

    dst_sw = prev_path.dst
    cur_sw = prev_path.dst

    msg = of.ofp_flow_mod()
    msg.match = match
    msg.idle_timeout = 30
    # msg.flags = of.OFPFF_SEND_FLOW_REM
    msg.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
    # log.debug("Installing monitoring forward from switch %s to controller port", util.dpid_to_str(cur_sw))
    switches[dst_sw].connection.send(msg)

    next_sw = cur_sw
    cur_sw = prev_path.prev[next_sw]
    while cur_sw is not None:  # for switch in path.keys():
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.idle_timeout = 10
        # msg.flags = of.OFPFF_SEND_FLOW_REM
        msg.actions.append(of.ofp_action_output(port=adj[cur_sw][next_sw]))
        switches[cur_sw].connection.send(msg)
        next_sw = cur_sw

        cur_sw = prev_path.prev[next_sw]


class Monitoring(object):
    def _timer_MonitorPaths(self):

        def monitor_all():
            # log.debug("Port Stats Sending to Switch\n")
            for con in core.openflow.connections:  # make this _connections.keys() for pre-betta
                con.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

        monitor_all()

    def __init__(self, postfix):
        # log.debug("Monitoring coming up")

        def startup():
            core.openflow.addListeners(self,
                                       priority=0xfffffffe)  # took 1 priority lower as the discovery module, although it should not matter

            core.opennetmon_forwarding.addListeners(self)  # ("NewPath")

            self.decreaseTimer = False
            self.increaseTimer = False
            self.t = Timer(1, self._timer_MonitorPaths, recurring=True)

            self.f = open("output.%s.csv" % postfix, "w")

            self.experiment = postfix

        # log.debug("Monitoring started")

        core.call_when_ready(startup, ('opennetmon_forwarding'))  # Wait for opennetmon-forwarding to be started

    def __del__(self):

        self.f.close()

    def _handle_NewSwitch(self, event):
        switch = event.switch
        # log.debug("New switch to Monitor %s", switch.connection)
        switches[switch.connection.dpid] = switch
        switch.addListeners(self)

    # msg = of.ofp_stats_request(body=of.ofp_port_stats_request())
    # switch.connection.send(msg)

    def _handle_NewFlow(self, event):
        match = event.match

    def _handle_FlowRemoved(self, event):
        match = ofp_match_withHash.from_ofp_match_Superclass(event.ofp.match)


    def _handle_FlowStatsReceived(self, event):
        # stats = flow_stats_to_list(event.stats)
        # log.debug("Received Flow Stats from %s: %s", util.dpid_to_str(event.connection.dpid), stats)
        try:
            client = pymongo.MongoClient("127.0.0.1")
            print("Connected successfully!!!")
        except pymongo.errors.ConnectionFailure as e:
            print("Could not connect to MongoDB: %s" % e)
        # client
        db = client.opencdn
        table = db.netmonitor
        dpid = event.connection.dpid
        for stat in event.stats:
            match = ofp_match_withHash.from_ofp_match_Superclass(stat.match)
            if match.dl_type != pkt.ethernet.LLDP_TYPE and not (
                    match.dl_type == pkt.ethernet.IP_TYPE and match.nw_proto == 253 and match.nw_dst == IPAddr(
                "224.0.0.255")):
                if match not in prev_stats or dpid not in prev_stats[match]:
                    prev_stats[match][dpid] = 0, 0, 0, 0, -1.0
                prev_packet_count, prev_byte_count, prev_duration_sec, prev_duration_nsec, prev_throughput = \
                    prev_stats[match][dpid]

                delta_packet_count = stat.packet_count - prev_packet_count
                delta_byte_count = stat.byte_count - prev_byte_count
                delta_duration_sec = stat.duration_sec - prev_duration_sec
                delta_duration_nsec = stat.duration_nsec - prev_duration_nsec
                if delta_duration_nsec > 0:
                    cur_throughput = delta_byte_count / (delta_duration_sec + (delta_duration_nsec / 1000000000.0))

                    self.f.write("%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%f\n" % (
                        self.experiment, util.dpid_to_str(dpid), match.nw_src, match.nw_dst, match.nw_proto,
                        stat.packet_count, stat.byte_count, stat.duration_sec, stat.duration_nsec, delta_packet_count,
                        delta_byte_count, delta_duration_sec, delta_duration_nsec, cur_throughput))
                    post = {"exp_id": self.experiment, "dpid": util.dpid_to_str(dpid), "srcip": str(match.nw_src),
                            "dstip": str(match.nw_dst), "pkttype": str(match.nw_proto), "pktcount": stat.packet_count,
                            "bytecount": stat.byte_count, "duration": stat.duration_sec, "delpkt": delta_packet_count,
                            "delbytecount": delta_byte_count, "delduration": delta_duration_sec,
                            "throughput": cur_throughput, "date": datetime.utcnow()}
                    # posts = table
                    post_id = table.insert_one(post).inserted_id
                    self.f.flush()
                    prev_stats[match][
                        dpid] = stat.packet_count, stat.byte_count, stat.duration_sec, stat.duration_nsec, cur_throughput
                # influence the timer by inspecting the change in throughput
                if abs(cur_throughput - prev_throughput) > .05 * prev_throughput:
                    self.decreaseTimer = False
                if abs(cur_throughput - prev_throughput) > .20 * prev_throughput:
                    self.increaseTimer = True

    # This event handler pushes the collected port statistics from all switches in the hetwork
    # into the MongoDB archival system
    def _handle_PortStatsReceived(self, event):
        dpid = event.connection.dpid
        try:
            client = pymongo.MongoClient("127.0.0.1")
            print("Connected successfully!!!")
        except pymongo.errors.ConnectionFailure as e:
            print("Could not connect to MongoDB: %s" % e)
        db = client.opencdn
        table_port = db.portmonitor
        for stat in event.stats:
            # match = ofp_match_withHash.from_ofp_match_Superclass(stat.match)
            if stat.port_no != 65535:
                stats = flow_stats_to_list(event.stats)
                if dpid not in prev_stats or stat.port_no not in prev_stats[dpid]:
                    prev_stats[dpid][stat.port_no] = 0, 0, 0, 0
                prev_rx_packet, prev_rx_bytes, prev_tx_packet, prev_tx_bytes = prev_stats[dpid][stat.port_no]

                delta_rx_packet = stat.rx_packets - prev_rx_packet
                delta_rx_bytes = stat.rx_bytes - prev_rx_bytes
                delta_tx_packet = stat.tx_packets - prev_tx_packet
                delta_tx_bytes = stat.tx_bytes - prev_tx_bytes

                # self.f3.write("PortStatsReceived from %s: %s \t %s \t %s\n"%(dpidToStr(event.connection.dpid), stats, str(delta_rx_packet),str(delta_tx_bytes) ))
                log.debug("Monitoring_Called Statistics")
                post = {"exp_id": self.experiment, "dpid": dpidToStr(event.connection.dpid),
                        "RXpackets": str(delta_rx_packet), "RXbytes": str(delta_rx_bytes),
                        "TXpackets": str(delta_tx_packet), "TXbytes": str(delta_tx_bytes), "portno": stat.port_no,
                        "date": datetime.utcnow()}
                post_id = table_port.insert_one(post).inserted_id
                # self.f3.flush()
                prev_stats[dpid][stat.port_no] = stat.rx_bytes, stat.rx_bytes, stat.tx_packets, stat.tx_bytes

    def _handle_BarrierIn(self, event):
        timeRecv = time.time()
        dpid = event.dpid
        xid = event.xid
        if xid not in barrier:
            return

        (initiator, prevTime) = barrier[xid]
        # log.debug("Delay from switch %s initiated by %s = %f"%(util.dpid_to_str(dpid), util.dpid_to_str(initiator), timeRecv - prevTime))
        self.f2.write("Switch,%s,%s,%f\n" % (util.dpid_to_str(initiator), util.dpid_to_str(dpid), timeRecv - prevTime))
        self.f2.flush()
        del barrier[xid]
        return EventHalt

    def _handle_PacketIn(self, event):
        # log.debug("Incoming packet")
        timeRecv = time.time()
        packet = event.parsed
        if packet.effective_ethertype != pkt.ethernet.IP_TYPE:
            return
        ip_pck = packet.find(pkt.ipv4)
        if ip_pck is None or not ip_pck.parsed:
            log.error("No IP packet in IP_TYPE packet")
            return EventHalt

        if ip_pck.protocol != 253 or ip_pck.dstip != IPAddr("224.0.0.255"):
            # log.debug("Packet is not ours, give packet back to regular packet manager")
            return
        else:
            # log.debug("Received monitoring packet, with payload %s."%(ip_pck.payload))
            payload = eval(ip_pck.payload)

            # log.debug("Delay from switch %s to %s = %f"%(EthAddr(packet.src), EthAddr(packet.dst), timeRecv - payload.timeSent ))
            self.f2.write("Path,%s,%s,%f\n" % (EthAddr(packet.src), EthAddr(packet.dst), timeRecv - payload.timeSent))
            self.f2.flush()
            return EventHalt


def launch(postfix=datetime.now().strftime("%Y%m%d%H%M%S")):
    core.registerNew(Monitoring, postfix)
