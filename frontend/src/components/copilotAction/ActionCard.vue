<template>
	<div class="h-full">
		<CardEntity
			size="small"
			hoverable
			clickable
			:embedded
			class="h-full"
			main-box-class="grow"
			card-entity-wrapper-class="h-full"
			@click.stop="showDetails = true"
		>
			<template #header>
				<p class="text-default min-w-0 text-sm leading-snug font-semibold wrap-break-word">
					{{ action.copilot_action_name }}
				</p>
			</template>

			<template #default>
				<p v-if="action.description" class="text-secondary line-clamp-3 text-xs leading-relaxed">
					{{ action.description }}
				</p>
				<p v-else class="text-secondary text-xs italic">No description available</p>
			</template>

			<template #mainExtra>
				<div class="flex flex-col gap-2">
					<span class="text-secondary text-[10px] font-medium tracking-wider uppercase">Metadata</span>
					<div class="flex flex-wrap items-center gap-1.5">
						<Badge v-if="action.category" size="small">
							<template #value>{{ action.category }}</template>
						</Badge>

						<Badge v-if="action.version" color="primary" type="splitted" size="small">
							<template #label>version</template>
							<template #value>{{ action.version }}</template>
						</Badge>

						<Badge v-if="action.script_parameters.length" color="warning" type="splitted" size="small">
							<template #label>params</template>
							<template #value>{{ action.script_parameters.length }}</template>
						</Badge>

						<Badge v-for="tag of visibleTags" :key="tag" size="small">
							<template #value>{{ tag }}</template>
						</Badge>
						<Badge v-if="hiddenTagCount > 0" size="small">
							<template #value>+{{ hiddenTagCount }}</template>
						</Badge>
					</div>
				</div>
			</template>

			<template #footerMain>
				<TechnologyBadge :action />
			</template>
			<template #footerExtra>
				<div class="flex w-full items-center justify-end">
					<n-button size="small" type="primary" @click.stop="showInvokeModal = true">
						<template #icon>
							<Icon :name="PlayIcon" />
						</template>
						Invoke
					</n-button>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`CoPilot Action: ${action.copilot_action_name}`"
			:bordered="false"
			segmented
		>
			<ActionCardContent :action />
		</n-modal>

		<n-modal
			v-model:show="showInvokeModal"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)' }"
			:bordered="false"
			:title="action.copilot_action_name"
			display-directive="show"
			segmented
		>
			<InvokeActionForm :action @success="handleInvokeSuccess" @close="showInvokeModal = false" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CopilotAction } from "@/types/copilot-action"
import { NButton, NModal, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ActionCardContent from "./ActionCardContent.vue"
import InvokeActionForm from "./InvokeActionForm.vue"
import TechnologyBadge from "./TechnologyBadge.vue"

const { action } = defineProps<{ action: CopilotAction; embedded?: boolean }>()

const showDetails = ref(false)
const showInvokeModal = ref(false)
const message = useMessage()
const PlayIcon = "carbon:play"

const visibleTags = computed(() => action.tags?.slice(0, 2) ?? [])
const hiddenTagCount = computed(() => Math.max((action.tags?.length ?? 0) - 2, 0))

function handleInvokeSuccess() {
	showInvokeModal.value = false
	message.success("Action invoked successfully!")
}
</script>
