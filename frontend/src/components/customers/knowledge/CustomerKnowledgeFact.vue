<template>
	<CardEntity embedded size="small" data-testid="knowledge-fact">
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
			<div class="flex items-center justify-end gap-2">
				<n-button size="tiny" quaternary data-testid="knowledge-fact-edit" @click="emit('edit')">
					<template #icon>
						<Icon :name="EditIcon" :size="14" />
					</template>
					Edit
				</n-button>

				<n-popconfirm to="body" @positive-click="remove">
					<template #trigger>
						<n-button size="tiny" quaternary :loading="deleting" data-testid="knowledge-fact-delete">
							<template #icon>
								<Icon :name="DeleteIcon" :size="14" />
							</template>
							Delete
						</n-button>
					</template>
					Delete this fact? talon-analyst stops reading it. The audit log keeps what it held.
				</n-popconfirm>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { KnowledgeItem } from "@/types/customer-knowledge"
import { NButton, NPopconfirm, NTag, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { factView, lastChanged } from "./knowledge"

const { fact, customerCode } = defineProps<{
	fact: KnowledgeItem
	customerCode: string
}>()

const emit = defineEmits<{
	(e: "edit"): void
	(e: "deleted"): void
}>()

const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"

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
