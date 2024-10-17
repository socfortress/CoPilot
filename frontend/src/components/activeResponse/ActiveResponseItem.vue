<template>
	<div class="active-response-item" :class="{ embedded }">
		<div class="flex flex-col gap-2 px-4 py-3">
			<div class="header-box flex items-center justify-between">
				<div class="title">
					{{ activeResponse.name }}
				</div>
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="InfoIcon"></Icon>
					</template>
				</n-button>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex grow flex-col gap-1">
					<div class="description">
						{{ activeResponse.description }}
					</div>
				</div>
				<ActiveResponseActions
					v-if="!hideActions"
					class="actions-box"
					:agent-id="agentId"
					:active-response="activeResponse"
					@start-loading="loading = true"
					@stop-loading="loading = false"
				/>
			</div>
			<div class="footer-box flex items-center justify-between gap-4">
				<ActiveResponseActions
					v-if="!hideActions"
					class="actions-box"
					:agent-id="agentId"
					:active-response="activeResponse"
					size="small"
					@start-loading="loading = true"
					@stop-loading="loading = false"
				/>
			</div>
		</div>

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
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal } from "naive-ui"
import { ref, toRefs } from "vue"
import ActiveResponseActions from "./ActiveResponseActions.vue"
import ActiveResponseDetails from "./ActiveResponseDetails.vue"

const props = defineProps<{
	activeResponse: SupportedActiveResponse
	embedded?: boolean
	hideActions?: boolean
	agentId?: string | number
}>()
const { activeResponse, embedded, agentId, hideActions } = toRefs(props)

const InfoIcon = "carbon:information"
const loading = ref(false)
const showDetails = ref(false)
</script>

<style lang="scss" scoped>
.active-response-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);

	.main-box {
		.content {
			word-break: break-word;

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	.footer-box {
		display: none;
		font-size: 13px;
		margin-top: 10px;
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}
	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 650px) {
		.main-box {
			.actions-box {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
