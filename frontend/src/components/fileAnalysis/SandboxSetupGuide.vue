<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info" :bordered="false" class="text-sm">
			<template #header>Detonation is optional — static inspection works without any of this</template>
			File Analysis ships with <code>SANDBOX_BACKEND=none</code>. Tier 1 (static inspection) runs in a locked-down
			container on the CoPilot host and needs no extra hardware. Follow this guide only if you want Tier 2 — real
			detonation in a VM via <b>CAPEv2</b>.
		</n-alert>

		<!-- Only assert connectivity when we actually know it (a job carries the flag);
		     on the landing page the state is unknown, so we claim nothing. -->
		<n-alert v-if="sandboxEnabled === false" type="warning" :bordered="false" class="text-sm">
			<template #header>Sandbox not reachable for this analysis</template>
			CoPilot couldn't reach a CAPE backend, so the Detonation / Network tabs stay empty. That's
			expected until you finish the steps below.
		</n-alert>
		<n-alert v-else-if="sandboxEnabled === true" type="success" :bordered="false" class="text-sm">
			<template #header>Sandbox connected</template>
			CoPilot is talking to a CAPE backend — escalated samples will detonate.
		</n-alert>

		<n-collapse :default-expanded-names="['host']" accordion>
			<!-- 1 -->
			<n-collapse-item name="host" title="1. Host requirements">
				<div class="flex flex-col gap-2 text-sm">
					<p>
						CAPE runs guests under KVM, so the machine must expose hardware virtualization. A <b>bare-metal</b>
						host is strongly preferred — nested virtualization inside a cloud VM is often unavailable or slow.
					</p>
					<CodeBlock title="Verify virtualization is available (expect a non-zero count)" :code="checkVirt" />
					<p class="text-secondary text-xs">
						Reference build: Ubuntu 22.04, AMD Ryzen bare metal, KVM/libvirt. Windows hosts and Hyper-V/WSL2
						will block KVM — use a dedicated Linux box.
					</p>
				</div>
			</n-collapse-item>

			<!-- 2 -->
			<n-collapse-item name="install" title="2. Install CAPEv2">
				<div class="flex flex-col gap-3 text-sm">
					<CodeBlock title="Install (takes a while; keep the log)" :code="installCape" />
					<n-alert type="warning" :bordered="false" class="text-xs">
						<template #header>Three gotchas that will otherwise cost you hours</template>
						<ul class="ml-4 list-disc">
							<li>
								<b>libvirt-python is not installed into the poetry venv</b> by <code>cape2.sh base</code> —
								the <code>cape</code> service dies with <code>No module named 'libvirt'</code>. The pip
								version must match the system libvirt exactly.
							</li>
							<li>
								<b>API endpoints ship disabled.</b> Enable <code>cuckoostatus</code> (CoPilot's health
								check) and turn on token auth, or every call 401s / rate-limits.
							</li>
							<li>
								<b>Linux binary analysis is off by default</b> — every ELF/script submit is rejected with
								"Linux binaries analysis isn't enabled".
							</li>
						</ul>
					</n-alert>
					<CodeBlock title="Fix libvirt-python (match the system libvirt version)" :code="fixLibvirt" />
					<CodeBlock title="conf/api.conf + conf/web.conf edits" :code="capeConf" />
				</div>
			</n-collapse-item>

			<!-- 3 -->
			<n-collapse-item name="token" title="3. Create the API token CoPilot will use">
				<div class="flex flex-col gap-2 text-sm">
					<CodeBlock title="Create a user and mint a DRF token" :code="apiToken" />
					<p class="text-secondary text-xs">
						Copy the token — it becomes <code>CAPE_API_TOKEN</code> in step 5.
					</p>
				</div>
			</n-collapse-item>

			<!-- 4 -->
			<n-collapse-item name="guests" title="4. Build the analysis guests">
				<div class="flex flex-col gap-3 text-sm">
					<p>
						Each guest runs the CAPE agent and must be reachable from the host on the analysis bridge
						(default <code>virbr0</code>, <code>192.168.122.0/24</code>). Register them in
						<code>conf/kvm.conf</code>.
					</p>
					<div>
						<p class="font-medium">Linux guest</p>
						<p class="text-secondary text-xs">
							Ubuntu cloud image, headless. Run <code>/opt/CAPEv2/agent/agent.py</code> as a systemd unit.
							BIOS/SeaBIOS guests support internal snapshots, so <code>virsh snapshot-create-as</code>
							just works.
						</p>
					</div>
					<div>
						<p class="font-medium">Windows guest</p>
						<p class="text-secondary text-xs">
							Windows 10/11 (<code>mido</code> fetches an official evaluation ISO). Start the agent via an
							<code>HKCU\…\Run</code> key with <code>pythonw agent.py</code>, enable auto-logon, and disable
							Defender + Tamper Protection + Firewall + Update + UAC + SmartScreen so they don't perturb the
							analysis.
						</p>
					</div>
					<n-alert type="warning" :bordered="false" class="text-xs">
						<template #header>Snapshots: the part that bites on Windows 11</template>
						CAPE reverts to a snapshot between runs. Win11 requires UEFI, and <b>internal snapshots of
						pflash/UEFI VMs are unsupported</b>; reverting <i>external</i> snapshots needs libvirt ≥ 9.10
						(Ubuntu 22.04 ships 8.0). Options: build the guest as Win10 in <b>BIOS</b> mode (internal
						snapshots work), or host on Ubuntu 24.04 (libvirt 10 → external memory snapshots). Without a
						snapshot the guest cannot auto-reset between runs — acceptable for benign testing only.
					</n-alert>
					<CodeBlock title="Register guests in conf/kvm.conf" :code="kvmConf" />
				</div>
			</n-collapse-item>

			<!-- 5 -->
			<n-collapse-item name="wire" title="5. Point CoPilot at CAPE">
				<div class="flex flex-col gap-2 text-sm">
					<CodeBlock title="Add to CoPilot's .env, then restart the backend" :code="envWiring" />
					<p class="text-secondary text-xs">
						On restart the Detonation / Network tabs activate and this page flips to
						"Sandbox connected". Verify with
						<code>GET {{ '{CAPE_API_URL}' }}/cuckoo/status/</code>.
					</p>
				</div>
			</n-collapse-item>

			<!-- 6 -->
			<n-collapse-item name="safety" title="6. Network isolation — required before real malware">
				<div class="flex flex-col gap-2 text-sm">
					<n-alert type="error" :bordered="false" class="text-sm">
						<template #header>Do not detonate real malware until this is done</template>
						A detonating sample executes with whatever network it is given. Until the guest is isolated and
						the CAPE host is firewalled, restrict yourself to <b>benign test files</b>.
					</n-alert>
					<ul class="ml-4 list-disc text-sm">
						<li>
							Set <code>route = none</code> in <code>conf/routing.conf</code> so guests get no egress by
							default (per-task routing can be granted deliberately).
						</li>
						<li>
							Firewall the CAPE host: expose <code>:8000</code> only to the CoPilot backend's IP — never
							the public internet. The API and the VNC console are unauthenticated surfaces.
						</li>
						<li>Put the analysis bridge on its own VLAN with no route to production networks.</li>
						<li>Verify with a benign beacon: confirm the callout is captured and nothing escapes.</li>
					</ul>
				</div>
			</n-collapse-item>
		</n-collapse>
	</div>
