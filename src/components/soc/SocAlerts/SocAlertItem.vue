<template>
	<n-spin
		:show="loading"
		:description="loadingDelete ? 'Deleting Soc Alert' : 'Loading Soc Alert'"
		class="soc-alert-item flex flex-col gap-0"
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
					<Icon
						v-if="!hideBookmarkAction"
						:name="loadingBookmark ? LoadingIcon : isBookmark ? StarActiveIcon : StarIcon"
						:size="16"
						@click="toggleBookmark()"
						class="toggler-bookmark"
						:class="{ active: isBookmark }"
					></Icon>
				</div>
				<div class="time">
					<n-popover overlap placement="top-end" style="max-height: 240px" scrollable to="body">
						<template #trigger>
							<div class="flex items-center gap-2 cursor-help">
								<span>
									{{ formatDate(alert.alert_creation_time) }}
								</span>
								<Icon :name="TimeIcon" :size="16"></Icon>
							</div>
						</template>
						<div class="flex flex-col py-2 px-1">
							<SocAlertTimeline :alert="alert" />
						</div>
					</n-popover>
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
					:caseId="caseId"
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
					<div class="badges-box flex flex-wrap items-center gap-3 mt-3">
						<n-tooltip placement="top-start" trigger="hover">
							<template #trigger>
								<Badge type="splitted" hint-cursor>
									<template #iconLeft>
										<Icon :name="StatusIcon" :size="14"></Icon>
									</template>
									<template #label>Status</template>
									<template #value>{{ alert.status?.status_name || "-" }}</template>
								</Badge>
							</template>
							{{ alert.status.status_description }}
						</n-tooltip>
						<Badge type="splitted" :color="alert.severity?.severity_id === 5 ? 'danger' : undefined">
							<template #iconLeft>
								<Icon :name="SeverityIcon" :size="13"></Icon>
							</template>
							<template #label>Severity</template>
							<template #value>{{ alert.severity?.severity_name || "-" }}</template>
						</Badge>
						<Badge type="splitted" class="hide-on-small">
							<template #iconLeft>
								<Icon :name="SourceIcon" :size="13"></Icon>
							</template>
							<template #label>Source</template>
							<template #value>{{ alert.alert_source || "-" }}</template>
						</Badge>
						<Badge type="splitted" class="hide-on-small">
							<template #iconLeft>
								<Icon :name="CustomerIcon" :size="13"></Icon>
							</template>
							<template #label>Customer</template>
							<template #value>{{ alert.customer?.customer_name || "-" }}</template>
						</Badge>

						<SocAssignUser :alert="alert" :users="users" v-slot="{ loading }" @updated="updateAlert">
							<Badge type="active" class="cursor-pointer">
								<template #iconLeft>
									<n-spin :size="16" :show="loading">
										<Icon :name="OwnerIcon" :size="16"></Icon>
									</n-spin>
								</template>
								<template #label>Owner</template>
								<template #value>{{ ownerName || "n/d" }}</template>
							</Badge>
						</SocAssignUser>

						<Badge
							v-if="alert.alert_source_link"
							type="active"
							:href="alert.alert_source_link"
							target="_blank"
							alt="Source link"
							rel="nofollow noopener noreferrer"
						>
							<template #iconRight>
								<Icon :name="LinkIcon" :size="14"></Icon>
							</template>
							<template #label>Source link</template>
						</Badge>
					</div>
				</n-collapse-transition>
			</div>

			<div class="footer-box flex justify-between items-center gap-4">
				<SocAlertItemActions
					v-if="!hideSocCaseAction"
					class="actions-box grow !flex-wrap !justify-start"
					style="flex-direction: initial"
					size="small"
					:caseId="caseId"
					:alertId="alert.alert_id"
					@caseCreated="caseCreated($event)"
					@deleted="deleted()"
					@startDeleting="loadingDelete = true"
				/>
				<div class="time">{{ formatDate(alert.alert_creation_time) }}</div>
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
				<AlertItem :alert="alertObject" :hide-actions="true" class="-mt-4" />
			</n-collapse-item>
		</n-collapse>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-style="padding:0px"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="`SOC Alert: #${alert?.alert_id} - ${alert?.alert_uuid}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24" v-if="alert">
				<n-tab-pane name="Context" tab="Context" display-directive="show:lazy">
					<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
						<KVCard v-for="(value, key) of alert.alert_context" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value ?? "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Note" tab="Note" display-directive="show:lazy">
					<div class="p-7 pt-4">
						{{ alert.alert_note ?? "No notes for this alert" }}
					</div>
				</n-tab-pane>
				<n-tab-pane name="Customer" tab="Customer" display-directive="show:lazy">
					<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
						<KVCard v-for="(value, key) of alert.customer" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value || "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Owner" tab="Owner" display-directive="show:lazy">
					<div class="grid gap-2 px-7 pt-4">
						<Badge
							type="active"
							style="max-width: 145px"
							class="cursor-pointer"
							@click="gotoUsersPage(ownerId)"
						>
							<template #iconRight>
								<Icon :name="LinkIcon" :size="14"></Icon>
							</template>
							<template #label>Go to users page</template>
						</Badge>
					</div>
					<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
						<KVCard>
							<template #key>user_login</template>
							<template #value>
								<SocAssignUser
									:alert="alert"
									:users="users"
									v-slot="{ loading }"
									@updated="updateAlert"
								>
									<div class="flex items-center gap-2 cursor-pointer text-primary-color">
										<n-spin :size="16" :show="loading">
											<Icon :name="EditIcon" :size="16"></Icon>
										</n-spin>
										<span>{{ ownerName || "Assign a user" }}</span>
									</div>
								</SocAssignUser>
							</template>
						</KVCard>
						<KVCard v-if="alert.owner">
							<template #key>user_name</template>
							<template #value>
								<span>#{{ alert.owner.id }}</span>
								{{ alert.owner.user_name }}
							</template>
						</KVCard>
						<KVCard v-if="alert.owner">
							<template #key>user_email</template>
							<template #value>
								{{ alert.owner.user_email }}
							</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="History" tab="History" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SocAlertTimeline :alert="alert" />
					</div>
				</n-tab-pane>
				<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SimpleJsonViewer
							class="vuesjv-override"
							:model-value="socAlertDetail"
							:initialExpandedDepth="1"
						/>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</n-spin>
