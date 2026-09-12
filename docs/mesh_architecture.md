# RESQ Phase 4 — Software-Simulated Peer-to-Peer Mesh Layer

## 1. Overview & Scope

**Phase 4** implements a software-simulated peer-to-peer (P2P) mesh communication layer for RESQ rescue devices. It models how life-critical packets traverse intermediate nodes across arbitrary topological structures during blackout conditions without relying on centralized cellular, internet, or cloud infrastructure.

### Strict Scope Boundary
* **No Cryptography:** Phase 4 strictly avoids encryption, decryption, digital signatures, key management, and cryptographic authentication.
* **Opaque Payload:** The mesh transport layer treats message content (`payload`) as completely opaque data. It transports payloads from source to destination without inspecting, modifying, parsing, or decrypting them.
* **Local In-Memory Simulation:** Operates 100% locally with zero external network or cloud dependencies.

---

## 2. Core Architecture & Modularity

The mesh layer is organized into decoupled components:

```text
MeshNode (node.py)
   ├── node_id / device_id (DEVICE-### compatible)
   ├── neighbors (set of adjacent node IDs)
   ├── inbox (delivered packets with duplicate suppression)
   └── captured_packets (passive sniffer observation)
          ↓
MeshNetwork (network.py)
   ├── Topology Management (add/remove node, connect/disconnect, get_topology)
   ├── Route Discovery (BFS shortest path with deterministic neighbor ordering)
   ├── Hop-by-Hop Forwarding (records HopRecord on packet)
   └── Delivery Logger (audit trail of delivery successes and failures)
          ↓
MeshPacket (packet.py)
   ├── packet_id
   ├── sender_id / source
   ├── receiver_id / destination
   ├── payload (OPAQUE: plain text, ciphertext, JSON, or binary)
   └── hop_log (ordered traversal history)
```

---

## 3. Future Integration Interface (Phase 5+ Cryptography Boundary)

Phase 4 defines a clean, invariant contract for future security and messaging phases:

### Transport Contract
```text
                  Sender Node Boundary
                           ↓
                send_packet(packet: MeshPacket)
                           ↓
               [ Intermediate Mesh Hops ]
             (Zero-Knowledge Hop Forwarding)
                           ↓
              receive_packet(packet: MeshPacket)
                           ↓
                 Receiver Node Boundary
```

### Opaque Payload Invariant
```python
# The mesh transport layer accepts:
packet = MeshPacket(
    packet_id="PKT-001",
    source="DEVICE-001",
    destination="DEVICE-004",
    payload=opaque_payload,  # Plaintext in Phase 4; EncryptionEnvelope/ciphertext in Phase 5+
)

# And delivers to destination inbox:
delivered_packet = network.send_packet(packet)
assert delivered_packet.payload == opaque_payload  # Guaranteed untouched
```

The mesh layer never checks whether `payload` is plaintext, an authenticated `EncryptionEnvelope` (ChaCha20-Poly1305), or a signed container. Future phases (Phase 5: Secure Message Transmission, Phase 6: Decryption) wrap around this interface without requiring modifications to the routing logic.

---

## 4. Routing & Loop Safety

* **Algorithm:** Breadth-First Search (BFS) shortest-path routing.
* **Loop Prevention:** Maintained via a `visited` set and deterministic neighbor traversal order (`sorted(node.neighbors)`). Cyclic topologies (e.g., `A-B-C-D-A`) terminate without infinite loops.
* **Unreachable Nodes:** If no path connects source and destination, `NoRouteError` is raised and a failed routing attempt is recorded in `delivery_logs`.
* **Dynamic Re-Routing:** If an active edge or node is removed, the router automatically calculates alternative paths if available.
* **Duplicate Suppression:** `MeshNode.receive_packet()` tracks `seen_packet_ids` to prevent duplicate delivery of retransmitted packets.

---

## 5. REST API Endpoints

All endpoints are mounted under `/api/mesh`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/mesh/demo` | Reset and build the standard 5-node demo topology (supports `use_device_ids=True`). |
| `GET` | `/api/mesh/topology` | Return current nodes and edges snapshot. |
| `GET` | `/api/mesh/nodes` | List all registered nodes in the mesh. |
| `POST` | `/api/mesh/nodes` | Register a new simulated node. |
| `DELETE` | `/api/mesh/nodes/{node_id}` | Remove a node and cleanly unregister its edges. |
| `POST` | `/api/mesh/connect` | Connect two nodes with a bidirectional edge. |
| `POST` | `/api/mesh/disconnect` | Disconnect an edge between two nodes. |
| `POST` | `/api/mesh/send` | Route and deliver a packet from sender to receiver. |
| `GET` | `/api/mesh/node/{id}/inbox` | Retrieve delivered packets for a node. |
| `GET` | `/api/mesh/node/{id}/captured` | Retrieve observed packets for an attacker sniffer node. |
| `GET` | `/api/mesh/logs` | Retrieve structured delivery and routing audit logs. |
| `DELETE` | `/api/mesh/reset` | Clear all nodes, edges, and logs. |
