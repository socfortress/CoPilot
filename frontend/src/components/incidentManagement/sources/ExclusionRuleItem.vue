<template>
	<div>
		<CardEntity :loading :embedded hoverable>
			<template #headerMain>{{ entity.name }}</template>
			<template #headerExtra>
				<div class="hidden font-sans sm:block">
					<n-switch
						v-model:value="entity.enabled"
						:rail-style
						:loading="updatingStatus"
						@update:value="toggleExclusionRuleStatus()"
					>
						<template #checked>Enabled</template>
						<template #unchecked>Disabled</template>
					</n-switch>
				</div>
			</template>
			<template #default>
				{{ entity.title }}
			</template>
			<template #footerMain>
				<div class="hidden flex-wrap items-center gap-3 sm:flex">
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TargetIcon" />
						</template>
						<template #label>Match count</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ entity.match_count }}
							</div>
						</template>
					</Badge>

					<Badge v-if="entity.last_matched_at" type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TimeIcon" />
						</template>
						<template #label>Last match</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ formatDate(entity.last_matched_at, dFormats.datetimesec) }}
							</div>
						</template>
					</Badge>

					<Badge v-if="entity.customer_code" type="splitted">
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

			<template #footerExtra>
				<div class="flex items-center gap-3">
					<div class="block sm:hidden">
						<n-switch
							v-model:value="entity.enabled"
							:rail-style
							:loading="updatingStatus"
							@update:value="toggleExclusionRuleStatus()"
						>
							<template #checked>Enabled</template>
							<template #unchecked>Disabled</template>
						</n-switch>
					</div>

					<n-button size="small" @click.stop="openDetails()">
						<template #icon>
							<Icon :name="DetailsIcon"></Icon>
						</template>
						Details
					</n-button>
				</div>
			</template>
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
import type { CSSProperties } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { useThemeStore } from "@/stores/theme"
import { formatDate } from "@/utils"
import { NButton, NCard, NModal, NSwitch, useMessage } from "naive-ui"
import { computed, ref, toRefs } from "vue"

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
const DetailsIcon = "carbon:settings-adjust"
const TargetIcon = "zondicons:target"

const message = useMessage()
const themeStore = useThemeStore()
const checkedColor = computed(() => themeStore.style["success-color-rgb"])
const uncheckedColor = computed(() => themeStore.style["border-color-rgb"])
const loading = ref(false)
const updatingStatus = ref(false)
const showDetails = ref(false)
const { gotoCustomer } = useGoto()
const dFormats = useSettingsStore().dateFormat

function openDetails() {
	showDetails.value = true
}

function closeDetails() {
	showDetails.value = false
}

function railStyle({ focused, checked }: { focused: boolean; checked: boolean }) {
	const style: CSSProperties = {}
	if (checked) {
		style.background = `rgb(${checkedColor.value})`
		if (focused) {
			style.boxShadow = `0 0 0 2px rgb(${checkedColor.value} / 30%)`
		}
	} else {
		style.background = `rgb(${uncheckedColor.value})`
		if (focused) {
			style.boxShadow = `0 0 0 2px rgb(${uncheckedColor.value} / 30%)`
		}
	}
	return style
}

function toggleExclusionRuleStatus() {
	updatingStatus.value = true

	Api.incidentManagement
		.toggleExclusionRuleStatus(entity.value.id)
		.then(res => {
			if (res.data.success) {
				entity.value.enabled = res.data.exclusion_response.enabled
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			updatingStatus.value = false
		})
}
</script>
