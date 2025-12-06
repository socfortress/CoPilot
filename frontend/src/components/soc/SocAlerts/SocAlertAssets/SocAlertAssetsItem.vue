<template>
	<div>
		<CardEntity hoverable clickable @click.stop="showDetails = true">
			<template #headerMain>#{{ asset.asset_id }} - {{ asset.asset_uuid }}</template>
			<template #default>
				<div class="flex flex-col gap-1">
					{{ asset.asset_name }}

					<p v-if="asset.asset_description" class="text-sm">
						<template v-if="isUrlLike(asset.asset_description)">
							<a
								:href="asset.asset_description"
								class="asset-url"
								target="_blank"
								alt="asset url"
								rel="nofollow noopener noreferrer"
							>
								<code class="text-primary">
									<span>
										{{ asset.asset_description }}
									</span>
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
							</a>
						</template>
						<template v-else>
							{{ excerpt }}
						</template>
					</p>
				</div>
			</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge v-if="asset.date_added" type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="ClockIcon" :size="14" />
						</template>
						<template #label>Added</template>
						<template #value>
							{{ formatDate(asset.date_added) }}
						</template>
					</Badge>
					<Badge v-if="asset.date_update" type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="ClockIcon" :size="14" />
						</template>
						<template #label>Updated</template>
						<template #value>
							{{ formatDate(asset.date_update) }}
						</template>
					</Badge>
					<Badge type="active" class="cursor-pointer" @click.stop="gotoAgent(asset.asset_tags)">
						<template #iconRight>
							<Icon :name="LinkIcon" :size="14" />
						</template>
						<template #label>Agent: {{ asset.asset_tags }}</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Assets #${asset.asset_id} - ${asset.asset_uuid}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div v-if="properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of properties" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								<template v-if="key === 'asset_tags'">
									<code
										v-if="value && value !== '-'"
										class="text-primary cursor-pointer"
										@click.stop="gotoAgent(value)"
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
						</CardKV>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Type" tab="Type" display-directive="show">
					<div v-if="assetType" class="grid-auto-fit-250 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of assetType" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								{{ value || "-" }}
							</template>
						</CardKV>
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
import type { SocAlertAsset } from "@/types/soc/asset.d"
import _omit from "lodash/omit"
import { NModal, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { isUrlLike } from "@/utils"
import dayjs from "@/utils/dayjs"

const { asset } = defineProps<{ asset: SocAlertAsset }>()

const ArtifactsCollect = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCollect.vue"))

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

	return text.replace(/\n/g, "<br>") || "Empty"
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

function formatDate(date: string, useSec = false) {
	const datejs = dayjs(date)
	if (!datejs.isValid()) return date

	return datejs.format(useSec ? dFormats.datetimesec : dFormats.datetime)
}
</script>

<style lang="scss" scoped>
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
</style>
