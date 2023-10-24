<template>
	<div class="item flex flex-col mb-2 gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="flex items-center gap-3">
				<n-tooltip trigger="hover">
					<template #trigger>
						<div class="priority">
							{{ event.priority }}
						</div>
					</template>
					Priority
				</n-tooltip>
				<div class="id">
					<div class="flex items-center gap-2">
						<span>#{{ event.id }}</span>
						<Icon :name="InfoIcon" :size="16" @click="showDetails = true" class="cursor-pointer"></Icon>
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
			content-style="padding:0px"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="event.title"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated justify-content="space-evenly">
				<n-tab-pane name="alerts" tab="Alerts" display-directive="show:lazy">
					<div class="p-3 break-all">
						<n-input :value="event?.config?.query" type="textarea" readonly />
					</div>
				</n-tab-pane>
				<n-tab-pane name="fieldSpec" tab="Field Spec" display-directive="show:lazy">
					<div class="p-3">
						<JsonTreeView :data="fieldSpec" :colorScheme="theme" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import Icon from "@/components/common/Icon.vue"
import { JsonTreeView } from "json-tree-view-vue3"
import { computed, ref } from "vue"
import { NModal, NTabs, NTabPane, NInput, NTooltip } from "naive-ui"
import { useThemeStore } from "@/stores/theme"

const { event } = defineProps<{ event: EventDefinition }>()

const InfoIcon = "carbon:information"

const showDetails = ref(false)
const fieldSpec = computed(() => JSON.stringify(event?.field_spec))
const theme = computed(() => useThemeStore().themeName)
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;

		.priority {
			background-color: var(--divider-020-color);
			width: 20px;
			height: 20px;
			border-radius: 99999px;
			text-align: center;
			line-height: 21px;
			font-size: 12px;
		}
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
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
