#!/usr/bin/env python3
import sys
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

def build(use_ctl=False):
    net = Mininet(switch=OVSSwitch, link=TCLink, controller=None, autoSetMacs=True)
    if use_ctl:
        net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    s1 = net.addSwitch('s1', protocols='OpenFlow13', failMode='secure', dpid='0000000000000001')
    s2 = net.addSwitch('s2', failMode='standalone')

    a1 = net.addHost('a1', ip='10.0.1.1/24', defaultRoute='via 10.0.1.254')
    a2 = net.addHost('a2', ip='10.0.1.2/24', defaultRoute='via 10.0.1.254')
    b1 = net.addHost('b1', ip='10.0.2.1/24', defaultRoute='via 10.0.2.254')
    b2 = net.addHost('b2', ip='10.0.2.2/24', defaultRoute='via 10.0.2.254')
    fw = net.addHost('fw', ip=None)
    fw2 = net.addHost('fw2', ip=None)
    srv = net.addHost('srv', ip='10.0.3.10/24', defaultRoute='via 10.0.3.254')

    # Puertos de s1: a1=1, a2=2, b1=3, b2=4, fw=5, fw2=6
    for h in (a1, a2, b1, b2):
        net.addLink(h, s1, bw=100)
    net.addLink(s1, fw, bw=100)      # fw-eth0
    net.addLink(fw, s2, bw=100)      # fw-eth1
    net.addLink(s1, fw2, bw=100)     # fw2-eth0
    net.addLink(fw2, s2, bw=100)     # fw2-eth1
    net.addLink(srv, s2, bw=100)

    net.start()
    fw.cmd('ip addr add 10.0.1.254/24 dev fw-eth0')
    fw.cmd('ip addr add 10.0.2.254/24 dev fw-eth0')
    fw.cmd('ip addr add 10.0.3.254/24 dev fw-eth1')
    fw.cmd('sysctl -w net.ipv4.conf.all.arp_ignore=1 net.ipv4.conf.all.arp_announce=2')
    fw2.cmd('sysctl -w net.ipv4.conf.all.arp_ignore=1 net.ipv4.conf.all.arp_announce=2')
    return net

if __name__ == '__main__':
    setLogLevel('info')
    net = build(use_ctl=(len(sys.argv) > 1 and sys.argv[1] == 'ryu'))
    CLI(net)
    net.stop()