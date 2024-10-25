<template>
	<n-spin :show="loading">
		<CardStatsMulti title="Healthcheck" hovered class="h-full cursor-pointer" :values @click="gotoHealthcheck()">
			<template #icon>
				<CardStatsIcon
					:icon-name="HealthcheckIcon"
					boxed
					:box-size="30"
					:color="criticalTotal ? style['warning-color'] : undefined"
				></CardStatsIcon>
			</template>
		</CardStatsMulti>
	</n-spin>
</template>

<script setup lang="ts">
import Api from "@/api"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import CardStatsMulti, { type ItemProps } from "@/components/common/cards/CardStatsMulti.vue"
import { useGoto } from "@/composables/useGoto"
import { useThemeStore } from "@/stores/theme"
import { type InfluxDBAlert, InfluxDBAlertLevel } from "@/types/healthchecks.d"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"

const HealthcheckIcon = "ph:heartbeat"
const { gotoHealthcheck } = useGoto()
const message = useMessage()
const loading = ref(false)
const healthcheck = ref<InfluxDBAlert[]>([])
const style = computed(() => useThemeStore().style)
const total = computed<number>(() => {
	return healthcheck.value.length || 0
})
const criticalTotal = computed<number>(() => {
	return healthcheck.value.filter(o => o.level === InfluxDBAlertLevel.Crit).length || 0
})
const values = computed<ItemProps[]>(() => [
	{ value: total.value, label: "Total" },
	{ value: criticalTotal.value, label: "Critical", status: criticalTotal.value ? "warning" : undefined }
])

function getData() {
	loading.value = true

	Api.healthchecks
		.getHealthchecks()
		.then(res => {
			if (res.data.success) {
				healthcheck.value = res.data.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			healthcheck.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.n-spin-container {
	:deep() {
		.n-spin-content {
			height: 100%;
		}
	}
}
</style>
