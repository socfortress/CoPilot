<template>
	<div class="soc-asset-item">
		<div class="flex flex-col gap-2 px-5 py-4">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2">
					<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>#{{ asset.asset_id }} - {{ asset.asset_uuid }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div class="title">{{ asset.asset_name }}</div>
					<div class="description mt-2" v-if="asset.asset_description">
						<template v-if="isUrlLike(asset.asset_description)">
							<a
								:href="asset.asset_description"
								class="asset-url"
								target="_blank"
								alt="asset url"
								rel="nofollow noopener noreferrer"
							>
								<code class="text-primary-color">
									<span>
										{{ asset.asset_description }}
									</span>
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
							</a>
						</template>
						<template v-else>{{ excerpt }}</template>
					</div>

					<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
						<Badge type="splitted" v-if="asset.date_added">
							<template #iconLeft>
								<Icon :name="ClockIcon" :size="14"></Icon>
							</template>
							<template #label>Added</template>
							<template #value>{{ formatDate(asset.date_added) }}</template>
						</Badge>
						<Badge type="splitted" v-if="asset.date_update">
							<template #iconLeft>
								<Icon :name="ClockIcon" :size="14"></Icon>
							</template>
							<template #label>Updated</template>
							<template #value>{{ formatDate(asset.date_update) }}</template>
						</Badge>
						<Badge type="active" class="cursor-pointer" @click="gotoAgent(asset.asset_tags)">
							<template #iconRight>
								<Icon :name="LinkIcon" :size="14"></Icon>
							</template>
							<template #label>Agent: {{ asset.asset_tags }}</template>
						</Badge>
					</div>
				</div>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Assets #${asset.asset_id} - ${asset.asset_uuid}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4" v-if="properties">
						<KVCard v-for="(value, key) of properties" :key="key">
							<template #key>{{ key }}</template>
							<template #value>
								<template v-if="key === 'asset_tags'">
									<code
										class="cursor-pointer text-primary-color"
										@click="gotoAgent(value)"
										v-if="value && value !== '-'"
									>
										{{ value }}
										<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
									</code>
									<span v-else>-</span>
								</template>
								<template v-else>
									{{ value ?? "-" }}
								</template>
							</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Type" tab="Type" display-directive="show">
					<div class="grid gap-2 grid-auto-flow-250 p-7 pt-4" v-if="assetType">
						<KVCard v-for="(value, key) of assetType" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value || "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Description" tab="Description" display-directive="show">
					<div class="p-7 pt-4">
						<template v-if="isUrlLike(asset.asset_description)">
							<a
								:href="asset.asset_description"
								class="asset-url"
								target="_blank"
								alt="asset url"
								rel="nofollow noopener noreferrer"
							>
								{{ asset.asset_description }}
							</a>
						</template>
						<template v-else>
							<div v-html="descriptionFull"></div>
						</template>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Artifact Collection" tab="Artifact Collection" display-directive="show:lazy">
					<div class="p-7 pt-2">
						<ArtifactsCollect
							:hostname="asset.asset_name"
							:artifacts-filter="{ hostname: asset.asset_name }"
							hide-hostname-field
							velociraptor-id="string"
							hide-velociraptor-id-field
						/>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, defineAsyncComponent, ref } from "vue"
import { NModal, NTabs, NTabPane } from "naive-ui"
import _omit from "lodash/omit"
import dayjs from "@/utils/dayjs"
import { isUrlLike } from "@/utils"
import type { SocAlertAsset } from "@/types/soc/asset.d"
import { useSettingsStore } from "@/stores/settings"
import { useGoto } from "@/composables/useGoto"
const ArtifactsCollect = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCollect.vue"))

const { asset } = defineProps<{ asset: SocAlertAsset }>()

const InfoIcon = "carbon:information"
const ClockIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const { gotoAgent } = useGoto()
const showDetails = ref(false)

const dFormats = useSettingsStore().dateFormat

const excerpt = computed(() => {
	const text = asset.asset_description
	const truncated = text.split(" ").slice(0, 30).join(" ")

	return truncated + (truncated !== text ? "..." : "")
})

const descriptionFull = computed(() => {
	const text = asset.asset_description

	return text.replace(/\n/gim, "<br>") || "Empty"
})

const properties = computed(() => {
	const props = _omit(asset, ["asset_description", "asset_type"])
	for (const key in props) {
		const prop = props[key as keyof typeof props]
		if (prop && (key === "date_added" || key === "date_update")) {
			props[key] = formatDate(prop.toString(), true)
		}
	}
	return props
})

const assetType = computed(() => {
	return asset.asset_type || {}
})

const formatDate = (date: string, useSec = false) => {
	const datejs = dayjs(date)
	if (!datejs.isValid()) return date

	return datejs.format(useSec ? dFormats.datetimesec : dFormats.datetime)
}
</script>

<style lang="scss" scoped>
.soc-asset-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;

			&:hover {
				color: var(--primary-color);
			}
		}

		.toggler-bookmark {
			&.active {
				color: var(--primary-color);
			}
			&:hover {
				color: var(--primary-color);
			}
		}
		.time {
			color: var(--fg-secondary-color);

			&:hover {
				color: var(--primary-color);
			}
		}
	}

	.main-box {
		word-break: break-word;

		.content {
			max-width: 100%;

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;

				.asset-url {
					display: block;

					code {
						padding: 8px 12px;
						display: flex;
						gap: 10px;

						span {
							white-space: nowrap;
							flex-grow: 1;
							overflow: hidden;
							text-overflow: ellipsis;
						}
					}
				}
			}
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
