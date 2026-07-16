<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedGap" :embedded>
			<template #headerMain>
				<div class="flex flex-col gap-1">
					<div class="text-secondary text-xs tracking-wide uppercase">MITRE ATT&amp;CK Gap</div>
					<div class="text-default font-mono text-lg leading-tight font-semibold">
						{{ resolvedGap.technique_id }}
					</div>
				</div>
			</template>

			<template #default>
				<div class="flex flex-col gap-4">
					<p class="text-default text-base leading-snug font-medium">
						{{ resolvedGap.technique_name }}
					</p>

					<div v-if="resolvedGap.tactics.length" class="flex flex-wrap gap-1.5">
						<n-tag v-for="tactic of resolvedGap.tactics" :key="tactic" type="warning" size="small">
							{{ tactic.toUpperCase() }}
						</n-tag>
					</div>
					<p v-else class="text-secondary text-sm">No tactics mapped for this technique.</p>

					<n-button
						v-if="resolvedGap.url"
						tag="a"
						:href="resolvedGap.url"
						target="_blank"
						rel="noopener"
						size="small"
						type="primary"
						secondary
					>
						<template #icon>
							<Icon name="carbon:launch" :size="12" />
						</template>
						View on MITRE ATT&amp;CK
					</n-button>
				</div>
			</template>
		</CardEntity>
	</n-spin>
</template>

<script setup lang="ts">
import type { CatalogCoverageGapRow } from "@/types/detection-catalog"
import { NButton, NSpin, NTag } from "naive-ui"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"

const props = withDefaults(
	defineProps<{
		gap?: CatalogCoverageGapRow | null
		techniqueId?: string | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: CatalogCoverageGapRow): void
}>()

const { loading, entity: resolvedGap } = useEntityDetails<CatalogCoverageGapRow, string>({
	entity: () => props.gap,
	id: () => props.techniqueId || null,
	fetch: (id, signal) =>
		Api.detectionCatalog.getCoverageGap(id, signal).then(res => ({
			entity: res.data.success ? (res.data.gap ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Coverage gap not found.",
	errorMessage: "Failed to load coverage gap.",
	onLoaded: value => emit("loaded", value)
})

defineExpose({ loading, resolvedGap })
</script>
