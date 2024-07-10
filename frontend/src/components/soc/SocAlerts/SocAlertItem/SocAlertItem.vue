<template>
	<n-spin
		:show="loading"
		:description="loadingDelete ? 'Deleting Soc Alert' : 'Loading Soc Alert'"
		class="soc-alert-item flex flex-col gap-0 min-h-36 pb-2"
		:class="{ bookmarked: isBookmark, highlight, embedded }"
		:id="'alert-' + alert?.alert_id"
	>
		<div class="soc-alert-info px-5 py-3 flex flex-col gap-3" v-if="alert">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2 cursor-pointer">
					<div v-if="showCheckbox" class="check-box mr-2">
						<n-checkbox size="large" v-model:checked="checked" />
					</div>
					<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>#{{ alert.alert_id }} - {{ alert.alert_uuid }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
					<SocAlertItemBookmarkToggler
						v-if="!hideBookmarkAction && alert"
						:alert
						:isBookmark
						@bookmark="emit('bookmark', $event)"
					/>
				</div>
				<div class="time">
					<SocAlertItemTime :alert />
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div class="title">{{ alert.alert_title }}</div>
					<div
						class="description mb-2"
						v-if="alert.alert_description && alert.alert_title !== alert.alert_description"
					>
						{{ alert.alert_description }}
					</div>
				</div>
				<SocAlertItemActions
					v-if="!hideSocCaseAction"
					class="actions-box"
					:caseId
					:alertId="alert.alert_id"
					@caseCreated="caseCreated($event)"
					@deleted="deleted()"
					@startDeleting="loadingDelete = true"
				/>
			</div>

			<div>
				<div
					class="show-badges-toggle flex items-center gap-2"
					v-if="showBadgesToggle"
					@click="showBadges = !showBadges"
				>
					{{ showBadges ? "Less info" : "More info" }}
					<span class="transition-transform flex items-center" :class="{ 'rotate-90': showBadges }">
						<Icon :name="ChevronIcon" :size="14"></Icon>
					</span>
				</div>
				<n-collapse-transition :show="!showBadgesToggle || showBadges">
					<SocAlertItemBadges class="badges-box" v-if="alert" :alert :users @updated="updateAlert" />
				</n-collapse-transition>
			</div>

			<div class="footer-box flex justify-between items-center gap-4">
				<SocAlertItemActions
					v-if="!hideSocCaseAction"
					class="actions-box grow !flex-wrap !justify-start"
					style="flex-direction: initial"
					size="small"
					:caseId
					:alertId="alert.alert_id"
					@caseCreated="caseCreated($event)"
					@deleted="deleted()"
					@startDeleting="loadingDelete = true"
				/>
				<div class="time">
					<SocAlertItemTime :alert hide-timeline />
				</div>
			</div>
		</div>
		<n-collapse>
			<template #arrow>
				<div class="mx-5 flex">
					<Icon :name="ChevronIcon"></Icon>
				</div>
			</template>
			<n-collapse-item>
				<template #header>
					<div class="py-3 -ml-2">Alert details</div>
				</template>
				<AlertItem :alert="alertObject" hide-actions class="-mt-4" />
			</n-collapse-item>
		</n-collapse>

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
				<SocAlertItemRecommendation v-if="alert" :alert />
			</template>
			<SocAlertItemDetails v-if="alert" :alert :users @updated="updateAlert" />
		</n-modal>
	</n-spin>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import type { Alert } from "@/types/alerts.d"
import Icon from "@/components/common/Icon.vue"
import { computed, defineAsyncComponent, onBeforeMount, ref, toRefs, watch } from "vue"
import SocAlertItemActions from "./SocAlertItemActions.vue"
import SocAlertItemTime from "./SocAlertItemTime.vue"
import SocAlertItemBookmarkToggler from "./SocAlertItemBookmarkToggler.vue"
import Api from "@/api"
import { NCollapse, useMessage, NCollapseItem, NModal, NSpin, NCheckbox, NCollapseTransition } from "naive-ui"
import type { SocUser } from "@/types/soc/user.d"
const SocAlertItemDetails = defineAsyncComponent(() => import("./SocAlertItemDetails.vue"))
const SocAlertItemBadges = defineAsyncComponent(() => import("./SocAlertItemBadges.vue"))
const SocAlertItemRecommendation = defineAsyncComponent(() => import("./SocAlertItemRecommendation.vue"))
const AlertItem = defineAsyncComponent(() => import("@/components/alerts/Alert.vue"))

const checked = defineModel<boolean>("checked", { default: false })

const emit = defineEmits<{
	(e: "bookmark", value: boolean): void
	(e: "deleted"): void
	(e: "checked"): void
	(e: "unchecked"): void
	(e: "check", value: boolean): void
}>()

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
const InfoIcon = "carbon:information"

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
.soc-alert-item {
	transition: all 0.2s var(--bezier-ease);

	.soc-alert-info {
		border-bottom: var(--border-small-050);

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

		.show-badges-toggle {
			font-size: 14px;
			cursor: pointer;
			transition: color 0.2s var(--bezier-ease);

			&:hover {
				color: var(--primary-color);
			}
		}

		.footer-box {
			font-size: 13px;
			margin-top: 10px;
			display: none;
		}
	}

	&.bookmarked {
		background-color: var(--primary-005-color);
		border-color: var(--primary-030-color);
	}

	&:not(.embedded) {
		border-radius: var(--border-radius);
		background-color: var(--bg-color);
		border: var(--border-small-050);

		&:hover,
		&.highlight {
			border-color: var(--primary-color);
		}
	}

	@container (max-width: 650px) {
		.soc-alert-info {
			.header-box {
				.time {
					display: none;
				}
			}

			.main-box {
				.actions-box {
					display: none;
				}
				.badges-box {
					:deep() {
						.badge {
							&.hide-on-small {
								display: none;
							}
						}
					}
				}
			}
			.footer-box {
				display: flex;
			}
		}
	}
}
</style>
