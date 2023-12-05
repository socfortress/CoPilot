<template>
	<n-spin :show="loadingAlerts" :size="14">
		<div class="flex alert-list items-center gap-3" v-if="!loadingAlerts">
			<strong>{{ alertsList.length }}</strong>
			<div class="flex flex-wrap gap-2">
				<n-tooltip v-for="alert of alertsList" :key="alert.alert_id">
					<template #trigger>
						<code class="alert-btn" @click="gotoSocAlert(alert.alert_id)">#{{ alert.alert_id }}</code>
					</template>
					{{ alert.alert_title }}
				</n-tooltip>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import { useMessage, NTooltip, NSpin } from "naive-ui"
import { useRouter } from "vue-router"

const { userId } = defineProps<{
	userId: string | number
}>()

const loadingAlerts = ref(false)
const alertsList = ref<SocAlert[]>([])
const router = useRouter()
const message = useMessage()

function gotoSocAlert(socId: string | number) {
	router.push(`/soc/alerts?id=${socId}`).catch(() => {})
}

function getAlerts() {
	loadingAlerts.value = true

	Api.soc
		.getAlertsByUser(userId.toString())
		.then(res => {
			if (res.data.success) {
				alertsList.value = res.data?.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAlerts.value = false
		})
}

onBeforeMount(() => {
	getAlerts()
})
</script>

<style lang="scss" scoped>
.alert-list {
	max-width: 200px;
	.alert-btn {
		cursor: pointer;
		text-decoration: underline;

		&:hover {
			color: var(--primary-color);
		}
	}
}
</style>
