<template>
	<div class="soc-alerts-list" ref="list">
		<n-split
			direction="horizontal"
			:default-size="splitDefault"
			:resize-trigger-size="26"
			:min="splitMin"
			:max="splitMax"
			v-if="!compactMode"
		>
			<template #1>
				<SocAlertsBookmarks
					:usersList="usersList"
					@bookmark="reloadAlerts()"
					@deleted="itemDeleted($event)"
					@loaded="bookmarksList = $event"
					@mounted="socAlertsBookmarksCTX = $event"
				/>
			</template>
			<template #2>
				<SocAlertsList
					:highlight="highlight"
					:bookmarksList="bookmarksList"
					:usersList="usersList"
					@bookmark="reloadBookmarks()"
					@deleted="reloadBookmarks()"
					@mounted="socAlertsCTX = $event"
				/>
			</template>
			<template #resize-trigger>
				<div class="split-trigger">
					<div class="split-trigger-icon">
						<Icon :name="SplitIcon"></Icon>
					</div>
				</div>
			</template>
		</n-split>

		<template v-else>
			<SocAlertsList
				:highlight="highlight"
				:bookmarksList="bookmarksList"
				:usersList="usersList"
				@bookmark="reloadBookmarks()"
				@deleted="reloadBookmarks()"
				@mounted="socAlertsCTX = $event"
			>
				<template #header>
					<n-button size="small" @click="showBookmarkedDrawer = true">
						<template #icon>
							<Icon :name="StarIcon" :size="14"></Icon>
						</template>
					</n-button>
				</template>
			</SocAlertsList>

			<n-drawer
				v-model:show="showBookmarkedDrawer"
				:width="700"
				style="max-width: 90vw"
				:trap-focus="false"
				display-directive="show"
				placement="left"
			>
				<n-drawer-content title="Alerts list" closable :native-scrollbar="false">
					<SocAlertsBookmarks
						:usersList="usersList"
						@bookmark="reloadAlerts()"
						@deleted="itemDeleted($event)"
						@loaded="bookmarksList = $event"
						@mounted="socAlertsBookmarksCTX = $event"
					/>
				</n-drawer-content>
			</n-drawer>
		</template>

		<n-back-top :visibility-height="300"></n-back-top>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs } from "vue"
import { useMessage, NSplit, NBackTop, NButton, NDrawer, NDrawerContent } from "naive-ui"
import Api from "@/api"
import SocAlertsBookmarks from "./SocAlertsBookmarks.vue"
import SocAlertsList from "./SocAlertsList.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import Icon from "@/components/common/Icon.vue"
import type { SocUser } from "@/types/soc/user.d"
import { useResizeObserver } from "@vueuse/core"

const props = defineProps<{ highlight: string | null | undefined }>()
const { highlight } = toRefs(props)

const SplitIcon = "carbon:draggable"
const StarIcon = "carbon:star-filled"

const message = useMessage()
const bookmarksList = ref<SocAlert[]>([])
const usersList = ref<SocUser[]>([])
const socAlertsBookmarksCTX = ref<{ reload: () => void } | null>(null)
const socAlertsCTX = ref<{ reload: () => void; itemDeleted: (alertId: string, noEmit?: boolean) => void } | null>(null)

const list = ref(null)
const showBookmarkedDrawer = ref(false)
const compactMode = ref(false)
const splitMin = ref(0.25)
const splitMax = ref(0.75)
const splitDefault = ref(0.3)

function reloadBookmarks() {
	socAlertsBookmarksCTX.value?.reload()
}

function reloadAlerts() {
	socAlertsCTX.value?.reload()
}

function itemDeleted(alertId?: string) {
	if (alertId) {
		socAlertsCTX.value?.itemDeleted(alertId, true)
	}
}

function getUsers() {
	Api.soc
		.getUsers()
		.then(res => {
			if (res.data.success) {
				usersList.value = res.data?.users || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
}

useResizeObserver(list, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	compactMode.value = width < 680
	splitMin.value = width < 850 ? 0.5 : 0.25
	splitMax.value = width < 850 ? 0.5 : 0.75
	splitDefault.value = width < 850 ? 0.5 : 0.3

	if (width > 680) {
		showBookmarkedDrawer.value = false
	}
})

onBeforeMount(() => {
	getUsers()
})
</script>

<style lang="scss" scoped>
.soc-alerts-list {
	.n-split {
		:deep() {
			.n-split-pane-1 {
				min-width: 290px;
				max-width: 500px;
			}
		}
	}
	.split-trigger {
		height: 100%;
		width: 3px;
		background-color: var(--border-color);
		display: flex;
		justify-content: center;
		transition: background-color 0.3s var(--bezier-ease);
		margin-left: 11px;

		.split-trigger-icon {
			position: relative;
			top: min(48%, 300px);
			background-color: var(--border-color);
			border-radius: var(--border-radius-small);
			height: 20px;
			display: flex;
			justify-content: center;
			align-items: center;
			transition: background-color 0.3s var(--bezier-ease);
		}

		&:hover {
			background-color: var(--primary-color);

			.split-trigger-icon {
				background-color: var(--primary-color);
			}
		}
	}
}
</style>
