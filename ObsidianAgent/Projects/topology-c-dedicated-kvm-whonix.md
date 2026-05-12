# Topology C - Dedicated KVM/Whonix Compartmentalized Host

## Summary

Topology C is the strongest source-backed design in this hardware-constrained setup. It is
not a "more layers" design. It is a **less trust, less ambiguity, more isolation** design:

- one dedicated host
- one stock Whonix-Gateway
- multiple role-separated Whonix-Workstations
- one optional offline vault VM
- Tor bridges when needed
- no pfSense in the anonymity path
- no host VPN in the baseline path
- no second Tor layer

This is **more secure than Topology A** because it removes a custom router from the anonymity
path, restores Whonix's expected split model, reduces leak surface, and lowers operator error.

It is **closer to professional anonymity practice**, but it is **not** a promise of perfect
anonymity against a global passive adversary or endpoint compromise.

---

## 1. Honest Threat Model

Topology C is designed to improve resistance against:

- local ISP visibility of direct Tor usage when bridges are enabled
- accidental clearnet leaks from workstation applications
- identity cross-contamination between research, communications, and risky browsing
- operator mistakes caused by stacked VPN/Tor/router complexity
- compromise of one workstation identity spilling directly into another

Topology C does **not** claim to defeat:

- a global passive adversary doing end-to-end traffic correlation
- a fully compromised host OS
- hardware implants, Evil Maid, or physical seizure without proper host hardening
- poor OPSEC such as account reuse, browser misuse, metadata leaks, or unsafe document handling

---

## 2. Why Topology C Replaces Topology A

Topology A is useful as a **lab** for pfSense + libvirt + Whonix. It is not the best
operational anonymity design.

Topology C replaces it for real anonymity-oriented work because:

- it keeps the Whonix security model close to stock
- it removes pfSense from the live anonymity chain
- it avoids the custom `ws-int` redesign mistake
- it avoids adding extra DNS, NAT, logging, and admin surfaces
- it removes the temptation to stack VPNs and second-Tor paths
- it makes failures easier to detect and reason about

If pfSense is still wanted, keep it as a **separate training environment**. Do not place it
between the user and Whonix in the baseline anonymity path.

---

## 3. Topology Diagram

```text
Physical uplink
  -> dedicated Linux host (minimal admin role only)
  -> libvirt/KVM
  -> Whonix-Gateway external NIC
  -> Tor network
  -> Internet

Whonix-Gateway internal NIC
  -> Whonix-Internal network
  -> ws-comms
  -> ws-research
  -> ws-burner

Optional:
  -> vault-offline (no NIC attached)
```

### Core rule

Only **Whonix-Gateway** gets upstream network access.

All online workstations reach the network **only** through the Whonix internal path.

The offline vault VM has **no network adapter**.

---

## 4. Host Role

The host is a **dedicated anonymity workstation host**, not a daily-driver desktop.

Allowed host activity:

- firmware updates
- OS updates
- libvirt/KVM administration
- VM lifecycle management
- encrypted backup handling
- local console inspection

Forbidden host activity:

- normal web browsing
- personal email or chat
- document opening from untrusted sources
- social media
- development unrelated to the anonymity stack
- gaming, streaming, or general daily-use activity

### Host hardening baseline

- Full-disk encryption enabled.
- Firmware/BIOS password enabled.
- VT-x/AMD-V and VT-d/IOMMU enabled.
- No unnecessary host services exposed on the LAN.
- Firewall default deny for inbound host traffic.
- Minimal package set: `qemu`, `libvirt`, `virt-manager`, `dnsmasq`, `ovmf`, and support tooling only.
- Do not enable shared folders by default.
- Do not route host traffic through a baseline VPN in this design.

### Why no host VPN

Whonix's own KVM documentation notes known issues with host VPNs in KVM setups. More
importantly, a host VPN adds a new trust point and a new failure mode without fixing Tor's
core correlation limits.

---

## 5. VM Inventory

