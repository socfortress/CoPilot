<template>
	<div>
		<CardEntity :loading :embedded hoverable>
			<template #headerMain>{{ entity.name }}</template>
			<template #headerExtra>
				<div class="hidden font-sans sm:block">
					<ExclusionRuleStatusToggler :entity @loading="loading = $event" @updated="setStatus($event)" />
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
								@click.stop="routeCustomer({ code: entity.customer_code }).navigate()"
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
						<ExclusionRuleStatusToggler :entity @loading="loading = $event" @updated="setStatus($event)" />
					</div>

					<EntityDetailsButton
						size="small"
						:route="routeIncidentManagementExclusionRule(entity.id)"
						@view="openDetails()"
					/>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(480px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col p-0!"
				:title="`#${entity.id} • ${entity.name}`"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				<ExclusionRuleOverview :entity @deleted="handleDeleted()" @updated="emit('updated')" />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ExclusionRule } from "@/types/incidentManagement/exclusion-rules"
import { NCard, NModal } from "naive-ui"
import { ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import ExclusionRuleOverview from "./ExclusionRuleOverview.vue"
import ExclusionRuleStatusToggler from "./ExclusionRuleStatusToggler.vue"

const props = defineProps<{
	entity: ExclusionRule
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated"): void
}>()

const { entity } = toRefs(props)

const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const TargetIcon = "zondicons:target"

const loading = ref(false)
const showDetails = ref(false)
const { routeCustomer, routeIncidentManagementExclusionRule } = useNavigation()
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

function handleDeleted() {
	showDetails.value = false
	emit("deleted")
}
</script>
