<template>
	<n-popover trigger="click" :show-arrow="false" to="body" @update:show="loadList">
		<template #trigger>
			<n-button :size :focusable="false" :loading="!!linkingCaseId || !!linkingAlertId" :secondary>
				{{ label || "Link Alert" }}
			</n-button>
		</template>

		<n-spin :show="loading" class="min-h-50 max-w-100 min-w-50">
			<div class="mt-1 flex flex-col gap-2">
				<div class="flex flex-col gap-2">
					<CardEntity
						v-for="item in cases"
						:key="item.id"
						size="small"
						embedded
						main-box-class="p-1!"
						header-box-class="flex-nowrap!"
						hoverable
					>
						<template #header-main>
							<div class="px-1">#{{ item.id }} - {{ item.case_name }}</div>
						</template>
						<template #header-extra>
							<n-button
								type="primary"
								size="tiny"
								:loading="linkingCaseId === item.id"
								:disabled="item.alerts.some(alert => alert.id === props.alertId)"
								@click="linkAlert(item.id, props.alertId || 0)"
							>
								<template #icon>
									<Icon name="carbon:link" />
								</template>
								Link
							</n-button>
						</template>
					</CardEntity>

					<CardEntity
						v-for="item in alerts"
						:key="item.id"
						size="small"
						embedded
						main-box-class="p-1!"
						header-box-class="flex-nowrap!"
						hoverable
					>
						<template #header-main>
							<div class="px-1">#{{ item.id }} - {{ item.alert_name }}</div>
						</template>
						<template #header-extra>
							<n-button
								type="primary"
								size="tiny"
								:loading="linkingAlertId === item.id"
								:disabled="item.linked_cases.some(caseData => caseData.id === props.caseId)"
								@click="linkAlert(props.caseId || 0, item.id)"
							>
								<template #icon>
									<Icon name="carbon:link" />
								</template>
								Link
							</n-button>
						</template>
					</CardEntity>
				</div>
				<div class="flex justify-end">
					<n-pagination
						v-if="pagination.total > pagination.pageSize"
						v-model:page="pagination.page"
						:page-size="pagination.pageSize"
						:item-count="pagination.total"
						:page-slot="6"
						size="small"
					/>
				</div>
			</div>
		</n-spin>
	</n-popover>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { Alert } from "@/types/alerts"
import type { Case } from "@/types/cases"
import type { ApiError, Pagination } from "@/types/common"
import { useDebounceFn } from "@vueuse/core"
import { NButton, NPagination, NPopover, NSpin, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	alertId?: number
	caseId?: number
	label?: string
	secondary?: boolean
	size?: ButtonSize
}>()

const emit = defineEmits<{
	(e: "linked", value: number): void
}>()

const linkingCaseId = ref<number | null>(null)
const linkingAlertId = ref<number | null>(null)
const loading = ref(false)
const message = useMessage()
const pagination = ref({
	page: 1,
	pageSize: 5,
	total: 0
})
const cases = ref<Case[]>([])
const alerts = ref<Alert[]>([])

function linkAlert(caseId: number, alertId: number) {
	if (!caseId || !alertId) {
		message.error("Case and alert IDs are required")
		return
	}

	linkingCaseId.value = caseId
	linkingAlertId.value = alertId

	Api.cases
		.linkCaseToAlert(caseId, alertId)
		.then(res => {
			if (res.data.success) {
				emit("linked", alertId)
				message.success(res.data?.message || "Alert linked to case successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			linkingCaseId.value = null
			linkingAlertId.value = null
		})
}

const loadList = useDebounceFn(async () => {
	loading.value = true

	try {
		const paginationPayload: Pagination = {
			page: pagination.value.page,
			pageSize: pagination.value.pageSize,
			order: "desc"
		}

		const method = props.alertId ? Api.cases.getCases(paginationPayload) : Api.alerts.getAlerts(paginationPayload)

		const response = await method

		if (props.alertId && "cases" in response.data) {
			cases.value = response.data?.cases || []
		}
		if (props.caseId && "alerts" in response.data) {
			alerts.value = response.data?.alerts || []
		}

		pagination.value.total = response.data?.total || 0
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}, 300)

watch(() => pagination.value.page, loadList)
</script>
