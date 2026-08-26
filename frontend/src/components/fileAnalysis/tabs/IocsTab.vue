<template>
	<div class="@container flex flex-col gap-4">
		<div class="flex items-center justify-end">
			<n-button size="small" secondary :disabled="!hasIocs" @click="copyIocs()">
				<template #icon>
					<Icon :name="CopyIcon" />
				</template>
				Copy all IOCs
			</n-button>
		</div>

		<n-empty v-if="!hasIocs" description="No IOCs extracted." class="min-h-52 justify-center" />

		<div v-else class="grid gap-4 @4xl:grid-cols-3">
			<ValueList
				v-for="group of groups"
				:key="group.key"
				:label="group.label"
				:items="group.values"
				:link="group.link"
				max-height="18rem"
				empty-text="— none extracted —"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { InspectorIocs } from "@/types/file-analysis"
import { NButton, NEmpty, useMessage } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import ValueList from "@/components/common/ValueList.vue"

const props = defineProps<{ iocs?: InspectorIocs | null }>()
const message = useMessage()

const CopyIcon = "carbon:copy"

// Indicators link out to VirusTotal, the same affordance the detonation and
// VirusTotal tabs already give: an extracted indicator is something you look up.
const groups = computed(() => [
	{
		key: "urls",
		label: "URLs",
		values: props.iocs?.urls ?? [],
		link: undefined as ((v: string) => string) | undefined
	},
	{
		key: "domains",
		label: "Domains",
		values: props.iocs?.domains ?? [],
		link: (v: string) => `https://www.virustotal.com/gui/domain/${encodeURIComponent(defang(v))}`
	},
	{
		key: "ips",
		label: "IPs",
		values: props.iocs?.ips ?? [],
		link: (v: string) => `https://www.virustotal.com/gui/ip-address/${encodeURIComponent(defang(v))}`
	}
])

/** Indicators are stored defanged (example[.]com); a lookup URL needs them intact. */
function defang(value: string): string {
	return value.replaceAll("[.]", ".").replaceAll("[:]", ":")
}

const hasIocs = computed(() => groups.value.some(g => g.values.length))

/** Copy every extracted indicator, grouped and newline-separated, to the clipboard. */
function copyIocs() {
	const text = groups.value
		.filter(g => g.values.length)
		.map(g => `# ${g.label}\n${g.values.join("\n")}`)
		.join("\n\n")
	navigator.clipboard
		.writeText(text)
		.then(() => message.success("IOCs copied to clipboard."))
		.catch(() => message.error("Could not copy to the clipboard."))
}
</script>
