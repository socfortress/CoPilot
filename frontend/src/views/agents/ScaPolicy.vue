<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeScaPolicy())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="policy" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ policy.name }}</span>
				<span class="text-secondary font-mono text-sm">{{ policy.id }}</span>
			</div>
		</div>

		<n-spin v-if="policyId" :show="loading" class="min-h-40">
			<PolicyCardContent v-if="policy" :policy />
			<n-empty v-else-if="!loading" description="Policy not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid policy" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { ScaPolicyItem } from "@/types/sca"
import { NButton, NEmpty, NSpin } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import PolicyCardContent from "@/components/scaPolicies/PolicyCardContent.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeScaPolicy } = useNavigation()

const BackIcon = "carbon:arrow-left"

const policyId = useRouteParam("policyId")

const { loading, entity: policy } = useEntityDetails<ScaPolicyItem, string>({
	entity: () => null,
	id: () => policyId.value,
	fetch: (id, signal) =>
		Api.sca.getPolicyMetadata(id, signal).then(res => ({
			entity: res.data.success ? (res.data.policy ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Policy not found",
	errorMessage: "An error occurred. Please try again later."
})
</script>
