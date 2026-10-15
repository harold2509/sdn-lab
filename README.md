# Laboratorio SDN/NFV: redes virtuales con Mininet y Open vSwitch

Práctica de Arquitectura de Redes Virtuales SDN/NFV: topología con plano de control y reenvío separados, aislamiento por tenant, VNF (firewall/router) con respaldo, automatización con Ansible y Git, y mediciones de desempeño y falla.

## Topología

```
 a1,a2 (Tenant A 10.0.1.0/24) ─┐
                               s1 ──┬── fw  ──┬── s2 ── srv (10.0.3.10)
 b1,b2 (Tenant B 10.0.2.0/24) ─┘     └── fw2 ──┘
```

- `s1`: switch de borde OpenFlow 1.3 (`fail_mode: secure`), política por flujos.
- `fw` / `fw2`: VNF router/firewall (iptables), activo y respaldo.
- `srv`: servicio compartido (HTTP:80).

## Estructura

| Carpeta | Contenido |
|---|---|
| `topo/` | `topo.py` (base), `topo_ha.py` (con `fw2`) |
| `flows/` | `s1_flows.txt` (política OpenFlow manual) |
| `ansible/` | `vars.yml`, `flows.j2`, `site.yml` (política como código) |
| `scripts/` | `fw_rules.sh`, `fw2_activate.sh`, `fw2_reset.sh`, `fw2_watchdog.sh` |
| `results/` | Evidencias y mediciones |

## Requisitos

Ubuntu 22.04, Mininet, Open vSwitch 2.17, Ryu 4.34 (en venv), Ansible, iperf3, iputils-arping.

## Ejecución

```bash
sudo mn -c
sudo python3 topo/topo_ha.py          # terminal 1
ansible-playbook ansible/site.yml -K  # terminal 2: aplica flujos en s1
```
En `mininet>`:
```
fw bash scripts/fw_rules.sh
fw2 bash scripts/fw_rules.sh
srv python3 -m http.server 80 &
a1 ping -c3 10.0.3.10
```

## Resultados

| Métrica | Resultado |
|---|---|
| RTT a srv (100 pings) | 0,213 ms medio (mín 0,150, máx 1,660) |
| Throughput TCP | A: 85,8 Mbit/s, B: 86,5 Mbit/s (1 muestra c/u) |
| Aislamiento | 0 % pérdida intra-tenant; 100 % entre tenants; nmap: 200 puertos filtrados; `ofproto/trace`: drop |
| Política VNF | A: ICMP + HTTP; B: solo ICMP (HTTP bloqueado) |
| Provisión (Ansible) | Base 4,77 s (desv. 0,07); con Tenant C 4,71 s (desv. 0,08); rollback 5,11 s |
| Falla de enlace s1-fw | Brecha 3,12 s con 3 s inyectados (n=5) |
| Caída del controlador | 0 interrupción en flujos instalados; pares nuevos 100 % pérdida; recuperación 2,51 s (n=1) |
| Falla de `fw`, conmutación programada | 0,192 s (n=5; limitada por resolución de ping 0,1 s) |
| Falla de `fw`, watchdog automático | 1,271 s (desv. 0,042; n=5) |

## Git

Ramas `feat/tenant-c` y `feat/fw2`. El commit `Revert "feat: agrega tenant C"` (`a0b127c`) es la evidencia de rollback con trazabilidad.