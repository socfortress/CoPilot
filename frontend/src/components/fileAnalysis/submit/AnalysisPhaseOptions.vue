<template>
	<div class="border-default flex flex-col gap-3 rounded-lg border p-3">
		<span class="text-secondary text-xs font-medium">Analysis phases</span>

		<div class="flex items-center justify-between gap-4">
			<div class="flex flex-col">
				<span class="text-sm">Sandbox detonation (Tier 2)</span>
				<span class="text-secondary text-xs">
					Run the file in the CAPE VM to observe its behaviour. Off = static inspection only.
				</span>
			</div>
			<n-switch :value="sandbox" @update:value="emit('update:sandbox', $event)" />
		</div>

		<div class="flex flex-col gap-1">
			<div class="flex flex-wrap items-center justify-between gap-2">
				<span class="text-sm">VirusTotal</span>
				<n-radio-group :value="vtMode" size="small" @update:value="emit('update:vtMode', $event)">
					<n-radio-button value="off">Off</n-radio-button>
					<n-radio-button value="lookup">Hash lookup</n-radio-button>
					<n-radio-button value="upload">Lookup + upload</n-radio-button>
				</n-radio-group>
			</div>
			<span class="text-secondary text-xs">
				<template v-if="vtMode === 'off'">VirusTotal is skipped entirely — nothing about this file is sent.</template>
				<template v-else-if="vtMode === 'lookup'">
					Checks the file's hash only — the file itself is <b>never uploaded</b>.
				</template>
				<template v-else>
					⚠ Uploads the file if VirusTotal hasn't seen it — this <b>publishes it</b> and can't be undone.
				</template>
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ReputationMode } from "@/types/file-analysis"
import { NRadioButton, NRadioGroup, NSwitch } from "naive-ui"

// Chosen BEFORE analysis and shared by both submission paths (upload and
// endpoint collection), so it lives in the shell rather than in either panel.
// Tier-1 static inspection always runs and is therefore not an option here.
defineProps<{ sandbox: boolean; vtMode: ReputationMode }>()

const emit = defineEmits<{
	(e: "update:sandbox", value: boolean): void
	(e: "update:vtMode", value: ReputationMode): void
}>()
</script>
