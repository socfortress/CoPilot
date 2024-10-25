<template>
	<div :id="`alert-${alert?.alert_id}`">
		<CardEntity
			:loading
			:loading-description="loadingDelete ? 'Deleting Soc Alert' : 'Loading Soc Alert'"
			class="min-h-36"
			clickable
			hoverable
			:status="isBookmark ? 'success' : undefined"
			:embedded
			:highlighted="!!highlight"
			@click.stop="showDetails = true"
		>
			<template #headerMain>
				<div class="flex items-center gap-2">
					<div v-if="showCheckbox" class="check-box mr-2">
						<n-checkbox v-model:checked="checked" size="large" />
					</div>
					<span v-if="alert">#{{ alert.alert_id }} - {{ alert.alert_uuid }}</span>
					<SocAlertItemBookmarkToggler
						v-if="!hideBookmarkAction && alert"
						:alert
						:is-bookmark
						@bookmark="emit('bookmark', $event)"
					/>
				</div>
			</template>
			<template v-if="alert" #headerExtra>
				<SocAlertItemTime :alert />
			</template>

			<template v-if="alert" #default>
				<div class="flex flex-col gap-1">
					{{ alert.alert_title }}

					<p v-if="alert.alert_description && alert.alert_title !== alert.alert_description" class=" ">
						{{ alert.alert_description }}
					</p>
				</div>
			</template>

			<template #mainExtra>
				<div class="flex justify-between gap-3">
					<div>
						<div
							v-if="showBadgesToggle"
							class="show-badges-toggle flex items-center gap-2"
							@click.stop="showBadges = !showBadges"
						>
							{{ showBadges ? "Less info" : "More info" }}
							<span class="flex items-center transition-transform" :class="{ 'rotate-90': showBadges }">
								<Icon :name="ChevronIcon" :size="14"></Icon>
							</span>
						</div>
						<n-collapse-transition :show="!showBadgesToggle || showBadges">
							<SocAlertItemBadges v-if="alert" class="badges-box" :alert :users @updated="updateAlert" />
						</n-collapse-transition>
					</div>

					<SocAlertItemActions
						v-if="!hideSocCaseAction && alert"
						class="flex flex-row flex-wrap gap-2"
						size="small"
						:case-id
						:alert-id="alert.alert_id"
						@case-created="caseCreated($event)"
						@deleted="deleted()"
						@start-deleting="loadingDelete = true"
					/>
				</div>
			</template>
			<template #footer>
				<n-collapse>
					<template #arrow>
						<div class="mx-5 flex">
							<Icon :name="ChevronIcon"></Icon>
						</div>
					</template>
					<n-collapse-item>
						<template #header>
							<div class="-ml-2 py-3">Alert details</div>
						</template>
						<AlertItem :alert="alertObject" hide-actions class="-mt-4" />
					</n-collapse-item>
				</n-collapse>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<template #header>
				<div class="whitespace-nowrap">SOC Alert: {{ alert?.alert_id }}</div>
			</template>
			<template #header-extra>
				<ArtifactRecommendation v-if="alert" :context="alert.alert_context" />
			</template>
			<SocAlertItemDetails v-if="alert" :alert :users @updated="updateAlert" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/alerts.d"
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocUser } from "@/types/soc/user.d"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { NCheckbox, NCollapse, NCollapseItem, NCollapseTransition, NModal, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref, toRefs, watch } from "vue"
import SocAlertItemActions from "./SocAlertItemActions.vue"
import SocAlertItemBookmarkToggler from "./SocAlertItemBookmarkToggler.vue"
import SocAlertItemTime from "./SocAlertItemTime.vue"

const props = defineProps<{
	alertData?: SocAlert
	alertId?: string | number
	isBookmark?: boolean
	highlight?: boolean | null | undefined
	embedded?: boolean
	users?: SocUser[]
	hideSocCaseAction?: boolean
	hideBookmarkAction?: boolean
	showBadgesToggle?: boolean
	showCheckbox?: boolean
}>()
const emit = defineEmits<{
	(e: "bookmark", value: boolean): void
	(e: "deleted"): void
	(e: "checked"): void
	(e: "unchecked"): void
	(e: "check", value: boolean): void
}>()
const SocAlertItemDetails = defineAsyncComponent(() => import("./SocAlertItemDetails.vue"))
const SocAlertItemBadges = defineAsyncComponent(() => import("./SocAlertItemBadges.vue"))
const ArtifactRecommendation = defineAsyncComponent(() => import("@/components/artifacts/ArtifactRecommendation.vue"))
const AlertItem = defineAsyncComponent(() => import("@/components/alerts/Alert.vue"))

const checked = defineModel<boolean>("checked", { default: false })

const {
	alertData,
	alertId,
	isBookmark,
	highlight,
	users,
	embedded,
	hideSocCaseAction,
	hideBookmarkAction,
	showBadgesToggle,
	showCheckbox
} = toRefs(props)

const ChevronIcon = "carbon:chevron-right"

const showDetails = ref(false)
const showBadges = ref(false)
const loadingDelete = ref(false)
const loadingData = ref(false)
const loadingBookmark = ref(false)
const message = useMessage()

const alert = ref(alertData.value || null)
const alertObject = ref<Alert>({} as Alert)
const loading = computed(() => loadingBookmark.value || loadingData.value || loadingDelete.value)
const caseId = computed(() => (alert.value?.cases?.length ? alert.value?.cases[0] : null))

function updateAlert(alertUpdated: SocAlert) {
	const ownerObject = alertUpdated.owner
	const modificationHistory = alertUpdated.modification_history

	if (alert.value) {
		alert.value.owner = ownerObject
		alert.value.modification_history = modificationHistory
	}
}

function getAlert(id: string | number, cb?: () => void) {
	loadingData.value = true

	Api.soc
		.getAlert(id.toString())
		.then(res => {
			if (res.data.success) {
				alert.value = res.data?.alert || null
				if (cb) cb()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingData.value = false
		})
}

function createAlertObject() {
	alertObject.value = {
		_index: "",
		_id: alert.value?.alert_context.alert_id,
		_source: alert.value?.alert_source_content
	} as Alert
}

function caseCreated(caseId: string | number) {
	if (alert.value) {
		alert.value.cases = [caseId]
	}
}

function deleted() {
	loadingDelete.value = false
	emit("deleted")
}

watch(checked, val => {
	emit("check", val)
	if (val) {
		emit("checked")
	} else {
		emit("unchecked")
	}
})

onBeforeMount(() => {
	createAlertObject()

	if (!alertData.value && alertId.value) {
		getAlert(alertId.value, () => {
			createAlertObject()
		})
	}
})
</script>

<style lang="scss" scoped>
.show-badges-toggle {
	font-size: 14px;
	cursor: pointer;
	transition: color 0.2s var(--bezier-ease);

	&:hover {
		color: var(--primary-color);
	}
}
</style>
