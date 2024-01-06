<template>
	<div class="soc-alerts-list">
		<n-split
			direction="horizontal"
			:default-size="compactMode ? 0 : 0.4"
			:resize-trigger-size="26"
			:disabled="compactMode"
			:min="compactMode ? 0 : 0.25"
			:max="compactMode ? 1 : 0.75"
		>
			<template #1 v-if="!compactMode">
				<SocAlertsBookmarks
					class="my-3"
					:usersList="usersList"
					@bookmark="reloadAlerts()"
					@loaded="bookmarksList = $event"
				/>
			</template>
			<template #2>
				<SocAlertsList
					class="my-3"
					:highlight="highlight"
					:bookmarksList="bookmarksList"
					:usersList="usersList"
					@bookmark="reloadBookmarks()"
				/>
			</template>
			<template #resize-trigger v-if="!compactMode">
				<div class="split-trigger">
					<div class="split-trigger-icon">
						<Icon :name="SplitIcon"></Icon>
					</div>
				</div>
			</template>
		</n-split>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs } from "vue"
import { useMessage, NSplit } from "naive-ui"
import Api from "@/api"
import SocAlertsBookmarks from "./SocAlertsBookmarks.vue"
import SocAlertsList from "./SocAlertsList.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import Icon from "@/components/common/Icon.vue"
import type { SocUser } from "@/types/soc/user.d"

const props = defineProps<{ highlight: string | null | undefined }>()
const { highlight } = toRefs(props)

const SplitIcon = "carbon:draggable"

const message = useMessage()
const bookmarksList = ref<SocAlert[]>([])
const usersList = ref<SocUser[]>([])

const pageSize = ref(50)
const sort = ref<"desc" | "asc">("desc")
const alertTitle = ref("")
const compactMode = ref(false)

function reloadBookmarks() {}
function reloadAlerts() {}

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

onBeforeMount(() => {
	getUsers()
})
</script>

<style lang="scss" scoped>
.soc-alerts-list {
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
			top: min(50%, 200px);
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
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
