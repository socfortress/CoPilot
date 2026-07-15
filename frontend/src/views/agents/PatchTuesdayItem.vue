<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routePatchTuesdayItem())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate font-mono text-lg font-semibold">{{ cve }}</span>
				<span v-if="item" class="text-secondary text-sm">{{ item.affected.product }}</span>
				<span class="text-secondary font-mono text-sm">{{ cycle }}</span>
			</div>
		</div>

		<n-spin v-if="cycle && cve" :show="loading" class="min-h-40">
			<PatchTuesdayDetail v-if="item" :item />
			<n-empty v-else-if="!loading" description="CVE not found in this cycle" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid CVE" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { PatchTuesdayItem } from "@/types/patch-tuesday"
import { NButton, NEmpty, NSpin } from "naive-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"
import patchTuesdayApi from "@/api/endpoints/patch-tuesday"
import Icon from "@/components/common/Icon.vue"
import PatchTuesdayDetail from "@/components/patchTuesday/PatchTuesdayDetail.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const route = useRoute()
const { goBack, routePatchTuesdayItem } = useNavigation()

const BackIcon = "carbon:arrow-left"

const cycle = useRouteParam("cycle")
const cve = useRouteParam("cve")
// product disambiguates a CVE that affects several products in the same cycle
const product = computed(() => (route.query.product ? String(route.query.product) : undefined))

// no by-id endpoint: search the CVE within its cycle, filtered to this product
const { loading, entity: item } = useEntityDetails<PatchTuesdayItem, string>({
	entity: () => null,
	id: () => (cycle.value && cve.value ? `${cycle.value}|${cve.value}|${product.value ?? ""}` : null),
	fetch: (_id, signal) =>
		patchTuesdayApi
			.searchCVEs(
				{ cve_ids: [cve.value as string], cycle: cycle.value as string, product: product.value },
				signal
			)
			.then(res => ({
				entity: res.data.success ? (res.data.items?.[0] ?? null) : null,
				message: res.data.message
			})),
	notFoundMessage: "CVE not found in this cycle",
	errorMessage: "An error occurred. Please try again later."
})
</script>