### 5.1 `Whonix-Gateway`

Purpose:

- the only Tor egress point
- the only place where bridges are configured
- the only VM with an upstream-facing role

Rules:

- keep the imported Whonix KVM network model as close to stock as possible
- do not redesign the internal subnet unless you are also fully reconfiguring Whonix internals
- do not add a second VPN here in the baseline design
- do not use it for browsing, file handling, or general admin work

### 5.2 `ws-comms`

Purpose:

- long-lived communications identity
- email, messaging, controlled account access

Rules:

- no research browsing
- no random link clicking
- no document opening from untrusted senders
- credentials unique to this role only

### 5.3 `ws-research`

Purpose:

- long-lived research identity
- browsing, collection, reading, note taking

Rules:

- no personal accounts
- no shared browser state with `ws-comms`
- no risky attachments; those go to `ws-burner`

### 5.4 `ws-burner`

Purpose:

- risky links
- untrusted attachments
- disposable accounts
- one-off collection or testing

Rules:

- snapshot before use or revert after each mission
- no credential reuse from `ws-comms` or `ws-research`
- no persistence assumption
- this is the only online workstation allowed to touch high-risk content first

### 5.5 `vault-offline`

Purpose:

- secrets
- notes
- credentials
- key material
- final retained artifacts

Rules:

- no network adapter
- no browser
- import only manually reviewed artifacts
- never use as a staging box for untrusted content

---

## 6. Network and Routing Rules

### 6.1 Keep the Whonix split model stock

Do **not** repeat Topology A's custom `ws-int` design with a DHCP-backed `10.20.20.0/24`
segment unless you also fully reconfigure the guest-side Whonix networking model.

Topology C assumes:

- Whonix KVM images are imported from the official KVM workflow
- the Whonix-provided internal/external network structure remains the baseline
- additional workstations attach to the Whonix internal side only

### 6.2 No alternate egress

- workstations must not have a second NIC
- workstations must not use a bridged NIC
- workstations must not use the host uplink directly
- only the Gateway should touch the upstream-facing libvirt network

### 6.3 No pfSense in path

pfSense is removed because it adds:

- another admin plane
- another DNS surface
- another logging surface
- another NAT layer
- another place to fail open

This is a net loss for anonymity operations on a single-box design.

---

## 7. Bridges and Tor Signaling

If hiding obvious Tor usage from the ISP or local network matters, use **bridges** on
Whonix-Gateway rather than a host VPN.

Approved baseline:

- obfs4 or another currently supported Tor bridge transport
- configuration performed on the Gateway, not on the host
- no fallback to clearnet if bridge connection fails

Not approved in the baseline:

- host VPN added only to hide Tor
- second VPN inside a workstation
- Tor-over-Tor

Bridges reduce straightforward public-relay visibility. They do **not** create a guarantee
against a serious traffic analyst.

---

## 8. Identity and Data-Flow Rules

### Identity separation

- `ws-comms` identity never logs into accounts used from `ws-research`
- `ws-research` never becomes the place where risky files are opened
- `ws-burner` never becomes a long-term account workspace
- `vault-offline` never touches the network

### File-flow policy

Default state:

- no shared folders
- no clipboard sync assumptions across roles

Allowed path for risky files:

1. file enters `ws-burner`
2. file is inspected, converted, or sanitized there
3. if retention is needed, export to a temporary host-side staging directory
4. manually review and then import into `vault-offline` if justified

Never allow:

- direct import of untrusted files into `vault-offline`
- random documents opened on the host
- direct movement from `ws-burner` into `ws-comms`

---

## 9. Operational Rules

### Session model

Topology C uses a **hybrid model**:

- persistent compartments for stable identities
- disposable or revertable burner activity for risky sessions

### Browser and app discipline

- use Tor Browser in the Whonix workstations
- do not install arbitrary browser extensions
- do not mix personal and anonymous accounts
- do not rely on "private mode" to separate identities
- treat every identity as its own compartment

### Update model

