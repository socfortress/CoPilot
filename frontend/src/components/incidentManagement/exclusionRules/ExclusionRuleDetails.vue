<template>
	<n-tabs type="line" animated :tabs-padding="24" class="grow" pane-wrapper-class="flex grow flex-col">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex grow flex-col">
			<n-spin :show="loading" class="flex grow flex-col" content-class="flex grow flex-col">
				<div class="flex flex-col gap-4 p-5 pt-3">
					<div class="grid grid-cols-6 gap-4">
						<CardKV class="col-span-6 md:col-span-2">
							<template #key>name</template>
							<template #value>{{ entity.name }}</template>
						</CardKV>
						<CardKV class="col-span-3 md:col-span-2">
							<template #key>creator</template>
							<template #value>
								<div class="flex flex-col gap-2 py-1">
									<div>
										<span class="text-secondary">by:</span>
										{{ entity.created_by }}
									</div>
									<div>
										<span class="text-secondary">at:</span>
										{{ formatDate(entity.created_at, dFormats.datetimesec) }}
									</div>
								</div>
							</template>
						</CardKV>
						<CardKV class="col-span-3 md:col-span-2">
							<template #key>status</template>
							<template #value>
								<div class="flex h-full w-full items-center justify-center font-sans">
									<ExclusionRuleStatusToggler
										:entity
										@loading="updatingStatus = $event"
										@updated="setStatus($event)"
									/>
								</div>
							</template>
						</CardKV>
					</div>

					<div class="flex flex-wrap items-center gap-3">
						<Badge type="splitted">
							<template #label># ID</template>
							<template #value>{{ entity.id }}</template>
						</Badge>

						<Badge type="splitted" color="primary">
							<template #iconLeft>
								<Icon :name="TargetIcon" />
							</template>
							<template #label>Match count</template>
							<template #value>
								{{ entity.match_count }}
							</template>
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

					<CardKV v-for="(val, key) in properties" :key>
						<template #key>{{ key }}</template>
						<template #value>{{ val }}</template>
					</CardKV>
				</div>
			</n-spin>
		</n-tab-pane>
		<n-tab-pane name="Fields" tab="Fields" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<CardKV v-for="(val, key) in entity.field_matches" :key size="lg">
					<template #key>{{ key }}</template>
					<template #value>
						<CodeSource :code="val" lang="shell" />
					</template>
				</CardKV>
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { ExclusionRule } from "@/types/incidentManagement/exclusionRules.d"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import _pick from "lodash/pick"
import { NSpin, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref, toRefs } from "vue"
import ExclusionRuleStatusToggler from "./ExclusionRuleStatusToggler.vue"

const props = defineProps<{
	entity: ExclusionRule
}>()

const { entity } = toRefs(props)

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const TargetIcon = "zondicons:target"
const dFormats = useSettingsStore().dateFormat
const { gotoCustomer } = useGoto()
const updatingStatus = ref(false)
const loading = computed(() => updatingStatus.value)
const properties = computed(() => _pick(entity.value, ["description", "channel", "title"]))

function setStatus(value: ExclusionRule) {
	entity.value.enabled = value.enabled
}
</script>
