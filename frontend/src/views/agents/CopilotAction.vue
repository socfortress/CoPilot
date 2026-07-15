<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 flex-wrap items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeCopilotAction())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ action?.copilot_action_name || actionName }}</span>
				<span v-if="action?.version" class="text-secondary font-mono text-sm">v{{ action.version }}</span>
			</div>

			<n-button
				v-if="action"
				class="ml-auto shrink-0"
				type="primary"
				@click="showInvokeModal = true"
			>
				<template #icon>
					<Icon :name="PlayIcon" />
				</template>
				Invoke
			</n-button>
		</div>

		<n-spin v-if="actionName" :show="loading" class="min-h-40">
			<ActionCardContent v-if="action" :action />
			<n-empty v-else-if="!loading" description="Action not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid action" class="h-48 justify-center" />

		<n-modal
			v-if="action"
			v-model:show="showInvokeModal"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)' }"
			:bordered="false"
			:title="action.copilot_action_name"
			display-directive="show"
			segmented
		>
			<InvokeActionForm :action @success="handleInvokeSuccess()" @close="showInvokeModal = false" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CopilotAction } from "@/types/copilot-action"
import { NButton, NEmpty, NModal, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ActionCardContent from "@/components/copilotAction/ActionCardContent.vue"
import InvokeActionForm from "@/components/copilotAction/InvokeActionForm.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeCopilotAction } = useNavigation()

const BackIcon = "carbon:arrow-left"
const PlayIcon = "carbon:play"

const message = useMessage()
const showInvokeModal = ref(false)

const actionName = useRouteParam("name")

const { loading, entity: action } = useEntityDetails<CopilotAction, string>({
	entity: () => null,
	id: () => actionName.value,
	// the endpoint takes no abort signal, so the request itself is not cancellable
	fetch: name =>
		Api.copilotAction.getActionByName(name).then(res => ({
			entity: res.data.success ? (res.data.copilot_action ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Action not found",
	errorMessage: "An error occurred. Please try again later."
})

function handleInvokeSuccess() {
	showInvokeModal.value = false
	message.success("Action invoked successfully!")
}
</script>
