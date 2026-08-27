# CAPEv2 dev setup — Linux host + Linux guest, wired into CoPilot

Goal: stand up a **dev** CAPEv2 on one Linux VM, using a **Linux analysis guest**
(no Windows), and point CoPilot's `remote` sandbox backend at it. Enough to
validate real detonation of ELF/shell samples end-to-end.

> Reference: https://capev2.readthedocs.io/  (kevoreilly/CAPEv2)
> Everything below runs ON THE CAPE LINUX VM unless it says "on CoPilot".

---

## 0. Prerequisites — nested virtualization must work

CAPE runs the sample inside a **guest VM**, so your CAPE VM needs KVM available.

```bash
sudo apt update && sudo apt install -y cpu-checker
egrep -c '(vmx|svm)' /proc/cpuinfo     # must be > 0
kvm-ok                                  # must say "KVM acceleration can be used"
ls -l /dev/kvm                          # must exist
```

If `/dev/kvm` is missing and this VM is itself a guest, **enable nested virt on the
parent hypervisor** and reboot the VM:
- Proxmox: set the VM CPU type to `host`.
- ESXi/vSphere: "Expose hardware assisted virtualization to the guest OS".
- KVM parent: `modprobe kvm_intel nested=1` (or `kvm_amd`).
- VirtualBox: `VBoxManage modifyvm <vm> --nested-hw-virt on`.

Do NOT continue until `kvm-ok` passes — nothing else will work.

---

## 1. KVM / QEMU / libvirt

```bash
sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients \
                    bridge-utils virtinst virt-manager
sudo systemctl enable --now libvirtd
virsh list --all                        # should return (empty) table, no error
virsh net-list --all                    # 'default' network should exist
sudo virsh net-start default 2>/dev/null; sudo virsh net-autostart default
```

The `default` libvirt network gives you `virbr0` at `192.168.122.1`, DHCP range
`192.168.122.2-254`. We'll give the guest a static IP in that range.

---

## 2. Install CAPEv2 (automated installer)

```bash
cd /opt
sudo git clone https://github.com/kevoreilly/CAPEv2.git
cd CAPEv2/installer          # cape2.sh lives here (or repo root, check with: find /opt/CAPEv2 -name cape2.sh)
sudo chmod a+x cape2.sh
./cape2.sh -h                # review options

# Base install (creates the 'cape' user, poetry env, postgres, yara, systemd units):
sudo ./cape2.sh base cape | tee /tmp/cape.log
sudo reboot
```

After reboot, everything CAPE runs as the **cape** user under `/opt/CAPEv2`:

```bash
sudo su - cape -c /bin/bash
cd /opt/CAPEv2
poetry env list              # confirm the venv exists
```

Installer creates systemd services: `cape.service`, `cape-processor.service`,
`cape-web.service`, `cape-rooter.service`.

---

## 3. Build the Linux analysis guest

Create a small Ubuntu guest that CAPE will boot, run the sample in, then restore.

```bash
# On the CAPE host — create the guest (adjust ISO path / resources):
sudo virt-install \
  --name cape1 \
  --ram 2048 --vcpus 2 \
  --disk path=/var/lib/libvirt/images/cape1.qcow2,size=20 \
  --os-variant ubuntu22.04 \
  --network network=default \
  --graphics vnc \
  --cdrom /var/lib/libvirt/iso/ubuntu-22.04.iso
```

Inside the guest (via virt-manager console):
1. Install Ubuntu (minimal). Create a user, note credentials.
2. **Static IP** `192.168.122.50` (matches kvm.conf below).
3. Install Python + the CAPE agent:
   ```bash
   sudo apt install -y python3 python3-pip
   # copy agent from host: /opt/CAPEv2/agent/agent.py  ->  guest:/root/agent.py
   ```
4. Make `agent.py` run at boot (listens on tcp/8000 for the CAPE host):
   ```bash
   # /etc/systemd/system/cape-agent.service
   [Unit]
   After=network.target
   [Service]
   ExecStart=/usr/bin/python3 /root/agent.py
   Restart=always
   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl enable --now cape-agent
   ```
5. Disable auto-updates / anything that phones home. Reboot once, confirm the
   agent is listening: from the host `nc -vz 192.168.122.50 8000`.
