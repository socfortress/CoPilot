<template>
	<CardEntity>
		<template #headerMain>
			<div
				class="hover:text-primary flex cursor-pointer items-center gap-2"
				@click="routeIndex(alertsSummary.index_name)"
			>
				<IndexIcon v-if="alertsSummary.indexStats?.health" :health="alertsSummary.indexStats?.health" color />
				<Icon v-else :name="PlaceholderIcon" :size="18" />
				index: {{ alertsSummary.index_name }}
				<Icon :name="LinkIcon" :size="14" />
			</div>
		</template>
		<template #headerExtra>
			<div class="flex min-h-6 flex-wrap items-center justify-end gap-3">
				<n-button
					v-if="alertsSummary.alerts.length > 3 && showAllAlerts"
					class="animate-fade opacity-0"
					size="tiny"
					@click="showAllAlerts = false"
				>
					Show less
				</n-button>
				<span>
					Alerts:
					<strong class="ml-2 font-mono">{{ alertsSummary.total_alerts }}</strong>
				</span>
			</div>
		</template>
		<template #mainExtra>
			<div class="alert-list" :class="{ expand: showAllAlerts }">
				<n-scrollbar class="list-scroll" trigger="none">
					<div class="flex flex-col gap-2">
						<Alert v-for="alert of alertsSummary.alerts" :key="alert._id" :alert="alert" embedded />
					</div>
				</n-scrollbar>

				<div v-if="alertsSummary.alerts.length > 3" class="load-more" @click="showAllAlerts = true">
					<n-button size="small" text class="w-full!">
						<template #icon>
							<Icon :name="ExpandIcon" />
						</template>
						See all alerts
					</n-button>
				</div>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { AlertsSummary } from "@/types/alerts.d"
import type { IndexStats } from "@/types/indices.d"
import { NButton, NScrollbar } from "naive-ui"
import { ref } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { useNavigation } from "@/composables/useNavigation"
import Alert from "./Alert.vue"

export interface AlertsSummaryExt extends AlertsSummary {
	indexStats?: IndexStats
}

const { alertsSummary } = defineProps<{ alertsSummary: AlertsSummaryExt }>()

const ExpandIcon = "carbon:chevron-down"
const PlaceholderIcon = "ph:question"
const LinkIcon = "carbon:launch"

const showAllAlerts = ref(false)
const { routeIndex } = useNavigation()
</script>

<style lang="scss" scoped>
.alert-list {
	position: relative;
	overflow: hidden;
	transition: all 0.2s var(--bezier-ease);

	.alert-details {
		border-bottom: 1px solid var(--border-color);

		&:last-child {
			border-bottom: none;
			border-bottom-left-radius: var(--border-radius);
			border-bottom-right-radius: var(--border-radius);
		}
	}

	.load-more {
		position: absolute;
		top: 0;
		bottom: 0;
		left: 0;
		right: 0;
		height: 100%;
		width: 100%;
		background: rgba(var(--bg-default-color-rgb) / 0.6);
		background: linear-gradient(transparent 0%, var(--bg-default-color) 85%);
		display: flex;
		align-items: center;
		text-align: center;
		padding: 10px;
		flex-direction: column;
		justify-content: flex-end;
		cursor: pointer;
		transition: all 0.6s var(--bezier-ease);
	}

	:deep() {
		.list-scroll {
			max-height: 250px;
			transition: all 0.4s var(--bezier-ease);
		}
	}
	&.expand {
		:deep() {
			.list-scroll {
				max-height: 600px;
			}
		}

		.load-more {
			transform: translateY(100%);
		}
	}
}
</style>
