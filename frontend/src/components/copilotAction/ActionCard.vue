<template>
	<div class="h-full">
		<CardEntity
			hoverable
			clickable
			:embedded
			class="@ h-full"
			main-box-class="grow"
			card-entity-wrapper-class="h-full"
			header-box-class="flex-nowrap! items-start"
			@click.stop="showDetails = true"
		>
			<template #headerMain>{{ action.copilot_action_name }}</template>
			<template #headerExtra>
				<TechnologyBadge :action />
			</template>
			<template #default>
				<div class="line-clamp-3 text-sm">
					{{ action.description }}
				</div>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge v-if="action.category">
						<template #value>{{ action.category }}</template>
					</Badge>

					<Badge v-if="action.version" color="primary" type="splitted">
						<template #label>version</template>
						<template #value>{{ action.version }}</template>
					</Badge>

					<Badge v-if="action.script_parameters.length" color="warning" type="splitted">
						<template #label>params</template>
						<template #value>{{ action.script_parameters.length }}</template>
					</Badge>

					<div v-if="action.tags?.length" class="flex items-center gap-1">
						<Badge v-for="tag of action.tags.slice(0, 2)" :key="tag" size="small">
							<template #value>{{ tag }}</template>
						</Badge>
						<Badge v-if="action.tags.length > 2" size="small">
							<template #value>+{{ action.tags.length - 2 }}</template>
						</Badge>
					</div>
				</div>
			</template>
			<template #footerExtra>
				<n-button size="small" type="primary" secondary @click.stop="showInvokeModal = true">
					<template #icon>
						<Icon :name="PlayIcon"></Icon>
					</template>
					Invoke
				</n-button>
			</template>
		</CardEntity>

		<!-- Action Details Modal -->
		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`CoPilot Action: ${action.copilot_action_name}`"
			:bordered="false"
			segmented
		>
			<ActionCardContent :action="action" />
		</n-modal>

		<!-- Invoke Action Modal -->
		<n-modal
			v-model:show="showInvokeModal"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)' }"
			:title="`Invoke: ${action.copilot_action_name}`"
			:bordered="false"
			segmented
		>
			<InvokeActionForm :action="action" @success="handleInvokeSuccess" @close="showInvokeModal = false" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ActiveResponseItem } from "@/types/copilotAction.d"
import { NButton, NModal, useMessage } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ActionCardContent from "./ActionCardContent.vue"
import InvokeActionForm from "./InvokeActionForm.vue"
import TechnologyBadge from "./TechnologyBadge.vue"

const { action } = defineProps<{ action: ActiveResponseItem; embedded?: boolean }>()

const showDetails = ref(false)
const showInvokeModal = ref(false)
const message = useMessage()
const PlayIcon = "carbon:play"

function handleInvokeSuccess() {
	showInvokeModal.value = false
	message.success("Action invoked successfully!")
}
</script>
