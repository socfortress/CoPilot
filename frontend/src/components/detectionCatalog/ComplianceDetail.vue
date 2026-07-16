<template>
	<n-spin :show="loading">
		<div v-if="resolvedGroup" class="flex flex-col gap-4">
			<div v-if="!embedded && resolvedFrameworkLabel" class="flex flex-col gap-1">
				<div class="text-secondary text-xs tracking-wide uppercase">Compliance Control</div>
				<div class="text-default font-mono text-lg leading-tight font-semibold">
					{{ resolvedFrameworkLabel }} {{ resolvedGroup.control }}
				</div>
			</div>

			<div class="flex flex-wrap gap-2">
				<Badge type="splitted" color="primary">
					<template #label>Rules</template>
					<template #value>{{ resolvedGroup.rule_count }}</template>
				</Badge>
				<Badge type="splitted" :color="resolvedGroup.total_hits_30d > 0 ? 'warning' : undefined">
					<template #label>Hits 30d</template>
					<template #value>{{ resolvedGroup.total_hits_30d.toLocaleString() }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Hits 7d</template>
					<template #value>{{ resolvedGroup.total_hits_7d.toLocaleString() }}</template>
				</Badge>
			</div>

			<CardEntity :embedded>
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:list" :size="14" />
						<span class="text-sm font-semibold tracking-wide uppercase">Rule IDs</span>
					</div>
				</template>
				<template #default>
					<div class="flex flex-wrap gap-1.5">
						<n-tag
							v-for="rid of resolvedGroup.rule_ids"
							:key="rid"
							size="small"
							class="hover:bg-primary/10! cursor-pointer!"
							@click="openRuleDetail(rid)"
						>
							{{ rid }}
						</n-tag>
					</div>
				</template>
			</CardEntity>

			<n-modal
				v-model:show="showDetailModal"
				preset="card"
				:style="{ maxWidth: 'min(880px, 94vw)', minHeight: 'min(600px, 90vh)' }"
				:title="modalTitle"
				:bordered="false"
				segmented
			>
				<WazuhRuleDetail v-if="modalRuleId !== null" :rule-id="modalRuleId" />
			</n-modal>
		</div>
	</n-spin>
</template>

<script setup lang="tsx">
import type { CatalogComplianceGroupRow } from "@/types/detection-catalog"
import { NModal, NSpin, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import WazuhRuleDetail from "./WazuhRuleDetail.vue"

const props = withDefaults(
	defineProps<{
		group?: CatalogComplianceGroupRow | null
		framework?: string | null
		control?: string | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: CatalogComplianceGroupRow): void
}>()

const fetchedFrameworkLabel = ref<string | null>(null)

const showDetailModal = ref(false)
const modalTitle = ref("Compliance Control")
const modalRuleId = ref<number | null>(null)

const { loading, entity: resolvedGroup } = useEntityDetails<CatalogComplianceGroupRow, string>({
	entity: () => props.group,
	id: () => (props.framework && props.control ? `${props.framework}|${props.control}` : null),
	fetch: (_id, signal) =>
		Api.detectionCatalog
			.getComplianceGroup(props.framework as string, props.control as string, signal)
			.then(res => {
				if (res.data.success && res.data.group) {
					fetchedFrameworkLabel.value = res.data.framework_label
				}

				return {
					entity: res.data.success ? (res.data.group ?? null) : null,
					message: res.data.message
				}
			}),
	notFoundMessage: "Compliance control not found.",
	errorMessage: "Failed to load compliance control.",
	onLoaded: value => emit("loaded", value)
})

const resolvedFrameworkLabel = computed(() => fetchedFrameworkLabel.value)

watch(
	() => [props.group, props.framework, props.control] as const,
	([group, framework, control]) => {
		if (group || !framework || !control) {
			fetchedFrameworkLabel.value = null
		}
	},
	{ immediate: true }
)

function openRuleDetail(rid: number) {
	modalRuleId.value = rid
	modalTitle.value = `Rule ${rid}`
	showDetailModal.value = true
}

defineExpose({ loading, resolvedGroup, resolvedFrameworkLabel })
</script>
