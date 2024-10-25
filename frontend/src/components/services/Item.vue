<template>
	<div>
		<CardEntity :embedded :clickable="selectable" :disabled hoverable>
			<template #default>
				<div class="flex items-center gap-3">
					<div v-if="selectable" class="check-box mr-2">
						<n-radio v-model:checked="checked" size="large" />
					</div>
					<div class="flex flex-col gap-1">
						{{ data.name }}
						<p>
							{{ data.description }}
						</p>
					</div>
				</div>
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<code class="py-1">Auth Keys:</code>
					<Badge v-for="authKey of data.keys" :key="authKey.auth_key_name">
						<template #value>
							{{ authKey.auth_key_name }}
						</template>
					</Badge>
				</div>
			</template>
			<template #footerExtra>
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="InfoIcon"></Icon>
					</template>
					Details
				</n-button>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="data.name"
			:bordered="false"
			segmented
		>
			<Suspense>
				<Markdown :source="data.details" />
			</Suspense>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ServiceItemData, ServiceItemType } from "./types"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal, NRadio } from "naive-ui"
import { defineAsyncComponent, ref, toRefs } from "vue"

const props = defineProps<{
	data: ServiceItemData
	type: ServiceItemType
	embedded?: boolean
	checked?: boolean
	selectable?: boolean
	disabled?: boolean
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const { data, embedded, checked, selectable, disabled } = toRefs(props)

const InfoIcon = "carbon:information"

const showDetails = ref(false)
</script>
