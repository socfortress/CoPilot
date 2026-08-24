<template>
	<div class="border-default flex flex-col overflow-hidden rounded-lg border">
		<div class="border-default bg-secondary flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
			<span class="text-secondary text-xs font-medium">Analysis pipeline</span>
			<span class="text-secondary text-xs">{{ summary }}</span>
		</div>

		<!-- Tier 1 is shown even though it cannot be turned off: without a row of its
		     own the pipeline reads as "detonation and VirusTotal", and the phase that
		     actually produces the verdict for most files stays invisible. -->
		<div class="phase-row is-active">
			<div class="phase-icon text-primary bg-primary/10">
				<Icon :name="StaticIcon" :size="18" />
			</div>
			<div class="flex min-w-0 grow flex-col gap-0.5">
				<div class="flex flex-wrap items-center gap-2">
					<span class="text-sm font-medium">Static inspection</span>
					<n-tag size="tiny" round :bordered="false" type="primary">Tier 1</n-tag>
				</div>
				<span class="text-secondary text-xs">
					Parsed in a locked-down container — structure, IOCs and ATT&CK behaviours. The file is never executed.
				</span>
			</div>
			<n-tag size="small" round :bordered="false" class="shrink-0">
				<template #icon><Icon :name="LockedIcon" :size="13" /></template>
				Always on
			</n-tag>
		</div>

		<div class="phase-row cursor-pointer" :class="sandbox ? 'is-active' : 'is-off'" @click="toggleSandbox()">
			<div class="phase-icon" :class="sandbox ? 'text-primary bg-primary/10' : 'text-secondary bg-secondary'">
				<Icon :name="SandboxIcon" :size="18" />
			</div>
			<div class="flex min-w-0 grow flex-col gap-0.5">
				<div class="flex flex-wrap items-center gap-2">
					<span class="text-sm font-medium">Sandbox detonation</span>
					<n-tag size="tiny" round :bordered="false" :type="sandbox ? 'primary' : 'default'">Tier 2</n-tag>
				</div>
				<span class="text-secondary text-xs">
					{{
						sandbox
							? "Runs the file in the CAPE VM and records what it actually does."
							: "Off — static inspection only. VM-aware malware stays dormant anyway."
					}}
				</span>
			</div>
			<!-- stop: the row itself toggles, so letting the click through would flip twice -->
			<div class="shrink-0" @click.stop>
				<n-switch :value="sandbox" @update:value="emit('update:sandbox', $event)" />
			</div>
		</div>

		<div class="phase-row flex-wrap" :class="vtRowClass">
			<div class="phase-icon" :class="vtIconClass">
				<Icon :name="VtIcon" :size="18" />
			</div>
			<div class="flex min-w-0 grow flex-col gap-0.5">
				<div class="flex flex-wrap items-center gap-2">
					<span class="text-sm font-medium">VirusTotal</span>
					<n-tag v-if="vtMode === 'upload'" size="tiny" round :bordered="false" type="error">
						publishes the file
					</n-tag>
				</div>
				<span class="text-xs" :class="vtMode === 'upload' ? 'text-error' : 'text-secondary'">
					<template v-if="vtMode === 'off'">Skipped entirely — nothing about this file is sent.</template>
					<template v-else-if="vtMode === 'lookup'">
						Checks the file's hash only — the file itself is
						<b>never uploaded</b>
					</template>
					<template v-else>
						Uploads the file if VirusTotal hasn't seen it — this publishes it and
						<b>cannot be undone</b>
					</template>
				</span>
			</div>
			<n-radio-group
				:value="vtMode"
				size="small"
				class="shrink-0"
				@update:value="emit('update:vtMode', $event)"
			>
				<n-radio-button value="off">Off</n-radio-button>
				<n-radio-button value="lookup">Hash lookup</n-radio-button>
				<n-radio-button value="upload">Lookup + upload</n-radio-button>
			</n-radio-group>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ReputationMode } from "@/types/file-analysis"
import { NRadioButton, NRadioGroup, NSwitch, NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

// Chosen BEFORE analysis and shared by both submission paths (upload and
// endpoint collection), so it lives in the shell rather than in either panel.
const props = defineProps<{ sandbox: boolean; vtMode: ReputationMode }>()

const emit = defineEmits<{
	(e: "update:sandbox", value: boolean): void
	(e: "update:vtMode", value: ReputationMode): void
}>()

const StaticIcon = "carbon:document-security"
const SandboxIcon = "carbon:chemistry"
const VtIcon = "carbon:radar"
const LockedIcon = "carbon:locked"

// One line answering "what happens when I press analyze", so the plan survives
// a glance without reading three rows.
const summary = computed(() => {
	const steps = ["Static"]
	if (props.sandbox) steps.push("Detonation")
	if (props.vtMode === "lookup") steps.push("VT hash lookup")
	if (props.vtMode === "upload") steps.push("VT lookup + upload")
	return steps.join("  →  ")
})

// Upload mode is the only irreversible choice on this panel, so it must not look
// like every other active phase. It takes the ERROR accent rather than warning:
// this theme's warning (rgb 227,194,47) is a near-twin of its primary
// (rgb 255,182,0), so a warning tint reads as "enabled", not as "careful".
const vtRowClass = computed(() => {
	if (props.vtMode === "upload") return "is-danger"
	return props.vtMode === "off" ? "is-off" : "is-active"
})

const vtIconClass = computed(() => {
	if (props.vtMode === "upload") return "text-error bg-error/10"
	return props.vtMode === "off" ? "text-secondary bg-secondary" : "text-primary bg-primary/10"
})

function toggleSandbox() {
	emit("update:sandbox", !props.sandbox)
}
</script>

<style scoped lang="scss">
.phase-row {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	padding: 0.75rem;
	// The left rule is the at-a-glance "is this phase in the plan" signal; it is
	// transparent rather than absent so enabling a phase doesn't shift the layout.
	box-shadow: inset 3px 0 0 0 transparent;
	transition:
		box-shadow 0.2s ease,
		background-color 0.2s ease;

	// Only between rows — the header already draws the first divider.
	& + .phase-row {
		border-top: 1px solid var(--border-color);
	}

	&.is-active {
		box-shadow: inset 3px 0 0 0 var(--primary-color);
	}

	&.is-danger {
		box-shadow: inset 3px 0 0 0 var(--error-color);
		background-color: color-mix(in srgb, var(--error-color) 6%, transparent);
	}

	&.is-off {
		opacity: 0.75;
	}

	&.cursor-pointer:hover {
		background-color: var(--hover-005-color);
	}
}

.phase-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	width: 2rem;
	height: 2rem;
	border-radius: 0.5rem;
}
</style>
