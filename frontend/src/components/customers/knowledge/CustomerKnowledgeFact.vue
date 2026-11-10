<template>
	<CardEntity v-if="!compact" embedded size="small" data-testid="knowledge-fact">
		<template #headerMain>
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-default font-medium break-all" data-testid="knowledge-fact-headline">
					{{ view.headline }}
				</span>
				<n-tag v-if="view.crownJewel" size="small" type="error" :bordered="false">Crown jewel</n-tag>
				<n-tag v-if="fact.expired" size="small" type="warning" :bordered="false" data-testid="knowledge-fact-expired">
					Expired
				</n-tag>
			</div>
		</template>

		<template #default>
			<div class="flex flex-col gap-1 text-sm">
				<div v-for="detail of view.details" :key="detail.label" class="flex flex-wrap gap-1">
					<span class="font-medium">{{ detail.label }}:</span>
					<code v-for="value of detail.values" :key="value">{{ value }}</code>
				</div>
				<p v-if="fact.note" class="text-secondary m-0 break-words" data-testid="knowledge-fact-note">
					{{ fact.note }}
				</p>
			</div>
		</template>

		<template #footerMain>
			<span v-if="changed" class="text-secondary text-xs" data-testid="knowledge-fact-changed">{{ changed }}</span>
		</template>

		<template #footerExtra>
			<CustomerKnowledgeFactActions :deleting @edit="emit('edit')" @delete="remove()" />
		</template>
	</CardEntity>

	<!-- Compact: one row. Who changed it last is the row's tooltip; the note is cut to the row, whole in its own. -->
	<div v-else class="knowledge-fact-row" :title="changed ?? undefined" data-testid="knowledge-fact">
		<span class="text-default font-medium break-all" data-testid="knowledge-fact-headline">{{ view.headline }}</span>
		<n-tag v-if="view.crownJewel" size="tiny" type="error" :bordered="false">Crown jewel</n-tag>
		<n-tag v-if="fact.expired" size="tiny" type="warning" :bordered="false" data-testid="knowledge-fact-expired">
			Expired
		</n-tag>
		<span v-for="detail of view.details" :key="detail.label" class="knowledge-fact-detail">
			<span class="text-secondary">{{ detail.label }}</span>
			<code v-for="value of detail.values" :key="value">{{ value }}</code>
		</span>
		<span v-if="fact.note" class="knowledge-fact-note" :title="fact.note" data-testid="knowledge-fact-note">
			{{ fact.note }}
		</span>
		<CustomerKnowledgeFactActions compact class="ml-auto" :deleting @edit="emit('edit')" @delete="remove()" />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { KnowledgeItem } from "@/types/customer-knowledge"
import { NTag, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CustomerKnowledgeFactActions from "./CustomerKnowledgeFactActions.vue"
import { factView, lastChanged } from "./knowledge"

const {
	fact,
	customerCode,
	compact = false
} = defineProps<{
	fact: KnowledgeItem
	customerCode: string
	/** One row instead of a card (the pane's Compact choice). */
	compact?: boolean
}>()

const emit = defineEmits<{
	(e: "edit"): void
	(e: "deleted"): void
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const deleting = ref(false)

function when(moment: string): string {
	return String(formatDate(moment, dFormats.datetime))
}

const view = computed(() => factView(fact, when))
const changed = computed(() => lastChanged(fact, when))

async function remove() {
	deleting.value = true
	try {
		const res = await Api.customerKnowledge.remove(customerCode, fact.id)
		if (res.data.success) {
			message.success("Fact deleted")
			emit("deleted")
		} else {
			message.warning(res.data.message || "Couldn't delete this fact")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Couldn't delete this fact")
	} finally {
		deleting.value = false
	}
}
</script>

<style lang="scss" scoped>
.knowledge-fact-row {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	column-gap: 12px;
	row-gap: 4px;
	min-height: 40px;
	padding: 4px 8px 4px 12px;
	font-size: 13px;

	&:hover {
		background-color: var(--hover-color);
	}
}

.knowledge-fact-detail {
	display: inline-flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 4px;
}

.knowledge-fact-note {
	flex: 1 1 160px;
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--fg-secondary-color);
}
</style>
