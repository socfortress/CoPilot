<template>
	<div class="alert-summary flex flex-col">
		<div class="header-box flex justify-between gap-4">
			<div class="id flex items-center gap-2" @click="gotoIndex(alertsSummary.index_name)">
				<IndexIcon :health="alertsSummary.indexStats?.health" color v-if="alertsSummary.indexStats?.health" />
				<Icon :name="PlaceholderIcon" v-else :size="18" />

				{{ alertsSummary.index_name }}

				<Icon :name="LinkIcon" :size="14" />
			</div>
			<div class="total-alerts flex items-center flex-wrap justify-end">
				<n-button
					v-if="alertsSummary.alerts.length > 3 && showAllAlerts"
					@click="showAllAlerts = false"
					class="show-less"
					size="tiny"
				>
					Show less
				</n-button>
				<span>
					Alerts:
					<strong class="font-mono ml-2">{{ alertsSummary.total_alerts }}</strong>
				</span>
			</div>
		</div>
		<div class="main-box">
			<div class="alert-list" :class="{ expand: showAllAlerts }">
				<n-scrollbar class="list-scroll" trigger="none">
					<Alert v-for="alert of alertsSummary.alerts" :key="alert._id" :alert="alert" />
				</n-scrollbar>

				<div class="load-more" v-if="alertsSummary.alerts.length > 3" @click="showAllAlerts = true">
					<n-button size="small" text class="!w-full">
						<template #icon>
							<Icon :name="ExpandIcon"></Icon>
						</template>
						See all alerts
					</n-button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type AlertsSummary } from "@/types/alerts.d"
import { NScrollbar, NButton } from "naive-ui"
import Alert from "./Alert.vue"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import Icon from "@/components/common/Icon.vue"
import type { IndexStats } from "@/types/indices.d"
import { ref } from "vue"
import { useGoto } from "@/composables/useGoto"

export interface AlertsSummaryExt extends AlertsSummary {
	indexStats?: IndexStats
}

const { alertsSummary } = defineProps<{ alertsSummary: AlertsSummaryExt }>()

const ExpandIcon = "carbon:chevron-down"
const PlaceholderIcon = "ph:question"
const LinkIcon = "carbon:launch"

const showAllAlerts = ref(false)
const { gotoIndex } = useGoto()
</script>

<style lang="scss" scoped>
.alert-summary {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	overflow: hidden;
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-size: 15px;
		padding: 14px 16px;
		min-height: 52px;
		border-bottom: var(--border-small-100);

		.id {
			word-break: break-word;
			cursor: pointer;

			&:hover {
				color: var(--primary-color);
			}
		}
		.total-alerts {
			text-align: right;
			gap: 7px;

			.show-less {
				opacity: 0;
				animation: show-less-fade 0.3s forwards;

				@keyframes show-less-fade {
					from {
						opacity: 0;
					}
					to {
						opacity: 1;
					}
				}
			}
		}
	}

	.main-box {
		.alert-list {
			position: relative;
			overflow: hidden;
			transition: all 0.2s var(--bezier-ease);

			.alert-details {
				border-bottom: var(--border-small-100);

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
				background: rgba(var(--bg-color-rgb), 0.6);
				background: linear-gradient(transparent 0%, var(--bg-color) 85%);
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
	}

	&:hover {
		border-color: var(--primary-color);
	}
}
</style>
