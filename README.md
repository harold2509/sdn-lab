# sdn-lab: red virtual SDN/NFV con aislamiento multitenant

Laboratorio de redes definidas por software (SDN) y virtualización de funciones de red (NFV) sobre Mininet, Open vSwitch y Ryu, con la política escrita como código (Ansible + Git) y fallas medidas.

El laboratorio demuestra que una red virtual puede:

- aislar a dos clientes (tenants) que comparten infraestructura,
- obligar su tráfico a pasar por un firewall en software (VNF),
- automatizarse con Ansible y versionarse con Git, con rollback,
- recuperarse de fallas, con tiempos medidos y repetidos.

## Topología

```
Tenant A: a1, a2 (10.0.1.0/24) ─┐
                                 ├─ s1 ── fw ── s2 ── srv (10.0.3.10, HTTP :80)
Tenant B: b1, b2 (10.0.2.0/24) ─┘        └─ fw2 (respaldo pasivo)
```

| Componente | Función |
| --- | --- |
| `s1` | Switch Open vSwitch (OpenFlow 1.3, `fail_mode: secure`). Aplica la política de aislamiento con flujos. |
| `s2` | Switch en modo `standalone`. Solo une `fw` con `srv`. |
| `fw` | VNF router/firewall con `iptables`. Puertas de enlace 10.0.1.254, 10.0.2.254 y 10.0.3.254. |
| `fw2` | Respaldo pasivo de `fw` (solo en `topo_ha.py`). |
| `srv` | Servicio compartido (10.0.3.10) con HTTP en el puerto 80. |

Los enlaces están limitados a 100 Mbit/s (`TCLink`).

**Política.** Entre tenants no hay comunicación. En `s1`, todo se descarta por defecto (`priority=0 drop`) y solo se permite ARP e IP dentro de cada subred y hacia `10.0.3.0/24`. En `fw`, el Tenant A puede ICMP y HTTP hacia `srv`; el Tenant B, solo ICMP.

## Requisitos

Ubuntu 22.04 (probado en una VM de VMware) con:

- Mininet y Open vSwitch 2.17
- Ryu 4.34 (solo para las pruebas con controlador)
- Ansible 2.10
- `iperf3`, `nmap`, `jq`, `tcpdump`, `curl`

### Nota sobre Ryu

Con Ubuntu 22.04 y Python 3.10, Ryu necesitó un entorno virtual y dos ajustes:

```bash
python3 -m venv ~/ryu-env
source ~/ryu-env/bin/activate
pip install "ryu==4.34" --no-build-isolation --no-cache-dir
sed -i 's/from eventlet.wsgi import ALREADY_HANDLED/ALREADY_HANDLED = "<ALREADY_HANDLED>"/' \
  ~/ryu-env/lib/python3.10/site-packages/ryu/app/wsgi.py
printf '%s\n' '#!/home/sdnlabo/ryu-env/bin/python' 'from ryu.cmd.manager import main' 'main()' > ~/ryu-env/bin/ryu-manager
chmod +x ~/ryu-env/bin/ryu-manager
```

## Estructura

| Ruta | Contenido |
| --- | --- |
| `topo/topo.py` | Topología base. Con el argumento `ryu` conecta `s1` a un controlador remoto. |
| `topo/topo_ha.py` | Topología con el respaldo `fw2`. |
| `flows/s1_flows.txt` | Reglas OpenFlow de `s1` en texto. |
| `ansible/vars.yml` | Política como datos: tenants y subredes. |
| `ansible/flows.j2` | Plantilla que convierte la política en reglas. |
| `ansible/site.yml` | Playbook que aplica las reglas en `s1` (`replace-flows`). Es idempotente. |
| `scripts/fw_rules.sh` | Reglas de `iptables` de la VNF. |
| `scripts/fw2_activate.sh` | Pone a `fw2` en servicio (toma las IP y envía ARP gratuitos). |
| `scripts/fw2_reset.sh` | Devuelve `fw2` a respaldo pasivo. |
| `scripts/fw2_watchdog.sh` | Vigilante que activa `fw2` si `fw` deja de responder. |
| `results/` | Mediciones en bruto (pings con marca de tiempo, JSON de `iperf3`, tiempos). |

## Uso rápido

Siempre desde una red limpia:

```bash
cd ~/sdn-lab
sudo mn -c
```

