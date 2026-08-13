<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-end">
			<n-button size="small" secondary :disabled="!hasIocs" @click="copyIocs()">
				<template #icon>
					<Icon :name="CopyIcon" />
				</template>
				Copy all IOCs
			</n-button>
		</div>

		<n-empty v-if="!hasIocs" description="No IOCs extracted." class="min-h-52 justify-center" />

		<div v-else class="grid gap-4 md:grid-cols-3">
			<div v-for="group of groups" :key="group.key" class="flex flex-col gap-2">
				<div class="flex items-center gap-2">
					<Icon :name="group.icon" :size="16" />
					<span class="text-sm font-medium">{{ group.label }}</span>
					<n-tag size="tiny" round :bordered="false">{{ group.values.length }}</n-tag>
				</div>
				<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
					<code v-for="v of group.values" :key="v" class="text-xs break-all">{{ v }}</code>
					<span v-if="!group.values.length" class="text-secondary text-xs">—</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { InspectorIocs } from "@/types/file-analysis"
import { NButton, NEmpty, NTag, useMessage } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ iocs?: InspectorIocs | null }>()
const message = useMessage()

const CopyIcon = "carbon:copy"

const groups = computed(() => [
	{ key: "urls", label: "URLs", icon: "carbon:link", values: props.iocs?.urls ?? [] },
	{ key: "domains", label: "Domains", icon: "carbon:web-services-container", values: props.iocs?.domains ?? [] },
	{ key: "ips", label: "IPs", icon: "carbon:ibm-cloud-internet-services", values: props.iocs?.ips ?? [] }
])

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
