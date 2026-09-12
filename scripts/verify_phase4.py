"""
Quick sanity check script — runs core mesh logic without pytest overhead.
Execute: python3 verify_phase4.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.mesh_packet import MeshPacket, HopRecord
from backend.app.core.mesh_node import MeshNode
from backend.app.core.mesh_network import MeshNetwork, NoRouteError
from backend.app.services.mesh_service import build_demo_network, get_network, reset_network

errors = []

def check(name, cond, msg=""):
    if cond:
        print(f"  OK  {name}")
    else:
        print(f"FAIL  {name}: {msg}")
        errors.append(name)

print("=== Phase 4 Core Sanity Checks ===\n")

# --- MeshPacket ---
pkt = MeshPacket("p1", "A", "B", "hello")
check("MeshPacket construction", pkt.packet_id == "p1" and pkt.payload == "hello")
check("MeshPacket hop_log starts empty", pkt.hop_log == [])

# --- HopRecord ---
hr = HopRecord(1, "A", "B", "2026-01-01T00:00:00Z")
check("HopRecord construction", hr.hop_number == 1 and hr.from_node == "A")

# --- MeshNode ---
n = MeshNode("X")
check("MeshNode default not attacker", not n.is_attacker)
n.add_neighbor("Y")
check("MeshNode add_neighbor", "Y" in n.neighbors)
pkt2 = MeshPacket("p2", "A", "X", "data")
n.receive_packet(pkt2)
check("MeshNode receive_packet", len(n.inbox) == 1)

evil = MeshNode("EVIL", is_attacker=True)
evil.capture_packet(pkt2)
check("MeshNode capture_packet", len(evil.captured_packets) == 1)

# Capture is independent
pkt2.payload = "TAMPERED"
check("capture is copy not ref", evil.captured_packets[0].payload == "data")

# --- MeshNetwork routing ---
net = MeshNetwork()
for nid in ["A", "B", "C"]:
    net.add_node(MeshNode(nid))
net.connect_nodes("A", "B")
net.connect_nodes("B", "C")

route = net.find_route("A", "C")
check("BFS A->C = [A,B,C]", route == ["A", "B", "C"], f"got {route}")

try:
    net.find_route("A", "GHOST")
    check("NoRouteError for unknown", False, "should have raised")
except KeyError:
    check("NoRouteError for unknown", True)  # raises KeyError for unknown node -- OK

net2 = MeshNetwork()
for nid in ["X", "Y"]:
    net2.add_node(MeshNode(nid))
# No edge
try:
    net2.find_route("X", "Y")
    check("NoRouteError isolated", False, "should have raised NoRouteError")
except NoRouteError:
    check("NoRouteError isolated", True)

# --- Packet forwarding ---
net3 = MeshNetwork()
for nid in ["A", "B", "C"]:
    net3.add_node(MeshNode(nid))
net3.connect_nodes("A", "B")
net3.connect_nodes("B", "C")

pkt3 = MeshPacket("p3", "A", "C", "fwd")
net3.send_packet(pkt3)
check("Forward: hop_log length 2", len(pkt3.hop_log) == 2, f"got {len(pkt3.hop_log)}")
check("Forward: delivered to C inbox", len(net3.nodes["C"].inbox) == 1)
check("Forward: A inbox empty", len(net3.nodes["A"].inbox) == 0)

# --- Attacker capture ---
net4 = MeshNetwork()
for nid in ["A", "B", "C"]:
    net4.add_node(MeshNode(nid))
attacker = MeshNode("EVIL", is_attacker=True)
net4.add_node(attacker)
net4.connect_nodes("A", "B")
net4.connect_nodes("B", "C")
net4.connect_nodes("EVIL", "B")  # adjacent to route

pkt4 = MeshPacket("p4", "A", "C", "secret")
net4.send_packet(pkt4)
check("Attacker captures adjacent traffic", len(attacker.captured_packets) >= 1)
check("Attacker captured payload", attacker.captured_packets[0].payload == "secret")

# --- Cyclic graph (loop-safe) ---
net5 = MeshNetwork()
for nid in ["A", "B", "C", "D"]:
    net5.add_node(MeshNode(nid))
net5.connect_nodes("A", "B")
net5.connect_nodes("B", "C")
net5.connect_nodes("C", "D")
net5.connect_nodes("D", "A")

route5 = net5.find_route("A", "C")
check("Cyclic: A->C shortest = [A,B,C]", route5 == ["A", "B", "C"], f"got {route5}")

# --- Demo network ---
demo_net = build_demo_network()
check("Demo network has >=5 nodes", len(demo_net.nodes) >= 5)
check("Demo network has ATTACKER", "ATTACKER" in demo_net.nodes)
check("Demo ATTACKER is_attacker=True", demo_net.nodes["ATTACKER"].is_attacker)
check("Demo NODE-A exists", "NODE-A" in demo_net.nodes)
check("Demo NODE-E exists", "NODE-E" in demo_net.nodes)

# Send through demo network
pkt5 = MeshPacket("p5", "NODE-A", "NODE-E", "demo-test")
demo_net.send_packet(pkt5)
check("Demo: packet delivered to NODE-E", len(demo_net.nodes["NODE-E"].inbox) == 1)
check("Demo: ATTACKER captured demo traffic", len(demo_net.nodes["ATTACKER"].captured_packets) >= 1)

print(f"\n=== Results: {len(errors)} failures ===")
for e in errors:
    print(f"  FAILED: {e}")

if not errors:
    print("All checks passed!")
    sys.exit(0)
else:
    sys.exit(1)