</template>

<script setup lang="ts">
import { NAlert, NCollapse, NCollapseItem } from "naive-ui"
import CodeBlock from "@/components/fileAnalysis/CodeBlock.vue"

defineProps<{ sandboxEnabled?: boolean | null }>()

const checkVirt = `egrep -c '(vmx|svm)' /proc/cpuinfo   # 0 means no virtualization available
kvm-ok                                  # "KVM acceleration can be used"`

const installCape = `git clone https://github.com/kevoreilly/CAPEv2 /opt/CAPEv2
cd /opt/CAPEv2/installer
./cape2.sh base cape 2>&1 | tee cape-install.log

# services created: cape, cape-web, cape-processor, cape-rooter
systemctl status cape cape-web --no-pager`

const fixLibvirt = `apt install -y libvirt-dev
sudo -u cape /etc/poetry/bin/poetry -C /opt/CAPEv2 run \\
  pip install "libvirt-python==$(virsh --version)"
systemctl restart cape`

const capeConf = `# /opt/CAPEv2/conf/api.conf
[cuckoostatus]
enabled = yes          # CoPilot's health check hits /cuckoo/status/

[api]
token_auth_enabled = yes
ratelimit = no

# /opt/CAPEv2/conf/web.conf
[linux]
enabled = yes          # otherwise every ELF/script submit is rejected`

const apiToken = `cd /opt/CAPEv2/web
poetry run python manage.py createsuperuser
poetry run python manage.py drf_create_token <username>   # prints the token`

const kvmConf = `# /opt/CAPEv2/conf/kvm.conf
[kvm]
machines = guest_linux,guest_windows

[guest_linux]
label = guest_linux
platform = linux
ip = 192.168.122.50
snapshot = clean
tags = linux,x64

[guest_windows]
label = guest_windows
platform = windows
ip = 192.168.122.88
snapshot = clean
arch = x64
tags = windows,x64`

const envWiring = `SANDBOX_BACKEND=remote
CAPE_API_URL=http://<cape-host>:8000/apiv2
CAPE_API_TOKEN=<token from step 3>
CAPE_TASK_TIMEOUT=120
CAPE_POLL_INTERVAL=15
CAPE_POLL_TIMEOUT=1800`

</script>
