<template>
	<div>
		<CardEntity :embedded :clickable hoverable>
			<template #headerMain>
				<div class="text-default text-base">
					{{ activeResponse.name }}
				</div>
			</template>

			<template #headerExtra>
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="InfoIcon"></Icon>
					</template>
				</n-button>
			</template>

			<template #default>
				<p class="text-sm">
					{{ activeResponse.description }}
				</p>
			</template>

			<template v-if="!hideActions" #footerExtra>
				<ActiveResponseActions :agent-id="agentId" :active-response="activeResponse" size="small" />
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="activeResponse.name"
			:bordered="false"
			segmented
		>
			<ActiveResponseDetails :active-response="activeResponse" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SupportedActiveResponse } from "@/types/activeResponse.d"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal } from "naive-ui"
import { ref, toRefs } from "vue"
import ActiveResponseActions from "./ActiveResponseActions.vue"
import ActiveResponseDetails from "./ActiveResponseDetails.vue"

const props = defineProps<{
	activeResponse: SupportedActiveResponse
	embedded?: boolean
	clickable?: boolean
	hideActions?: boolean
	agentId?: string | number
}>()
const { activeResponse, embedded, agentId, hideActions, clickable } = toRefs(props)

const InfoIcon = "carbon:information"
const showDetails = ref(false)
</script>
