<template>
	<div class="alert-summary flex flex-col gap-2">
		<div class="header-box flex justify-between">
			<div class="id flex items-center gap-2" @click="gotoIndicesPage(alertsSummary.index_name)">
				<IndexIcon :health="alertsSummary.indexStats?.health" color v-if="alertsSummary.indexStats?.health" />
				<Icon :name="PlaceholderIcon" v-else :size="18" />

				{{ alertsSummary.index_name }}
			</div>
			<div class="total-alerts">
				Alerts:
				<strong class="font-mono ml-2">{{ alertsSummary.total_alerts }}</strong>
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
import { useRouter } from "vue-router"
import { ref } from "vue"

export interface AlertsSummaryExt extends AlertsSummary {
	indexStats?: IndexStats
}

const { alertsSummary } = defineProps<{ alertsSummary: AlertsSummaryExt }>()

const ExpandIcon = "carbon:chevron-down"
const PlaceholderIcon = "ph:question"

const router = useRouter()
const showAllAlerts = ref(false)

function gotoIndicesPage(index: string) {
	router.push(`/indices?index_name=${index}`).catch(() => {})
}
</script>

<style lang="scss" scoped>
.alert-summary {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	overflow: hidden;
	transition: all 0.2s var(--bezier-ease);

	.header-box {
		font-size: 15px;
		padding: 14px 16px;
		.id {
			word-break: break-word;
			line-height: 1;
			cursor: pointer;

			&:hover {
				color: var(--primary-color);
			}
		}
		.total-alerts {
			line-height: 1.5;
		}
	}

	.main-box {
		.alert-list {
			position: relative;
			overflow: hidden;
			transition: all 0.2s var(--bezier-ease);

			.alert-details {
				border-top: var(--border-small-100);

				&:last-child {
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
					max-height: 200px;
					transition: all 0.4s var(--bezier-ease);
				}
			}
			&.expand {
				:deep() {
					.list-scroll {
						max-height: 400px;
					}
				}

				.load-more {
					transform: translateY(100%);
				}
			}
		}
	}

	&:hover {
		//box-shadow: 0px 0px 0px 1px var(--primary-color);
	}

	@container (max-width: 650px) {
	}
}
</style>
