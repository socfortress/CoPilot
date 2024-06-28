<template>
	<n-spin :show="loading">
		<CardStatsDouble
			title="Healthcheck"
			firstLabel="Total"
			:value="total"
			hovered
			class="cursor-pointer"
			@click="gotoHealthcheck()"
			secondLabel="Critical"
			:subValue="criticalTotal"
			:secondStatus="criticalTotal ? 'warning' : undefined"
		>
			<template #icon>
				<CardStatsIcon
					:iconName="HealthcheckIcon"
					boxed
					:boxSize="30"
					:color="criticalTotal ? style['warning-color'] : undefined"
				></CardStatsIcon>
			</template>
		</CardStatsDouble>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref } from "vue"
import CardStatsDouble from "@/components/common/CardStatsDouble.vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import Api from "@/api"
import { useMessage, NSpin } from "naive-ui"
import { InfluxDBAlertLevel, type InfluxDBAlert } from "@/types/healthchecks.d"
import { useThemeStore } from "@/stores/theme"
import { useGoto } from "@/composables/useGoto"

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
