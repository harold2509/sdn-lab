#!/bin/bash
sysctl -w net.ipv4.ip_forward=1
iptables -F FORWARD
iptables -P FORWARD DROP
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -s 10.0.1.0/24 -d 10.0.3.10 -p icmp -j ACCEPT
iptables -A FORWARD -s 10.0.1.0/24 -d 10.0.3.10 -p tcp --dport 80 -j ACCEPT
iptables -A FORWARD -s 10.0.2.0/24 -d 10.0.3.10 -p icmp -j ACCEPT