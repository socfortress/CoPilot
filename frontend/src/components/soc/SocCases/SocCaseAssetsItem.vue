<template>
	<div class="soc-asset-item">
		<div class="flex flex-col gap-2 px-5 py-4">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2">
					<div class="id flex cursor-pointer items-center gap-2" @click="showDetails = true">
						<span>#{{ asset.asset_id }} - {{ asset.asset_uuid }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div class="title" v-html="asset.asset_name"></div>
					<div v-if="asset.asset_description" class="description mt-2">
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
					</div>

					<div class="badges-box mt-4 flex flex-wrap items-center gap-3">
						<Badge type="splitted" color="primary">
							<template #label>Status</template>
							<template #value>
								{{ asset.analysis_status }}
							</template>
						</Badge>
						<Badge type="splitted" color="primary">
							<template #label>Type</template>
							<template #value>
								{{ asset.asset_type }}
							</template>
						</Badge>
						<Badge v-for="tag of tags" :key="tag.key" type="splitted" color="primary">
							<template #label>
								{{ tag.key }}
							</template>
							<template v-if="tag.value !== undefined" #value>
								{{ tag.value || "-" }}
							</template>
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
					<div v-if="properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of properties" :key="key">
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
				<n-tab-pane name="Link" tab="Link" display-directive="show:lazy">
					<div v-if="asset.link?.length" class="flex flex-col gap-2 px-4">
						<SocCaseAssetLink
							v-for="link of asset.link"
							:key="`${link.case_id}-${link.asset_id}`"
							:link="link"
						/>
					</div>
					<template v-else>
						<n-empty description="No items found" class="h-48 justify-center" />
					</template>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SocCaseAsset } from "@/types/soc/asset.d"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { isUrlLike } from "@/utils"
import _omit from "lodash/omit"
import _split from "lodash/split"
import _upperFirst from "lodash/upperFirst"
import { NEmpty, NModal, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"

const { asset } = defineProps<{ asset: SocCaseAsset }>()

const SocCaseAssetLink = defineAsyncComponent(() => import("./SocCaseAssetLink.vue"))

const InfoIcon = "carbon:information"
const LinkIcon = "carbon:launch"

const showDetails = ref(false)

const excerpt = computed(() => {
	const text = asset.asset_description
	const truncated = text.split(" ").slice(0, 30).join(" ")

	return truncated + (truncated !== text ? "..." : "")
})

const descriptionFull = computed(() => {
	const text = asset.asset_description

	return text.replace(/\n/g, "<br>") || "Empty"
})

const tags = computed<{ key: string; value?: string }[]>(() => {
	if (!asset?.asset_tags) {
		return []
	}

	return _split(asset.asset_tags, ",")
		.filter(o => !!o)
		.map(o => {
			const chunks = _split(o, ":")

			return {
				key: _upperFirst(chunks[0]),
				value: chunks[1] || undefined
			}
		})
})

const properties = computed(() => {
	return _omit(asset, ["asset_description", "link"])
})
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
