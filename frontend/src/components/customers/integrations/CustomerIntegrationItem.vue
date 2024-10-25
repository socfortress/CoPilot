<template>
	<div>
		<CardEntity hoverable :embedded>
			<template #default>
				{{ serviceName }}
			</template>

			<template v-if="integration.deployed" #footerMain>
				<Badge type="active">
					<template #iconLeft>
						<Icon :name="DeployIcon" :size="13"></Icon>
					</template>
					<template #value>Deployed</template>
				</Badge>
			</template>
			<template #footerExtra>
				<div class="flex flex-wrap gap-3">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="InfoIcon"></Icon>
						</template>
						Details
					</n-button>

					<CustomerIntegrationActions
						class="flex flex-wrap gap-3"
						:integration
						hide-delete-button
						size="small"
						@deployed="emit('deployed')"
						@deleted="emit('deleted')"
					/>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="serviceName"
			:bordered="false"
			segmented
		>
			<div class="grid-auto-fit-200 grid gap-2">
				<CardKV v-for="ak of authKeys" :key="ak.key">
					<template #key>
						{{ ak.key }}
					</template>
					<template #value>
						{{ ak.value || "-" }}
					</template>
				</CardKV>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CustomerIntegration } from "@/types/integrations.d"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import _uniqBy from "lodash/uniqBy"
import { NButton, NModal } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import CustomerIntegrationActions from "./CustomerIntegrationActions.vue"

const props = defineProps<{
	integration: CustomerIntegration
	embedded?: boolean
}>()
const emit = defineEmits<{
	(e: "deployed"): void
	(e: "deleted"): void
}>()

const { integration, embedded } = toRefs(props)

const DeployIcon = "carbon:deploy"
const InfoIcon = "carbon:information"

const showDetails = ref(false)
const serviceName = computed(() => integration.value.integration_service_name)
const authKeys = computed(() => {
	const keys: { key: string; value: string }[] = []

	for (const subscriptions of integration.value.integration_subscriptions) {
		for (const ak of subscriptions.integration_auth_keys) {
			keys.push({
				key: ak.auth_key_name,
				value: ak.auth_value
			})
		}
	}

	return _uniqBy(keys, "key")
})
</script>
