<template>
	<div>
		<CardEntity :loading :embedded hoverable>
			<template #headerMain>{{ entity.name }}</template>
			<template #headerExtra>
				<div class="hidden font-sans sm:block">
					<ExclusionRuleStatusToggler
						:entity
						@loading="updatingStatus = $event"
						@updated="setStatus($event)"
					/>
				</div>
			</template>
			<template #default>
				{{ entity.title }}
			</template>
			<template #footerMain>
				<div class="hidden flex-wrap items-center gap-3 sm:flex">
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TargetIcon" />
						</template>
						<template #label>Match count</template>
						<template #value>{{ entity.match_count }}</template>
					</Badge>

					<Badge v-if="entity.last_matched_at" type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TimeIcon" />
						</template>
						<template #label>Last match</template>
						<template #value>
							{{ formatDate(entity.last_matched_at, dFormats.datetimesec) }}
						</template>
					</Badge>

					<Badge v-if="entity.customer_code" type="splitted">
						<template #label>Customer</template>
						<template #value>
							<code
								class="text-primary cursor-pointer leading-none"
								@click.stop="gotoCustomer({ code: entity.customer_code })"
							>
								#{{ entity.customer_code }}
								<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
							</code>
						</template>
					</Badge>
				</div>
			</template>

			<template #footerExtra>
				<div class="flex items-center gap-3">
					<div class="block sm:hidden">
						<ExclusionRuleStatusToggler
							:entity
							@loading="updatingStatus = $event"
							@updated="setStatus($event)"
						/>
					</div>

					<n-button size="small" @click.stop="openDetails()">
						<template #icon>
							<Icon :name="DetailsIcon"></Icon>
						</template>
						Details
					</n-button>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(480px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col !p-0"
				:title="`#${entity.id} • ${entity.name}`"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				<n-spin :show="loadingDelete">
					<ExclusionRuleForm v-if="editing" :entity class="p-6" @submitted="updateEntity($event)">
						<template #additionalActions>
							<n-button v-if="editing" @click="editing = false">Close</n-button>
						</template>
					</ExclusionRuleForm>
					<ExclusionRuleDetails v-else :entity />
				</n-spin>

				<template #footer>
					<div v-if="!editing" class="flex items-center justify-end gap-4">
						<n-button text type="error" ghost :loading="loadingDelete" @click="handleDelete">
							<template #icon>
								<Icon :name="DeleteIcon" :size="15"></Icon>
							</template>
							Delete
						</n-button>
						<n-button :disabled="loadingDelete" @click="editing = true">
							<template #icon>
								<Icon :name="EditIcon" :size="14"></Icon>
							</template>
							Edit
						</n-button>
					</div>
				</template>
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ExclusionRule } from "@/types/incidentManagement/exclusionRules.d"
import { NButton, NCard, NModal, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, h, ref, toRefs } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import ExclusionRuleDetails from "./ExclusionRuleDetails.vue"
import ExclusionRuleForm from "./ExclusionRuleForm.vue"
import ExclusionRuleStatusToggler from "./ExclusionRuleStatusToggler.vue"

const props = defineProps<{
	entity: ExclusionRule
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated"): void
}>()

const { entity, embedded } = toRefs(props)

const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const DetailsIcon = "carbon:settings-adjust"
const DeleteIcon = "ph:trash"
const EditIcon = "uil:edit-alt"
const TargetIcon = "zondicons:target"

const message = useMessage()
const dialog = useDialog()
const updatingStatus = ref(false)
const loadingDelete = ref(false)
const loading = computed(() => updatingStatus.value || loadingDelete.value)
const editing = ref(false)
const showDetails = ref(false)
const { gotoCustomer } = useGoto()
const dFormats = useSettingsStore().dateFormat

function openDetails() {
	showDetails.value = true
}

function closeDetails() {
	showDetails.value = false
}

function setStatus(value: ExclusionRule) {
	entity.value.enabled = value.enabled
}

function updateEntity(value: ExclusionRule) {
	entity.value.name = value.name
	entity.value.description = value.description
	entity.value.channel = value.channel
	entity.value.title = value.title
	entity.value.field_matches = value.field_matches
	entity.value.enabled = value.enabled
	entity.value.customer_code = value.customer_code

	editing.value = false
	emit("updated")
}

function deleteExclusionRules() {
	loadingDelete.value = true

	Api.incidentManagement.exclusionRules
		.deleteExclusionRules(entity.value.id)
		.then(res => {
			if (res.data.success) {
				showDetails.value = false
				emit("deleted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDelete.value = false
		})
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the Exclusion Rule: <strong>${entity.value.name}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteExclusionRules()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}
</script>