- update the host separately from the Whonix VMs
- update the Gateway before dependent workstation testing
- validate Tor connectivity after update changes
- do not mix update testing with live operational sessions

---

## 10. Validation Checklist

### Host checks

- `libvirtd` active
- user in `libvirt` and `kvm`
- FDE enabled
- inbound host firewall restrictive
- no unnecessary network services exposed

### Gateway checks

- only Gateway has upstream access
- Tor connectivity works
- bridge connectivity works when enabled
- no second VPN configured in baseline mode

### Workstation checks

- each online workstation has only the internal Whonix path
- each workstation shows Tor egress, not clearnet host egress
- no extra NICs attached
- `ws-burner` reset workflow works

### Isolation checks

- `vault-offline` has no NIC
- `ws-comms` and `ws-research` keep separate credentials and browser state
- risky file flow only starts in `ws-burner`

### Leak checks

- Tor check from each online workstation
- DNS leak test from each online workstation
- public IP confirmation from each online workstation
- confirm no clearnet fallback when Tor or bridges fail

---

## 11. Comparison Against Topology A

| Area | Topology A | Topology C | Why C is better |
|---|---|---|---|
| Upstream path | `pfSense -> Whonix -> workstation` | `Whonix-Gateway -> workstation` | fewer components and trust points |
| Internal network | custom `ws-int` redesign | stock Whonix split model | avoids guest reconfiguration mistakes |
| Admin surfaces | host + pfSense + Whonix | host + Whonix | less logging, less DNS, less NAT |
| Failure analysis | multiple routing/NAT layers | simpler Tor split model | clearer fail-closed reasoning |
| Identity layout | one final workstation implied | multiple role-specific workstations | better compartmentalization |
| Risky file handling | not central to design | dedicated burner workflow | safer operational discipline |
| Tor signaling mitigation | implied future VPN additions | bridges on Gateway | lower trust and lower complexity |

### Net result

Topology C wins because it improves the things that matter operationally:

- isolation
- determinism
- compartmentalization
- reduced trust
- reduced leak surface

It does **not** win by adding more hops.

---

## 12. Non-Negotiable Prohibitions

Do not add these to Topology C baseline:

- pfSense in the anonymity path
- host VPN to "improve anonymity"
- workstation VPN layered over Whonix
- Tor-over-Tor
- direct bridged workstation NICs
- daily-driver activity on the host
- long-term use of the burner workstation

These changes make the system harder to reason about and usually worse in practice.

---

## 13. Caveats

- Qubes-Whonix would still be the stronger isolation model if hardware compatibility allowed it.
- Whonix on KVM is viable, but the KVM workflow is community-supported rather than a fully first-class Qubes experience.
- No desktop topology makes a user anonymous if OPSEC is poor.
- A compromised host can still destroy the guarantees of all guest VMs.

Topology C should therefore be described honestly as:

> the strongest practical non-Qubes single-box design in this environment, not a magic
> invisibility system

---

## 14. Source Notes

Primary references:

- Whonix KVM: https://www.whonix.org/wiki/KVM
- Whonix KVM support caveat: https://www.whonix.org/wiki/KVM/Support
- Connections between Whonix-Gateway and Whonix-Workstation: https://www.whonix.org/wiki/Connections_between_Gateway_and_Workstation
- Whonix versus VPNs: https://www.whonix.org/wiki/Whonix_versus_VPNs
- Whonix virtualization notes: https://www.whonix.org/wiki/Dev/Virtualization_Platform
- Tor attack limits: https://support.torproject.org/about-tor/security/attacks-on-onion-routing/
- Tor bridges overview: https://support.torproject.org/en-US/censorship/censorship-7/
- Using Tor bridges: https://support.torproject.org/tor-browser/circumvention/using-bridges/
- Getting Tor bridges: https://support.torproject.org/tor-browser/circumvention/getting-bridges/
- Kicksecure host hardening checklist: https://www.kicksecure.com/wiki/System_Hardening_Checklist

