<template>
	<div :id="`event-${event.id}`">
		<CardEntity :highlighted="!!highlight" hoverable clickable @click="showDetails = true">
			<template #headerMain>
				<div class="flex items-center gap-3">
					<n-tooltip trigger="hover">
						<template #trigger>
							<div class="priority cursor-help">
								{{ event.priority }}
							</div>
						</template>
						Priority
					</n-tooltip>
					<span>#{{ event.id }}</span>
				</div>
			</template>
			<template #headerExtra>
				Notifications:
				<strong>{{ event.notifications.length }}</strong>
			</template>
			<template #default>
				<div class="flex flex-col gap-1">
					<div>
						{{ event.title }}
					</div>
					<p>
						{{ event.description }}
					</p>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="event.title"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="query" tab="Query" display-directive="show">
					<div class="p-7 pt-4">
						<n-input
							:value="event?.config?.query"
							type="textarea"
							readonly
							size="large"
							placeholder="Empty"
							:autosize="{
								minRows: 3,
								maxRows: 10
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="fieldSpec" tab="Field Spec" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SimpleJsonViewer
							class="vuesjv-override"
							:model-value="event.field_spec"
							:initial-expanded-depth="1"
						/>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { NInput, NModal, NTabPane, NTabs, NTooltip } from "naive-ui"
import { ref, toRefs } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/overrides/vuesjv-override.scss"

const props = defineProps<{ event: EventDefinition; highlight: boolean | null | undefined }>()
const { event, highlight } = toRefs(props)

const showDetails = ref(false)
</script>

<style lang="scss" scoped>
.priority {
	background-color: var(--hover-005-color);
	border: var(--border-small-100);
	width: 20px;
	height: 20px;
	border-radius: 99999px;
	text-align: center;
	line-height: 19px;
	font-size: 11px;
}
</style>