6. **Snapshot the clean state** (guest running, agent up):
   ```bash
   sudo virsh snapshot-create-as cape1 clean "clean baseline"
   ```

---

## 4. Tell CAPE about the guest

As the **cape** user, edit configs in `/opt/CAPEv2/conf/`:

`cuckoo.conf`:
```ini
[cuckoo]
machinery = kvm
[resultserver]
ip = 192.168.122.1        # the host's virbr0 address
port = 2042
```

`kvm.conf`:
```ini
[kvm]
machines = cape1
interface = virbr0

[cape1]
label = cape1             # libvirt domain name (virsh list)
platform = linux          # LINUX guest
ip = 192.168.122.50       # the guest's static IP
snapshot = clean          # the snapshot from step 3.6
tags = linux,x64
```

---

## 5. Network isolation (the safety gate)

For **dev with benign samples**, the simplest safe default is *no* guest internet.
In `/opt/CAPEv2/conf/routing.conf`:
```ini
[routing]
route = none              # guest gets NO internet by default
internet = none
```
`cape-rooter.service` (runs as root) applies the iptables rules. For fake network
services (DNS/HTTP sinkholes) install **inetsim** and set `[inetsim] enabled = yes`
— do this before you ever run a non-benign sample.

**Verify isolation before any real sample:** from inside the guest, confirm it
canNOT reach the internet (`curl -m5 https://1.1.1.1` should fail/time out).

---

## 6. Enable the REST API + token

```bash
cd /opt/CAPEv2/web
sudo -u cape poetry run pip install djangorestframework
sudo -u cape poetry run python3 manage.py createsuperuser        # make an admin user
sudo -u cape poetry run python3 manage.py drf_create_token <user># prints the TOKEN — save it
```

In `/opt/CAPEv2/conf/api.conf`:
```ini
[api]
token_auth_enabled = yes
ratelimit = no
```

---

## 7. Start services + health check

```bash
sudo systemctl restart cape-rooter cape cape-processor cape-web
systemctl status cape cape-web --no-pager
journalctl -u cape -n 50 --no-pager        # watch for the KVM machine registering

# Local health check with your token:
curl -H "Authorization: Token <TOKEN>" http://127.0.0.1:8000/apiv2/cuckoo/status/
# Expect JSON with machines/analysis info (HTTP 200).
```

Make sure the API is reachable from the CoPilot VM (firewall/security group must
allow the CoPilot VM to hit `<CAPE_VM_IP>:8000`).

---

## 8. Connect it in CoPilot's env

On the **CoPilot** host, add to `.env` (only once step 7's health check passes):
```ini
SANDBOX_BACKEND=remote
CAPE_API_URL=http://<CAPE_VM_IP>:8000/apiv2
CAPE_API_TOKEN=<TOKEN>
# optional tuning:
CAPE_TASK_TIMEOUT=120
CAPE_POLL_INTERVAL=15
CAPE_POLL_TIMEOUT=1800
```
Restart the CoPilot backend. `get_backend()` now returns `CapeBackend`; on the next
analysis of an escalation-worthy file (`pe`/`elf`/`script`, or a suspicious flag)
the pipeline will submit → poll → report → summarize, and the **Detonation /
Network** tabs will populate.

---

## 9. Validate end-to-end

- From the CoPilot VM: `curl -H "Authorization: Token <TOKEN>" http://<CAPE_VM_IP>:8000/apiv2/cuckoo/status/` → 200.
- In CoPilot, analyze a benign **ELF** or shell script (Linux guest can detonate it).
- Watch: job shows `sandbox_enabled=true`, dynamic status runs, then the Detonation
  tab shows the CAPE summary (signatures, network, dropped).

---

## Notes / gotchas
- Guest platform is **linux** here, so you can only detonate Linux samples. Add a
  Windows guest later (another `[machine]` block with `platform = windows`) for PE/Office.
- If `cuckoo status` shows 0 machines, the guest/libvirt/snapshot names in `kvm.conf`
  don't match `virsh list` — fix the `label`/`snapshot`.
- `cape-rooter` must be running (as root) or routing/isolation won't apply.
- The CoPilot↔CAPE link is REST only — no Wazuh/Velociraptor agent needed on the
  CAPE host (optional if you want to monitor the host itself).
