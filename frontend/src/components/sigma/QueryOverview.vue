<template>
	<n-spin :show="loading" class="flex flex-col grow" content-class="flex flex-col grow">
		<div class="flex flex-col gap-4 grow justify-between">
			<div class="content-box flex flex-col gap-4 py-3">
				<div class="px-7 flex sm:!flex-row flex-col gap-4">
					<KVCard :color="query.active ? 'success' : undefined" size="lg" class="grow w-full">
						<template #key>
							<div class="flex gap-2 items-center">
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
										class="flex gap-3 items-center"
										:class="{
											'cursor-not-allowed': loadingActive,
											'cursor-pointer': !loadingActive,
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
					</KVCard>

					<KVCard size="lg" class="grow w-full">
						<template #key>
							<div class="flex gap-2 items-center">
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
										class="flex gap-3 items-center"
										:class="{
											'cursor-not-allowed': loadingTimeInterval,
											'cursor-pointer': !loadingTimeInterval,
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
					</KVCard>
				</div>

				<div class="px-7">
					<KVCard>
						<template #key>name</template>
						<template #value>
							{{ query.rule_name ?? "-" }}
						</template>
					</KVCard>
				</div>

				<div class="px-7 grid gap-2 grid-auto-fit-250">
					<KVCard>
						<template #key>last execution time</template>
						<template #value>
							{{
								query.last_execution_time
									? formatDate(query.last_execution_time, dFormats.datetimesec)
									: "n/d"
							}}
						</template>
					</KVCard>

					<KVCard>
						<template #key>last updated</template>
						<template #value>
							{{ query.last_updated ? formatDate(query.last_updated, dFormats.datetimesec) : "n/d" }}
						</template>
					</KVCard>
				</div>
			</div>

			<div class="footer-box px-7 py-4 flex items-center gap-2">
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
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
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
	border-top: var(--border-small-100);
	background-color: var(--bg-secondary-color);
}
</style>
