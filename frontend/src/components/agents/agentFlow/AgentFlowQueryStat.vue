<template>
	<div class="item flex flex-col gap-2 px-5 py-3" :class="{ embedded }">
		<div class="header-box flex justify-between items-center gap-3">
			<div class="id grow flex flex-wrap gap-2">
				<span>
					{{ formatDate(stat.first_active, dFormats.datetimesecmill) }}
				</span>
				<span>•</span>
				<span>
					{{ formatDate(stat.last_active, dFormats.datetimesecmill) }}
				</span>
			</div>
			<div class="actions whitespace-nowrap">
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="InfoIcon"></Icon>
					</template>
					Details
				</n-button>
			</div>
		</div>
		<div class="main-box flex flex-col gap-2 mt-2">
			<div class="content flex flex-wrap gap-2">
				<span v-for="artifact of stat.names_with_response" :key="artifact" class="artifact-label">
					{{ artifact }}
				</span>
			</div>
			<div class="error-message" v-if="stat.error_message">
				{{ stat.error_message }}
			</div>
			<div class="badges-box flex flex-wrap items-center gap-3 mt-1">
				<Badge type="splitted">
					<template #label>Status</template>
					<template #value>{{ stat.status || "-" }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Duration</template>
					<template #value>{{ duration }}</template>
				</Badge>
			</div>
		</div>
		<div class="footer-box">
			<div class="actions whitespace-nowrap">
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="InfoIcon"></Icon>
					</template>
					Details
				</n-button>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="`Agent Query Stat ${stat.Artifact ? ': ' + stat.Artifact : ''}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4" v-if="properties">
						<KVCard v-for="(value, key) of properties" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value === "" ? "-" : value ?? "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Backtrace" tab="Backtrace" display-directive="show">
					<div class="p-7 pt-4">
						<n-input
							:value="stat.backtrace"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3,
								maxRows: 18
							}"
						/>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NModal, NTabs, NTabPane, NInput, NButton } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils"
import type { FlowQueryStat } from "@/types/flow.d"
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import { computed, ref } from "vue"
import _pick from "lodash/pick"
import Badge from "@/components/common/Badge.vue"

const { stat, embedded } = defineProps<{ stat: FlowQueryStat; embedded?: boolean }>()

const InfoIcon = "carbon:information"

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const duration = computed(() => dayjs.duration(stat.duration).humanize())

const properties = computed(() => {
	return _pick(stat, [
		"Artifact",
		"log_rows",
		"uploaded_files",
		"uploaded_bytes",
		"expected_uploaded_bytes",
		"result_rows",
		"query_id",
		"total_queries"
	])
})
</script>

<style lang="scss" scoped>
.item {
	background-color: var(--bg-color);
	border-radius: var(--border-radius);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);

	.header-box {
		font-size: 13px;
		.id {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}
	}

	.main-box {
		.content {
			word-break: break-word;

			.artifact-label {
				background-color: var(--bg-secondary-color);
				padding: 3px 8px;
				border-radius: var(--border-radius);
			}
		}
	}
	.footer-box {
		display: none;
		text-align: right;
		font-size: 13px;
		margin-top: 10px;
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	&.embedded {
		background-color: var(--bg-secondary-color);

		.main-box {
			.content {
				.artifact-label {
					background-color: var(--bg-color);
				}
			}
		}
	}

	@container (max-width: 550px) {
		.header-box {
			.actions {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
