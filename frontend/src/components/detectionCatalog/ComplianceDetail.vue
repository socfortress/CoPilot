<template>
	<div v-if="group" class="flex flex-col gap-4">
		<div class="flex flex-wrap gap-2">
			<Badge type="splitted" color="primary">
				<template #label>Rules</template>
				<template #value>{{ group.rule_count }}</template>
			</Badge>
			<Badge type="splitted" :color="group.total_hits_30d > 0 ? 'warning' : undefined">
				<template #label>Hits 30d</template>
				<template #value>{{ group.total_hits_30d.toLocaleString() }}</template>
			</Badge>
			<Badge type="splitted">
				<template #label>Hits 7d</template>
				<template #value>{{ group.total_hits_7d.toLocaleString() }}</template>
			</Badge>
		</div>

		<CardEntity>
			<template #headerMain>
				<div class="flex items-center gap-2">
					<Icon name="carbon:list" :size="14" />
					<span class="text-sm font-semibold tracking-wide uppercase">Rule IDs</span>
				</div>
			</template>
			<template #default>
				<div class="flex flex-wrap gap-1.5">
					<n-tag
						v-for="rid of group.rule_ids"
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

		<!-- Detail modal -->
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
</template>

<script setup lang="tsx">
import type { CatalogComplianceGroupRow } from "@/types/detectionCatalog"
import { NModal, NTag } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import WazuhRuleDetail from "./WazuhRuleDetail.vue"

defineProps<{ group: CatalogComplianceGroupRow }>()

const showDetailModal = ref(false)
const modalTitle = ref("Compliance Control")
const modalRuleId = ref<number | null>(null)

function openRuleDetail(rid: number) {
	modalRuleId.value = rid
	modalTitle.value = `Rule ${rid}`
	showDetailModal.value = true
}
</script>
