<template>
	<div class="sca-result-item" :class="{ embedded }">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex items-center">
				<div class="id">#{{ data.id }}</div>
				<div class="grow"></div>
				<div class="actions">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="DetailsIcon"></Icon>
						</template>
						Details
					</n-button>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ data.title }}</div>
					<div class="description">$ {{ data.command }}</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<Badge
					type="splitted"
					:color="
						data.result === 'failed' ? 'danger' : data.result === 'not applicable' ? 'warning' : 'success'
					"
					class="uppercase"
				>
					<template #label>{{ data.result }}</template>
				</Badge>

				<Badge type="splitted">
					<template #label>Compliance</template>
					<template #value>{{ data.compliance?.length || "-" }}</template>
				</Badge>

				<Badge type="splitted">
					<template #label>Condition</template>
					<template #value>{{ data.condition || "-" }}</template>
				</Badge>

				<Badge type="splitted">
					<template #label>Rules</template>
					<template #value>{{ data.rules?.length || "-" }}</template>
				</Badge>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="data?.title"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane
					name="Overview"
					tab="Overview"
					display-directive="show:lazy"
					class="flex flex-col gap-4 !py-8"
				>
					<div class="px-7">
						<n-card content-class="bg-secondary-color" class="overflow-hidden">
							<div class="flex justify-between gap-8 flex-wrap">
								<n-statistic label="Result" tabular-nums>
									<span
										class="uppercase"
										:class="
											data.result === 'failed'
												? 'text-error-color'
												: data.result === 'not applicable'
													? 'text-warning-color'
													: 'text-success-color'
										"
									>
										{{ data.result }}
									</span>
								</n-statistic>
								<n-statistic label="Condition" tabular-nums>
									<span class="uppercase">{{ data.condition }}</span>
								</n-statistic>
								<n-statistic label="Compliance" :value="data.compliance.length" tabular-nums />
								<n-statistic label="Rules" :value="data.rules.length" tabular-nums />
							</div>
						</n-card>
					</div>

					<div class="px-7">
						<n-card content-class="bg-secondary-color !p-0" class="overflow-hidden">
							<div
								class="scrollbar-styled overflow-hidden"
								v-shiki="{ theme: codeTheme, lang: 'shell', decode: true }"
							>
								<pre v-html="data.command"></pre>
							</div>
						</n-card>
					</div>

					<div class="grid gap-2 grid-auto-flow-200 px-7" v-if="properties">
						<KVCard v-for="(value, key) of properties" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value ?? "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Description" tab="Description" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<n-input
							:value="data.description"
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
				<n-tab-pane name="Rationale" tab="Rationale" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<n-input
							:value="data.rationale"
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
				<n-tab-pane name="Reason" tab="Reason" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<n-input
							:value="data.reason"
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
				<n-tab-pane name="Remediation" tab="Remediation" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<n-input
							:value="data.remediation"
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
				<n-tab-pane name="Compliance" tab="Compliance" display-directive="show:lazy">
					<div class="p-7 pt-4">compliance</div>
				</n-tab-pane>
				<n-tab-pane name="Rules" tab="Rules" display-directive="show:lazy">
					<div class="p-7 pt-4">rules</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import vShiki from "@/directives/v-shiki"
import _pick from "lodash/pick"
import KVCard from "@/components/common/KVCard.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref } from "vue"
import { NModal, NTabs, NTabPane, NStatistic, NInput, NCard, NButton } from "naive-ui"
import type { ScaPolicyResult } from "@/types/agents"
import { useThemeStore } from "@/stores/theme"

const { data, embedded } = defineProps<{
	data: ScaPolicyResult
	embedded?: boolean
}>()

const DetailsIcon = "carbon:settings-adjust"

const showDetails = ref(false)
const themeStore = useThemeStore()
const codeTheme = computed(() => (themeStore.isThemeDark ? "dark" : "light"))
const properties = computed(() => {
	return _pick(data, ["id", "policy_id", "title"])
})
</script>

<style lang="scss" scoped>
.sca-result-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

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

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
