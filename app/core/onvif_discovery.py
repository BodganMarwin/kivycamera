import socket
import uuid
import re
import xml.etree.ElementTree as ET
from typing import List, Dict

WS_DISCOVERY_PROBE = """<?xml version="1.0" encoding="utf-8"?>
<Envelope xmlns:dn="http://www.onvif.org/ver10/network/wsdl"
          xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Header>
    <wsa:MessageID xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">uuid:{message_id}</wsa:MessageID>
    <wsa:To xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    <wsa:Action xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
  </Header>
  <Body>
    <Probe xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
           xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">
      <Types>dn:NetworkVideoTransmitter</Types>
      <Scopes />
    </Probe>
  </Body>
</Envelope>"""

def discover_onvif_cameras(timeout: float = 2.5) -> List[Dict[str, str]]:
    """
    Envía una sonda WS-Discovery UDP multicast para encontrar cámaras ONVIF en la red local.
    Retorna una lista de diccionarios con IP, XAddrs y nombre detectado.
    """
    cameras: List[Dict[str, str]] = []
    seen_ips = set()

    multicast_group = ('239.255.255.250', 3702)
    message_id = str(uuid.uuid4())
    probe_data = WS_DISCOVERY_PROBE.format(message_id=message_id).encode('utf-8')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    try:
        sock.sendto(probe_data, multicast_group)

        while True:
            try:
                data, addr = sock.recvfrom(65535)
                ip = addr[0]
                if ip in seen_ips:
                    continue
                seen_ips.add(ip)

                xml_str = data.decode('utf-8', errors='ignore')
                
                # Extraer XAddrs (URLs de servicios ONVIF)
                xaddrs = []
                xaddrs_match = re.search(r'<[^:]*:XAddrs[^>]*>(.*?)</[^:]*:XAddrs>', xml_str, re.DOTALL)
                if xaddrs_match:
                    xaddrs = xaddrs_match.group(1).strip().split()

                # Extraer Scopes (nombre del hardware si está disponible)
                name = f"Cámara ONVIF ({ip})"
                scopes_match = re.search(r'<[^:]*:Scopes[^>]*>(.*?)</[^:]*:Scopes>', xml_str, re.DOTALL)
                if scopes_match:
                    scopes = scopes_match.group(1).strip().split()
                    for s in scopes:
                        if "onvif://www.onvif.org/name/" in s:
                            name = s.split("/")[-1].replace("_", " ")
                            break

                cameras.append({
                    "ip": ip,
                    "name": name,
                    "xaddrs": xaddrs[0] if xaddrs else f"http://{ip}/onvif/device_service",
                    "default_rtsp": f"rtsp://{ip}:554/live"
                })

            except socket.timeout:
                break
            except Exception as e:
                print(f"[ONVIF Discovery] Error procesando respuesta: {e}")
                break

    except Exception as e:
        print(f"[ONVIF Discovery] Error enviando sonda UDP: {e}")
    finally:
        sock.close()

    return cameras
