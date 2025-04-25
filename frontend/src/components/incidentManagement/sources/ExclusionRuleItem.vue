<template>
	<div>
		<CardEntity :loading :embedded hoverable clickable @click.stop="openDetails()">
			<template #headerMain>#{{ entity.name }}</template>
			<template #headerExtra>
				<div class="flex items-center gap-2">
					<span>{{ entity.enabled ? "Enabled" : "Disabled" }}</span>
					<Icon v-if="entity.enabled" :name="EnabledIcon" :size="14" class="text-success"></Icon>
					<Icon v-else :name="DisabledIcon" :size="14" class="text-secondary"></Icon>
				</div>
			</template>
			<template #default>
				{{ entity.title }}
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" bright fluid class="!hidden sm:!flex">
						<template #iconLeft>
							<Icon :name="TargetIcon" />
						</template>
						<template #label>match_count</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ entity.match_count }}
							</div>
						</template>
					</Badge>

					<Badge v-if="entity.last_matched_at" type="splitted" bright fluid class="!hidden sm:!flex">
						<template #iconLeft>
							<Icon :name="TimeIcon" />
						</template>
						<template #label>last_matched_at</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ formatDate(entity.last_matched_at, dFormats.datetimesec) }}
							</div>
						</template>
					</Badge>

					<Badge v-if="entity.customer_code" type="splitted" class="!hidden sm:!flex">
						<template #label>Customer</template>
						<template #value>
							<div class="flex h-full items-center">
								<code
									class="text-primary cursor-pointer leading-none"
									@click.stop="gotoCustomer({ code: entity.customer_code })"
								>
									#{{ entity.customer_code }}
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
							</div>
						</template>
					</Badge>
				</div>
			</template>

			<template #footerExtra>enable toggle</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(480px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col !p-0"
				:title="entity.name"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				details
				<!--
				<QueryDetails :query @deleted="emitDelete(query)" @updated="updateQuery($event)" />
				-->
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ExclusionRule } from "@/types/incidentManagement/sources.d"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NCard, NModal } from "naive-ui"
import { ref, toRefs } from "vue"

const props = defineProps<{
	entity: ExclusionRule
	embedded?: boolean
}>()

/*
const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated"): void
}>()
*/

const { entity, embedded } = toRefs(props)

const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const TargetIcon = "zondicons:target"
const EnabledIcon = "carbon:circle-solid"
const DisabledIcon = "carbon:subtract-alt"

const loading = ref(false)
const showDetails = ref(false)
const { gotoCustomer } = useGoto()
const dFormats = useSettingsStore().dateFormat

function openDetails() {
	showDetails.value = true
}

function closeDetails() {
	showDetails.value = false
}
</script>