**Red sin controlador** (aislamiento, firewall, mediciones):

```bash
sudo python3 topo/topo.py
# en otra terminal, aplicar la política en s1
sudo -v
ansible-playbook ansible/site.yml
```

**Red con controlador Ryu:**

```bash
# terminal 2
source ~/ryu-env/bin/activate
ryu-manager ryu.app.simple_switch_13
# terminal 1
sudo python3 topo/topo.py ryu
```

**Red con respaldo fw2:**

```bash
sudo python3 topo/topo_ha.py
```

Comprobación inicial, dentro del prompt `mininet>`:

```
a1 ping -c2 10.0.3.10      # 0 % de pérdida
b1 ping -c2 10.0.3.10      # 0 % de pérdida
a1 ping -c2 -W1 b1         # 100 % de pérdida (aislamiento)
```

Si `srv` no responde tras reiniciar, configura el firewall con `fw bash scripts/fw_rules.sh`.

## Mediciones

Cada medición se repitió al menos tres veces. La media y la desviación (poblacional) se calculan con los archivos de `results/`.

| Medición | Resultado | n |
| --- | --- | --- |
| RTT a `srv` | 0,213 ms de media, 0 % de pérdida | 100 pings |
| Throughput a `srv` | Tenant A 86,2 Mbit/s; Tenant B 87,1 Mbit/s | 5 y 3 |
| Throughput `a1`→`a2` (sin pasar por `fw`) | 83,8 Mbit/s | 3 |
| Aislamiento entre tenants | 100 % de pérdida; `nmap`: todos los puertos filtrados | 20 pings por prueba |
| Provisión con Ansible | 4,77 s (4,71 s con el Tenant C) | 5 |
| Provisión manual | 86,8 s | 3 |
| Rollback con `git revert` | 6,17 s, 0 reglas residuales | 3 |
| Falla del enlace `s1`–`fw` (3 s inyectados) | brecha 3,12 s | 5 |
| Controlador caído, flujo instalado | 0 interrupciones | 3 |
| Controlador caído, par nuevo | 100 % de pérdida | 3 |
| Reconexión del controlador | 2,37 s | 3 |
| Falla de `fw`, conmutación programada a `fw2` | 0,192 s | 5 |
| Falla de `fw`, watchdog automático | 1,271 s | 5 |
| Falla de `fw`, activación manual de `fw2` | 23,06 s (rango 11,9 a 38,6 s) | 4 |

### Cómo se calcula la brecha

La brecha es el mayor intervalo entre dos respuestas consecutivas de un `ping -i0.1 -D` (con marca de tiempo) lanzado antes de la falla. Es el tiempo sin servicio, con resolución de 0,1 s.

```bash
brecha() { for f in "$@"; do LC_ALL=C awk -F'[][]' '/bytes from/{t=$2+0; if(p>0 && t-p>m) m=t-p; p=t} END{printf "%.3f\n", m}' $f; done | LC_ALL=C awk '{print; s+=$1; ss+=$1*$1; n++} END {m=s/n; printf "media=%.3f s, desv=%.3f s, n=%d\n", m, sqrt(ss/n-m*m), n}'; }

brecha results/falla_[1-5].txt
brecha results/fw2_manual_humano_[1-4].txt
```

### Notas de método

- Para medir el throughput se abre temporalmente el puerto TCP 5201 en `fw` y se cierra al terminar. La política del laboratorio solo permite ICMP y HTTP.
- La conmutación programada es el mejor caso: la falla y la activación ocurren a la vez, sin tiempo de detección. El watchdog suma unos 1,1 s de detección.
- El tiempo manual incluye el tecleo del operador y no el de notar la falla, por lo que es una cota optimista.

## Ramas

- `main`: versión estable, con el Tenant C revertido.
- `feat/tenant-c`: alta del Tenant C (una línea y 4 reglas). El revert `a0b127c` es la evidencia de rollback.
- `feat/fw2`: respaldo `fw2` y watchdog.

## Limitaciones

- La resolución de la brecha está limitada por el intervalo del ping (0,1 s).
- No se probó suplantación de IP/MAC ni envenenamiento ARP.
- El Tenant C se provisionó solo como política; no se añadieron hosts a la topología.
- Los tiempos manuales son una cota optimista, porque quien los midió ya conocía los pasos.
