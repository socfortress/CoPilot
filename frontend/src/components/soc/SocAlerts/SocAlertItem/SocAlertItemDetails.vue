<template>
	<n-tabs v-if="alert" type="line" animated :tabs-padding="24">
		<n-tab-pane name="Context" tab="Context" display-directive="show:lazy">
			<SocAlertItemContext :alert="alert" class="p-7 pt-4" />
		</n-tab-pane>
		<n-tab-pane name="Note" tab="Note" display-directive="show:lazy">
			<div class="p-7 pt-4">
				{{ alert.alert_note ?? "No notes for this alert" }}
			</div>
		</n-tab-pane>
		<n-tab-pane name="Customer" tab="Customer" display-directive="show:lazy">
			<div class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
				<CardKV v-for="(value, key) of alert.customer" :key="key">
					<template #key>
						{{ key }}
					</template>
					<template #value>
						<template v-if="key === 'customer_code' && value && value !== 'Customer Not Found'">
							<code
								class="text-primary cursor-pointer"
								@click="routeCustomer({ code: value.toString() })"
							>
								#{{ value }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
						<template v-else>
							{{ value || "-" }}
						</template>
					</template>
				</CardKV>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Owner" tab="Owner" display-directive="show:lazy">
			<div class="grid gap-2 px-7 pt-4">
				<Badge type="active" style="max-width: 145px" class="cursor-pointer" @click="routeSocUsers(ownerId)">
					<template #iconRight>
						<Icon :name="LinkIcon" :size="14" />
					</template>
					<template #label>Go to users page</template>
				</Badge>
			</div>
			<div class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
				<CardKV>
					<template #key>user_login</template>
					<template #value>
						<SocAssignUser
							v-slot="{ loading }"
							:alert="alert"
							:users="users"
							@updated="emit('updated', $event)"
						>
							<div class="text-primary flex cursor-pointer items-center gap-2">
								<n-spin :size="16" :show="loading">
									<Icon :name="EditIcon" :size="16" />
								</n-spin>
								<span>{{ ownerName || "Assign a user" }}</span>
							</div>
						</SocAssignUser>
					</template>
				</CardKV>
				<CardKV v-if="alert.owner">
					<template #key>user_name</template>
					<template #value>
						<span>#{{ alert.owner.id }}</span>
						{{ alert.owner.user_name }}
					</template>
				</CardKV>
				<CardKV v-if="alert.owner">
					<template #key>user_email</template>
					<template #value>
						{{ alert.owner.user_email }}
					</template>
				</CardKV>
			</div>
		</n-tab-pane>
		<n-tab-pane name="History" tab="History" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<SocAlertItemTimeline :alert="alert" />
			</div>
		</n-tab-pane>
		<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<SimpleJsonViewer class="vuesjv-override" :model-value="socAlertDetail" :initial-expanded-depth="1" />
			</div>
		</n-tab-pane>
		<n-tab-pane name="Assets" tab="Assets" display-directive="show:lazy">
			<SocAlertAssetsList v-if="alert" :alert-id="alert.alert_id" />
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocUser } from "@/types/soc/user.d"
import { NSpin, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import "@/assets/scss/overrides/vuesjv-override.scss"

const { alert } = defineProps<{
	alert: SocAlert
	users?: SocUser[]
}>()
const emit = defineEmits<{
	(e: "updated", value: SocAlert): void
}>()
const SocAlertItemTimeline = defineAsyncComponent(() => import("./SocAlertItemTimeline.vue"))
const SocAssignUser = defineAsyncComponent(() => import("./SocAssignUser.vue"))
const SocAlertItemContext = defineAsyncComponent(() => import("./SocAlertItemContext.vue"))
const SocAlertAssetsList = defineAsyncComponent(() => import("../SocAlertAssets/SocAlertAssetsList.vue"))

const LinkIcon = "carbon:launch"
const EditIcon = "uil:edit-alt"

const { routeCustomer, routeSocUsers } = useNavigation()

const ownerName = computed(() => alert?.owner?.user_login)
const ownerId = computed(() => alert?.owner?.id)

const socAlertDetail = computed<Partial<SocAlert>>(() => {
	const clone: Partial<SocAlert> = JSON.parse(JSON.stringify(alert))

	delete clone.alert_context
	delete clone.alert_source_content
	delete clone.customer
	delete clone.modification_history
	delete clone.alert_note
	delete clone.alert_source_link

	return clone
})
</script>
