<template>
	<n-spin :show="loading">
		<CardStatsDouble
			title="Healthcheck"
			first-label="Total"
			:value="total"
			hovered
			class="cursor-pointer"
			second-label="Critical"
			:sub-value="criticalTotal"
			:second-status="criticalTotal ? 'warning' : undefined"
			@click="gotoHealthcheck()"
		>
			<template #icon>
				<CardStatsIcon
					:icon-name="HealthcheckIcon"
					boxed
					:box-size="30"
					:color="criticalTotal ? style['warning-color'] : undefined"
				></CardStatsIcon>
			</template>
		</CardStatsDouble>
	</n-spin>
</template>

<script setup lang="ts">
import Api from "@/api"
import CardStatsDouble from "@/components/common/CardStatsDouble.vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
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
