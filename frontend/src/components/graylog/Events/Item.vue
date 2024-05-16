<template>
	<div class="item flex flex-col gap-2 px-5 py-3" :class="{ highlight }" :id="'event-' + event.id">
		<div class="header-box flex justify-between">
			<div class="flex items-center gap-3">
				<n-tooltip trigger="hover">
					<template #trigger>
						<div class="priority cursor-help">
							{{ event.priority }}
						</div>
					</template>
					Priority
				</n-tooltip>
				<div class="id">
					<div class="flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>#{{ event.id }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
			</div>
			<div class="notification">
				Notifications:
				<strong>{{ event.notifications.length }}</strong>
			</div>
		</div>
		<div class="main-box">
			<div class="title">{{ event.title }}</div>
			<div class="description">{{ event.description }}</div>
		</div>
		<div class="footer-box flex justify-end items-center gap-3">
			<div class="notification">
				Notifications:
				<strong>{{ event.notifications.length }}</strong>
			</div>
		</div>

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
							:initialExpandedDepth="1"
						/>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { ref, toRefs } from "vue"
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import Icon from "@/components/common/Icon.vue"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/vuesjv-override.scss"
import { NModal, NTabs, NTabPane, NInput, NTooltip } from "naive-ui"

const props = defineProps<{ event: EventDefinition; highlight: boolean | null | undefined }>()
const { event, highlight } = toRefs(props)

const InfoIcon = "carbon:information"

const showDetails = ref(false)
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;

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
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);

			&:hover {
				color: var(--primary-color);
			}
		}
		.notification {
			color: var(--fg-secondary-color);
		}
	}
	.main-box {
		word-break: break-word;

		.description {
			color: var(--fg-secondary-color);
			font-size: 13px;
		}
	}
	.footer-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		margin-top: 10px;
		display: none;

		.notification {
			text-align: right;
			color: var(--fg-secondary-color);
		}
	}

	&.highlight {
		background-color: var(--primary-005-color);
		box-shadow: 0px 0px 0px 1px inset var(--primary-030-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 650px) {
		.header-box {
			.notification {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
