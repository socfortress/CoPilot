<template>
	<div class="@container flex flex-col gap-4">
		<n-empty v-if="!result" description="No metadata yet." class="min-h-52 justify-center" />

		<template v-else>
			<!-- Each fact is a card in the module's shared chrome, but not collapsible:
			     a single value has nothing worth folding away, and a chevron on eight
			     one-line cards would be eight controls that do nothing useful. -->
			<div class="grid gap-3 @2xl:grid-cols-2 @4xl:grid-cols-3">
				<CollapsibleCard v-for="row of rows" :key="row.label" :collapsible="false">
					<template #header>
						<span :class="SECTION_LABEL">{{ row.label }}</span>
					</template>
					<div class="p-3">
						<span class="text-default font-mono text-sm break-all">{{ row.value }}</span>
					</div>
				</CollapsibleCard>
			</div>

			<div v-if="result.av?.signature" class="flex items-center gap-2">
				<Icon :name="AvIcon" :size="16" />
				<span class="text-sm">AV signature:</span>
				<n-tag type="error" size="small" round :bordered="false">{{ result.av.signature }}</n-tag>
			</div>

			<!-- FLOSS / extracted strings -->
			<ValueList
				v-if="result.content?.strings?.length"
				label="Strings"
				:items="result.content.strings"
				max-height="20rem"
			/>

			<!-- PE sections -->
			<n-data-table
				v-if="result.content?.sections?.length"
				:columns="sectionColumns"
				:data="result.content.sections"
				size="small"
			/>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { InspectorResult, InspectorSection } from "@/types/file-analysis"
import { NDataTable, NEmpty, NTag } from "naive-ui"
import { computed } from "vue"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import ValueList from "@/components/common/ValueList.vue"

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
