<template>
	<div class="sigma-query-item" :class="{ embedded }" @click="openDetails()">
		<n-spin :show="loading">
			<div class="flex flex-col">
				<div class="header-box px-5 py-3 pb-0 flex justify-between items-center">
					<div class="id flex items-center gap-2 cursor-pointer" @click="openDetails()">
						<span>#{{ query.id }}</span>
					</div>
					<div class="status flex gap-2 items-center">
						<span>{{ query.active ? "Active" : "Inactive" }}</span>
						<Icon v-if="query.active" :name="EnabledIcon" :size="14" class="text-success-color"></Icon>
						<Icon v-else :name="DisabledIcon" :size="14" class="text-secondary-color"></Icon>
					</div>
				</div>

				<div class="main-box flex flex-col gap-3 px-5 py-3">
					<div class="content flex flex-col gap-1 grow">
						<div class="title">
							{{ query.rule_name }}
						</div>
					</div>
				</div>

				<div class="footer-box px-5 py-3 flex justify-between items-center gap-4">
					<div class="badges-box flex flex-wrap items-center gap-3">
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
								<template #label>
									Time Interval
								</template>
								<template #value>
									<div class="flex gap-2 items-center">
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
							<template #label>
								Last execution time
							</template>
							<template #value>
								<div class="flex gap-2 items-center">
									{{
										query.last_execution_time
											? formatDate(query.last_execution_time, dFormats.datetimesec)
											: "n/d"
									}}
								</div>
							</template>
						</Badge>
					</div>
					<div class="actions-box">
						<QueryDeleteOne
							v-slot="{ loading: loadingDelete, togglePopup: toggleDeletePopup }"
							:query
							@deleted="emit('deleted', query)"
						>
							<n-button quaternary size="tiny" :loading="loadingDelete" @click.stop="toggleDeletePopup()">
								Delete
							</n-button>
						</QueryDeleteOne>
					</div>
				</div>
			</div>
		</n-spin>

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
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NButton, NCard, NModal, NSpin } from "naive-ui"
import { ref, toRefs } from "vue"
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

<style lang="scss" scoped>
.sigma-query-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);
	overflow: hidden;
	cursor: pointer;

	.header-box {
		font-size: 13px;

		.id {
			color: var(--fg-secondary-color);
			font-family: var(--font-family-mono);
			word-break: break-word;
			line-height: 1.2;
		}
	}
	.main-box {
		.content {
			word-break: break-word;
		}
	}

	.footer-box {
		border-top: var(--border-small-100);
		font-size: 13px;
		background-color: var(--bg-secondary-color);
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px var(--primary-color);
	}
}
</style>
