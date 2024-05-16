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
			test
			<!--



			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Details" tab="Details" display-directive="show" class="flex flex-col gap-4 !py-8">
					<div class="px-7">
						<n-card content-class="bg-secondary-color" class="overflow-hidden">
							<div class="flex justify-between gap-8 flex-wrap">
								<n-statistic label="Checks" :value="sca.total_checks" tabular-nums />
								<n-statistic label="Pass" :value="sca.pass" tabular-nums />
								<n-statistic label="Fail" :value="sca.fail" tabular-nums />
								<n-statistic label="Invalid" :value="sca.invalid" tabular-nums />
								<n-statistic label="Score" :value="sca.score + '%'" tabular-nums />
							</div>
						</n-card>
					</div>
					<div class="px-7">
						<n-card content-class="bg-secondary-color" class="overflow-hidden">
							<div class="flex justify-between gap-8 xs:!flex-row flex-col">
								<n-statistic
									class="grow"
									label="Start scan"
									:value="formatDate(sca.start_scan, dFormats.datetime).toString()"
								/>
								<n-statistic
									class="grow"
									label="End scan"
									:value="formatDate(sca.end_scan, dFormats.datetime).toString()"
								/>
							</div>
						</n-card>
					</div>
					<div class="grid gap-2 grid-auto-flow-200 px-7" v-if="properties">
						<KVCard v-for="(value, key) of properties" :key="key">
							<template #key>{{ key }}</template>
							<template #value>
								<template v-if="value && key === 'references'">
									<a
										:href="value"
										target="_blank"
										alt="references url"
										rel="nofollow noopener noreferrer"
										class="leading-6"
									>
										<span>
											{{ value }}
										</span>
										<Icon :name="LinkIcon" :size="14" class="relative top-0.5 ml-2" />
									</a>
								</template>
								<template v-else>
									{{ value ?? "-" }}
								</template>
							</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Description" tab="Description" display-directive="show">
					<div class="p-7 pt-4">
						<n-input
							:value="sca.description"
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
				<n-tab-pane name="SCA Results" tab="SCA Results" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<ScaResults :sca="sca" :agent="agent" />
					</div>
				</n-tab-pane>
			</n-tabs>
		-->
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import { NAvatar, useMessage, NPopover, NModal, NTabs, NTabPane, NSpin, NScrollbar, NButton } from "naive-ui"
import type { ScaPolicyResult } from "@/types/agents"

const { data, embedded } = defineProps<{
	data: ScaPolicyResult
	embedded?: boolean
}>()

const DetailsIcon = "carbon:settings-adjust"
const UserTypeIcon = "solar:shield-user-linear"
const ParentIcon = "material-symbols-light:supervisor-account-outline-rounded"
const ArrowIcon = "carbon:arrow-left"
const LocationIcon = "carbon:location"
const PhoneIcon = "carbon:phone"

const showDetails = ref(false)
const selectedTabsGroup = ref<"customer" | "agents">("customer")
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