</template>

<script setup lang="ts">
// TODO: add customer goto function ??
import AlertItem from "@/components/alerts/Alert.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { Alert } from "@/types/alerts.d"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import KVCard from "@/components/common/KVCard.vue"
import SocAlertTimeline from "./SocAlertTimeline.vue"
import SocAssignUser from "./SocAssignUser.vue"
import SocAlertItemActions from "./SocAlertItemActions.vue"
import "@/assets/scss/vuesjv-override.scss"
import Api from "@/api"
import {
	NCollapse,
	useMessage,
	NCollapseItem,
	NPopover,
	NModal,
	NTabs,
	NTabPane,
	NSpin,
	NCheckbox,
	NTooltip,
	NCollapseTransition
} from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import type { SocUser } from "@/types/soc/user.d"
import { useRouter } from "vue-router"

const checked = defineModel<boolean>("checked", { default: false })

const emit = defineEmits<{
	(e: "bookmark", value: boolean): void
	(e: "deleted"): void
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
const { alertData, alertId, isBookmark, highlight, users, embedded, hideSocCaseAction, hideBookmarkAction } =
	toRefs(props)

const ChevronIcon = "carbon:chevron-right"
const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const StatusIcon = "fluent:status-20-regular"
const SeverityIcon = "bi:shield-exclamation"
const SourceIcon = "lucide:arrow-down-right-from-circle"
const CustomerIcon = "carbon:user"
const StarActiveIcon = "carbon:star-filled"
const OwnerIcon = "carbon:user-military"
const StarIcon = "carbon:star"
const EditIcon = "uil:edit-alt"
const LoadingIcon = "eos-icons:loading"

const showDetails = ref(false)
const showBadges = ref(false)
const loadingDelete = ref(false)
const loadingData = ref(false)
const loadingBookmark = ref(false)
const router = useRouter()
const message = useMessage()

const alert = ref(alertData.value || null)

const alertObject = ref<Alert>({} as Alert)

const loading = computed(() => loadingBookmark.value || loadingData.value || loadingDelete.value)
const ownerName = computed(() => alert.value?.owner?.user_login)
const ownerId = computed(() => alert.value?.owner?.id)
const caseId = computed<number | null>(() => (alert.value?.cases?.length ? alert.value?.cases[0] : null))

const socAlertDetail = computed<Partial<SocAlert>>(() => {
	const clone: Partial<SocAlert> = JSON.parse(JSON.stringify(alert.value))

	delete clone.alert_context
	delete clone.alert_source_content
	delete clone.customer
	delete clone.modification_history
	delete clone.alert_note
	delete clone.alert_source_link

	return clone
})

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}

function toggleBookmark() {
	if (alert.value?.alert_id) {
		loadingBookmark.value = true

		const method = isBookmark.value ? "removeAlertBookmark" : "addAlertBookmark"

		Api.soc[method](alert.value.alert_id.toString())
			.then(res => {
				if (res.data.success) {
					emit("bookmark", method === "removeAlertBookmark" ? false : true)
					message.success(res.data?.message || "Stream started.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingBookmark.value = false
			})
	}
}

function updateAlert(alertUpdated: SocAlert) {
	const ownerObject = alertUpdated.owner
	const modificationHistory = alertUpdated.modification_history

	if (alert.value) {
		alert.value.owner = ownerObject
		alert.value.modification_history = modificationHistory
	}
}

function gotoUsersPage(userId?: string | number) {
	router.push({ name: "Soc-Users", query: userId ? { user_id: userId } : {} })
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
	&:not(.embedded) {
		border-radius: var(--border-radius);
		background-color: var(--bg-color);
		border: var(--border-small-050);
	}
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

			.time {
				font-family: var(--font-family-mono);
				text-align: right;
				color: var(--fg-secondary-color);
			}
		}
	}

	&.bookmarked {
		background-color: var(--primary-005-color);
		border-color: var(--primary-030-color);
	}

	&:not(.embedded) {
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
					.badge {
						&.hide-on-small {
							display: none;
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
