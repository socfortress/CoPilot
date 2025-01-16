<template>
	<n-spin :show="loading" class="flex grow flex-col" content-class="flex flex-col grow">
		<div class="flex grow flex-col justify-between gap-4">
			<div class="content-box flex flex-col gap-4 py-3">
				<div class="flex flex-col gap-4 px-7 sm:!flex-row">
					<CardKV :color="query.active ? 'success' : undefined" size="lg" class="w-full grow">
						<template #key>
							<div class="flex items-center gap-2">
								<Icon :name="query.active ? EnabledIcon : DisabledIcon" />
								<span>Status</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<QueryActiveForm
									v-slot="{ loading: loadingActive, togglePopup: toggleActivePopup }"
									:query
									@updated="updateQuery($event)"
								>
									<div
										class="flex items-center gap-3"
										:class="{
											'cursor-not-allowed': loadingActive,
											'cursor-pointer': !loadingActive
										}"
										@click.stop="toggleActivePopup()"
									>
										<span>{{ query.active ? "Active" : "Inactive" }}</span>
										<n-spin
											:size="14"
											:show="loadingActive"
											content-class="flex flex-col justify-center"
										>
											<Icon :name="EditIcon" />
										</n-spin>
									</div>
								</QueryActiveForm>
							</div>
						</template>
					</CardKV>

					<CardKV size="lg" class="w-full grow">
						<template #key>
							<div class="flex items-center gap-2">
								<Icon :name="TimeIntervalIcon" />
								<span>Time Interval</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<QueryTimeIntervalForm
									v-slot="{ loading: loadingTimeInterval, togglePopup: toggleTimeIntervalPopup }"
									:query
									@updated="updateQuery($event)"
								>
									<div
										class="flex items-center gap-3"
										:class="{
											'cursor-not-allowed': loadingTimeInterval,
											'cursor-pointer': !loadingTimeInterval
										}"
										@click.stop="toggleTimeIntervalPopup()"
									>
										<span>{{ query.time_interval || "n/d" }}</span>
										<n-spin
											:size="14"
											:show="loadingTimeInterval"
											content-class="flex flex-col justify-center"
										>
											<Icon :name="EditIcon" />
										</n-spin>
									</div>
								</QueryTimeIntervalForm>
							</div>
						</template>
					</CardKV>
				</div>

				<div class="px-7">
					<CardKV>
						<template #key>name</template>
						<template #value>
							{{ query.rule_name ?? "-" }}
						</template>
					</CardKV>
				</div>

				<div class="grid-auto-fit-250 grid gap-2 px-7">
					<CardKV>
						<template #key>last execution time</template>
						<template #value>
							{{
								query.last_execution_time
									? formatDate(query.last_execution_time, dFormats.datetimesec)
									: "n/d"
							}}
						</template>
					</CardKV>

					<CardKV>
						<template #key>last updated</template>
						<template #value>
							{{ query.last_updated ? formatDate(query.last_updated, dFormats.datetimesec) : "n/d" }}
						</template>
					</CardKV>
				</div>
			</div>

			<div class="footer-box bg-secondary flex items-center gap-2 px-7 py-4">
				<div class="grow"></div>

				<QueryDeleteOne
					v-slot="{ loading: loadingDelete, togglePopup: toggleDeletePopup }"
					:query
					@deleted="emit('deleted', query)"
				>
					<n-button type="error" secondary :loading="loadingDelete" @click.stop="toggleDeletePopup()">
						<template #icon>
							<Icon :name="TrashIcon" />
						</template>
						Delete
					</n-button>
				</QueryDeleteOne>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { SigmaQuery } from "@/types/sigma.d"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NButton, NSpin } from "naive-ui"
import { ref, toRefs } from "vue"
import QueryActiveForm from "./actionsProviders/QueryActiveForm.vue"
import QueryDeleteOne from "./actionsProviders/QueryDeleteOne.vue"
import QueryTimeIntervalForm from "./actionsProviders/QueryTimeIntervalForm.vue"

const props = defineProps<{ query: SigmaQuery }>()

const emit = defineEmits<{
	(e: "deleted", value: SigmaQuery): void
	(e: "updated", value: SigmaQuery): void
}>()

const { query } = toRefs(props)

const TrashIcon = "carbon:trash-can"
const TimeIntervalIcon = "material-symbols:autoplay"
const EditIcon = "uil:edit-alt"
const EnabledIcon = "carbon:circle-solid"
const DisabledIcon = "carbon:subtract-alt"

const dFormats = useSettingsStore().dateFormat
const loading = ref(false)

function updateQuery(updatedQuery: SigmaQuery) {
	emit("updated", updatedQuery)
}
</script>

<style lang="scss" scoped>
.footer-box {
	border-top: 1px solid var(--border-color);
}
</style>
