<template>
	<div class="flex flex-col gap-4">
		<n-empty v-if="!result" description="No metadata yet." class="min-h-52 justify-center" />

		<template v-else>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				<div v-for="row of rows" :key="row.label" class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
					<span class="text-secondary text-xs">{{ row.label }}</span>
					<code class="text-sm break-all">{{ row.value }}</code>
				</div>
			</div>

			<div v-if="result.av?.signature" class="flex items-center gap-2">
				<Icon :name="AvIcon" :size="16" />
				<span class="text-sm">AV signature:</span>
				<n-tag type="error" size="small" round :bordered="false">{{ result.av.signature }}</n-tag>
			</div>

			<!-- FLOSS / extracted strings -->
			<div v-if="result.content?.strings?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">Strings ({{ result.content.strings.length }})</span>
				<n-scrollbar class="bg-secondary max-h-80 rounded-lg p-3">
					<code v-for="(s, i) of result.content.strings" :key="i" class="block text-xs break-all">{{ s }}</code>
				</n-scrollbar>
			</div>

			<!-- PE sections -->
			<n-data-table v-if="result.content?.sections?.length" :columns="sectionColumns" :data="result.content.sections" size="small" />
		</template>
	</div>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { InspectorResult, InspectorSection } from "@/types/file-analysis"
import { NDataTable, NEmpty, NScrollbar, NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ result?: InspectorResult | null }>()

const AvIcon = "carbon:radar"

const rows = computed(() => {
	const r = props.result
	if (!r) return []
	return [
		{ label: "Filename", value: r.filename },
		{ label: "Detected type", value: r.filetype },
		{ label: "Magic", value: r.magic || "—" },
		{ label: "Extension mismatch", value: r.extension_mismatch ? "yes" : "no" },
		{ label: "Entropy", value: String(r.entropy) },
		{ label: "SHA256", value: r.hashes?.sha256 ?? r.sha256 },
		{ label: "MD5", value: r.hashes?.md5 ?? "—" },
		{ label: "Imphash", value: r.hashes?.imphash ?? "—" }
	]
})

const sectionColumns: DataTableColumns<InspectorSection> = [
	{ title: "Section", key: "name" },
	{ title: "Virtual size", key: "vsize" },
	{ title: "Raw size", key: "rawsize" },
	{ title: "Entropy", key: "entropy" }
]
</script>
