#!/bin/bash
ip addr add 10.0.1.254/24 dev fw2-eth0
ip addr add 10.0.2.254/24 dev fw2-eth0
ip addr add 10.0.3.254/24 dev fw2-eth1
arping -U -c3 -I fw2-eth0 10.0.1.254 > /dev/null 2>&1
arping -U -c3 -I fw2-eth0 10.0.2.254 > /dev/null 2>&1
arping -U -c3 -I fw2-eth1 10.0.3.254 > /dev/null 2>&1