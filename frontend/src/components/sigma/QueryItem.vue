<template>
	<div>
		<CardEntity :loading :embedded hoverable clickable @click.stop="openDetails()">
			<template #headerMain>#{{ query.id }}</template>
			<template #headerExtra>
				<div class="flex items-center gap-2">
					<span>{{ query.active ? "Active" : "Inactive" }}</span>
					<Icon v-if="query.active" :name="EnabledIcon" :size="14" class="text-success" />
					<Icon v-else :name="DisabledIcon" :size="14" class="text-secondary" />
				</div>
			</template>
			<template #default>
				{{ query.rule_name }}
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<QueryTimeIntervalForm
						v-slot="{ loading: loadingTimeInterval, togglePopup: toggleTimeIntervalPopup }"
						:query
						@updated="updateQuery($event)"
					>
						<Badge type="splitted" bright point-cursor @click.stop="toggleTimeIntervalPopup()">
							<template #iconLeft>
								<n-spin
									:size="12"
									:show="loadingTimeInterval"
									content-class="flex flex-col justify-center"
								>
									<Icon :name="TimeIntervalIcon" />
								</n-spin>
							</template>
							<template #label>Time Interval</template>
							<template #value>
								<div class="flex items-center gap-2">
									{{ query.time_interval || "n/d" }}
									<Icon :name="EditIcon" :size="13" />
								</div>
							</template>
						</Badge>
					</QueryTimeIntervalForm>

					<Badge type="splitted" bright fluid class="!hidden sm:!flex">
						<template #iconLeft>
							<Icon :name="TimeIcon" />
						</template>
						<template #label>Last execution time</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{
									query.last_execution_time
										? formatDate(query.last_execution_time, dFormats.datetimesec)
										: "n/d"
								}}
							</div>
						</template>
					</Badge>
				</div>
			</template>

			<template #footerExtra>
				<QueryDeleteOne
					v-slot="{ loading: loadingDelete, togglePopup: toggleDeletePopup }"
					:query
					@deleted="emit('deleted', query)"
				>
					<n-button quaternary size="tiny" :loading="loadingDelete" @click.stop="toggleDeletePopup()">
						Delete
					</n-button>
				</QueryDeleteOne>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(480px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col !p-0"
				:title="`#${query.id}`"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				<QueryDetails :query @deleted="emitDelete(query)" @updated="updateQuery($event)" />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SigmaQuery } from "@/types/sigma.d"
import { NButton, NCard, NModal, NSpin } from "naive-ui"
import { ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import QueryDeleteOne from "./actionsProviders/QueryDeleteOne.vue"
import QueryTimeIntervalForm from "./actionsProviders/QueryTimeIntervalForm.vue"
import QueryDetails from "./QueryDetails.vue"

const props = defineProps<{
	query: SigmaQuery
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "deleted", value: SigmaQuery): void
	(e: "updated", value: SigmaQuery): void
}>()

const { query, embedded } = toRefs(props)

const TimeIcon = "carbon:time"
const EditIcon = "uil:edit-alt"
const EnabledIcon = "carbon:circle-solid"
const DisabledIcon = "carbon:subtract-alt"
const TimeIntervalIcon = "material-symbols:autoplay"

const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

function updateQuery(updatedQuery: SigmaQuery) {
	emit("updated", updatedQuery)
}

function emitDelete(updatedQuery: SigmaQuery) {
	closeDetails()
	emit("deleted", updatedQuery)
}

function openDetails() {
	showDetails.value = true
}

function closeDetails() {
	showDetails.value = false
}
</script>
