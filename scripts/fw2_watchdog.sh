#!/bin/bash
# Se ejecuta dentro de fw2. Detecta la caida de fw (10.0.1.254) y activa fw2.
FALLOS=0
while true; do
  if ping -c1 -W0.2 -I 10.0.1.253 10.0.1.254 > /dev/null 2>&1; then
    FALLOS=0
  else
    FALLOS=$((FALLOS+1))
  fi
  if [ "$FALLOS" -ge 3 ]; then
    date +%s.%N > /tmp/t_deteccion.txt
    bash /home/sdnlabo/sdn-lab/scripts/fw2_activate.sh
    date +%s.%N > /tmp/t_activado.txt
    exit 0
  fi
  sleep 0.2
done