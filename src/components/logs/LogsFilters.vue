<template>
	<div class="py-1 flex flex-col gap-2">
		<div class="px-3 flex items-center justify-between gap-4">
			<small>Filter by:</small>
			<n-select
				v-model:value="filterType"
				:options="filtersAvailable"
				placeholder="Select"
				size="tiny"
				clearable
				class="!w-24"
			/>
		</div>
		<div class="px-3 !w-72">
			<div class="flex grow" v-if="filterType === 'userId'">
				<n-select
					v-if="userIdOptions.length"
					v-model:value="filterUserId"
					:options="userIdOptions"
					:loading="loadingUsers"
					:disabled="loadingUsers"
					:placeholder="loadingUsers ? 'Loading users...' : 'Select User'"
					class="grow"
				/>
				<n-input
					v-model:value="filterUserId"
					:loading="loadingUsers"
					:disabled="loadingUsers"
					:placeholder="loadingUsers ? 'Loading users...' : 'Insert User ID'"
					class="grow"
					v-else
				/>
			</div>
			<n-select
				v-if="filterType === 'eventType'"
				v-model:value="filterEventType"
				:options="eventTypeOptions"
				placeholder="Event"
				class="grow"
			/>
			<n-input-group v-if="filterType === 'timeRange'">
				<n-select
					v-model:value="filterTimeRange.unit"
					:options="unitOptions"
					placeholder="Time unit"
					class="!w-40"
				/>
				<n-input-number v-model:value="filterTimeRange.time" :min="1" placeholder="Time" class="grow" />
			</n-input-group>
		</div>
		<div class="px-3 flex justify-end gap-2">
			<n-button size="small" @click="close()" secondary>Close</n-button>
			<n-button size="small" @click="submit()" type="primary" secondary>Submit</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, watch, toRefs } from "vue"
import { NButton, NSelect, NInputGroup, NInputNumber, NInput } from "naive-ui"
import _cloneDeep from "lodash/cloneDeep"
import _toSafeInteger from "lodash/toSafeInteger"
import type { LogsQueryEventType, LogsQueryTimeRange, LogsQueryTypes, LogsQueryValues } from "@/api/logs"
import Api from "@/api"
import { LogEventType } from "@/types/logs.d"
import type { AuthUser } from "@/types/auth.d"

const emit = defineEmits<{
	(e: "close"): void
	(e: "submit"): void
	(e: "update:filtered", value: boolean): void
}>()

const type = defineModel<LogsQueryTypes | null>("type", { default: null })
const value = defineModel<LogsQueryValues | null>("value", { default: null })

const props = defineProps<{ users?: AuthUser[]; fetchingUsers?: boolean }>()
const { users, fetchingUsers } = toRefs(props)

const loadingUsers = ref(false)

watch(fetchingUsers, val => {
	loadingUsers.value = val
})

const filtered = computed(() => type.value !== null && value.value !== null)

const filtersAvailable: { label: string; value: LogsQueryTypes | "" }[] = [
	{ label: "User", value: "userId" },
	{ label: "Event", value: "eventType" },
	{ label: "Time", value: "timeRange" }
]

const filterType = ref<LogsQueryTypes | null>(null)
const filterValue = ref<LogsQueryValues | null>(null)

const filterTimeRange = ref({
	unit: "h",
	time: 1
})

const unitOptions: { label: string; value: "h" | "d" | "w" }[] = [
	{ label: "Hours", value: "h" },
	{ label: "Days", value: "d" },
	{ label: "Weeks", value: "w" }
]

const filterEventType = ref<LogsQueryEventType>(LogEventType.INFO)

const eventTypeOptions: { label: string; value: LogsQueryEventType }[] = [
	{ label: "Info", value: LogEventType.INFO },
	{ label: "Error", value: LogEventType.ERROR }
]

const filterUserId = ref<string | null>(null)

const userIdOptions = ref<{ label: string; value: string }[]>([])

watch(
	filtered,
	val => {
		emit("update:filtered", val)
	},
	{ immediate: true }
)

function close() {
	emit("close")
}

function submit() {
	if (filterType.value === null) {
		filterValue.value = null
	}
	if (filterType.value === "timeRange") {
		filterValue.value = (filterTimeRange.value.time + filterTimeRange.value.unit) as LogsQueryTimeRange
	}
	if (filterType.value === "eventType") {
		filterValue.value = filterEventType.value
	}
	if (filterType.value === "userId") {
		filterValue.value = filterUserId.value
	}

	type.value = _cloneDeep(filterType.value)
	value.value = _cloneDeep(filterValue.value)

	emit("submit")
}

function getUsers() {
	loadingUsers.value = true

	Api.auth
		.getUsers()
		.then(res => {
			if (res.data.success) {
				setUsers(res.data?.users)
			}
		})
		.finally(() => {
			loadingUsers.value = false
		})
}

function setUsers(users: AuthUser[]) {
	userIdOptions.value = (users || []).map(o => ({
		label: `#${o.id} - ${o.username}`,
		value: o.id + ""
	}))
}

onBeforeMount(() => {
	if (users.value !== undefined) {
		setUsers(users.value)
	} else {
		getUsers()
	}

	filterType.value = _cloneDeep(type.value)
	filterValue.value = _cloneDeep(value.value)

	if (filterValue.value) {
		if (filterType.value === "timeRange") {
			filterTimeRange.value.unit = filterValue.value[filterValue.value?.length - 1]
			filterTimeRange.value.time = _toSafeInteger(filterValue.value.slice(0, -1))
		}
		if (filterType.value === "eventType") {
			filterEventType.value = filterValue.value as LogsQueryEventType
		}
		if (filterType.value === "userId") {
			filterUserId.value = filterValue.value
		}
	}
})
</script>
