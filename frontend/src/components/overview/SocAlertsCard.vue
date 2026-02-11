<template>
	<n-spin :show="loading">
		<CardStats
			title="SOC Alerts"
			:value="total"
			:vertical="vertical"
			hovered
			class="h-full cursor-pointer"
			@click="gotoSocAlerts()"
		>
			<template #icon>
				<CardStatsIcon :icon-name="SOCIcon" boxed :box-size="40"></CardStatsIcon>
			</template>
		</CardStats>
	</n-spin>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import CardStats from "@/components/common/cards/CardStats.vue"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import { useNavigation } from "@/composables/useNavigation"

const props = defineProps<{
	vertical?: boolean
}>()
const { vertical } = toRefs(props)

const SOCIcon = "carbon:security"
const { gotoSocAlerts } = useNavigation()
const message = useMessage()
const loading = ref(false)
const alerts = ref<SocAlert[]>([])

const total = computed<number>(() => {
	return alerts.value.length || 0
})

function getData() {
	loading.value = true

	Api.soc
		.getAlerts()
		.then(res => {
			if (res.data.success) {
				alerts.value = res.data?.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
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
