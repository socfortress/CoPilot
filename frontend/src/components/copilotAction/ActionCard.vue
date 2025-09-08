<template>
	<div class="action-card h-full">
		<CardEntity hoverable clickable :embedded class="@container h-full flex flex-col" @click.stop="showDetails = true">
			<template #headerMain>{{ action.copilot_action_name }}</template>
			<template #headerExtra>
				<Badge :color="getTechnologyColor(action.technology)">
					<template #iconLeft><Icon :name="getTechnologyIcon(action.technology)" :size="14" /></template>
					<template #value>{{ action.technology }}</template>
				</Badge>
			</template>
			<template #default>
				<div class="flex-1">
					<p class="text-base font-medium opacity-90 leading-relaxed line-clamp-3">{{ action.description }}</p>
				</div>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge v-if="action.category" class="text-xs">
						<template #value>{{ action.category }}</template>
					</Badge>

					<Badge v-if="action.version" color="primary" type="splitted" class="text-xs">
						<template #label>v</template>
						<template #value>{{ action.version }}</template>
					</Badge>

					<Badge v-if="action.script_parameters.length > 0" color="warning" type="splitted" class="text-xs">
						<template #label>params</template>
						<template #value>{{ action.script_parameters.length }}</template>
					</Badge>

					<div v-if="action.tags && action.tags.length > 0" class="flex gap-1">
						<Badge v-for="tag of action.tags.slice(0, 2)" :key="tag" size="small" class="text-xs">
							<template #value>{{ tag }}</template>
						</Badge>
						<Badge v-if="action.tags.length > 2" size="small" class="text-xs">
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
import { Technology } from "@/types/copilotAction.d"
import ActionCardContent from "./ActionCardContent.vue"
import InvokeActionForm from "./InvokeActionForm.vue"

const { action } = defineProps<{ action: ActiveResponseItem; embedded?: boolean }>()

const showDetails = ref(false)
const showInvokeModal = ref(false)
const message = useMessage()
const PlayIcon = "carbon:play"

function getTechnologyIcon(technology: string): string {
	const iconMap: Record<string, string> = {
		[Technology.WINDOWS]: "carbon:logo-windows",
		[Technology.LINUX]: "carbon:logo-linux",
		[Technology.MACOS]: "carbon:logo-apple",
		[Technology.WAZUH]: "carbon:security",
		[Technology.VELOCIRAPTOR]: "carbon:eagle",
		[Technology.NETWORK]: "carbon:network-3",
		[Technology.CLOUD]: "carbon:cloud"
	}
	return iconMap[technology] || "carbon:application"
}

function getTechnologyColor(technology: string): "primary" | "warning" | "success" | "danger" | undefined {
	const colorMap: Record<string, "primary" | "warning" | "success" | "danger"> = {
		[Technology.WINDOWS]: "primary",
		[Technology.LINUX]: "warning",
		[Technology.MACOS]: "success",
		[Technology.WAZUH]: "success",
		[Technology.VELOCIRAPTOR]: "primary",
		[Technology.NETWORK]: "primary",
		[Technology.CLOUD]: "success"
	}
	return colorMap[technology]
}

function handleInvokeSuccess() {
	showInvokeModal.value = false
	message.success("Action invoked successfully!")
}
</script>

<style scoped>
.action-card {
	min-height: 200px;
}

.line-clamp-3 {
	display: -webkit-box;
	-webkit-line-clamp: 3;
	line-clamp: 3;
	-webkit-box-orient: vertical;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
