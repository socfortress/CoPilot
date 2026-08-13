<template>
	<div class="flex flex-col gap-4">
		<div v-if="showMeta" class="flex flex-col gap-1">
			<div :class="expanded ? 'text-lg font-medium' : undefined">
				{{ alert._source.rule_description || alert._source.type }}
			</div>
			<p v-if="alert._source.rule_groups" class="text-secondary">
				{{ alert._source.rule_groups }}
			</p>
		</div>

		<div v-if="showBadges && alert._id" class="flex flex-wrap items-center gap-3">
			<Badge type="splitted" color="primary">
				<template #iconLeft>
					<Icon :name="TargetIcon" :size="13" class="opacity-80!" />
				</template>
				<template #label>Fired times</template>
				<template #value>{{ alert._source.rule_firedtimes }}</template>
			</Badge>

			<Badge :type="alert._source.rule_mail ? 'active' : 'muted'">
				<template #iconRight>
					<Icon :name="alert._source.rule_mail ? MailIcon : DisabledIcon" :size="14" />
				</template>
				<template #label>Rule mail</template>
			</Badge>

			<template v-if="expanded">
				<Badge type="splitted" color="primary">
					<template #iconLeft>
						<Icon :name="AgentIcon" :size="13" class="opacity-80!" />
					</template>
					<template #label>Agent</template>
					<template #value>{{ alert._source.agent_name }}</template>
				</Badge>
				<Badge type="splitted" color="primary">
					<template #label>agent_id</template>
					<template #value>
						<code
							class="text-primary cursor-pointer"
							@click.stop="routeAgent(alert._source.agent_id).navigate()"
						>
							{{ alert._source.agent_id }}
						</code>
					</template>
				</Badge>
				<Badge type="splitted" color="primary">
					<template #label>agent_ip</template>
					<template #value>{{ alert._source.agent_ip }}</template>
				</Badge>
				<Badge type="splitted" color="primary">
					<template #label>Customer</template>
					<template #value>
						<code
							class="text-primary cursor-pointer"
							@click.stop="routeCustomer({ code: alert._source.agent_labels_customer }).navigate()"
						>
							{{ alert._source.agent_labels_customer }}
						</code>
					</template>
				</Badge>
			</template>
			<n-popover v-else overlap placement="bottom-start">
				<template #trigger>
					<Badge type="splitted" color="primary" hint-cursor>
						<template #iconLeft>
							<Icon :name="AgentIcon" :size="13" class="opacity-80!" />
						</template>
						<template #label>Agent</template>
						<template #value>
							<div class="flex flex-wrap items-center gap-2">
								{{ alert._source.agent_name }} / {{ alert._source.agent_labels_customer }}
								<Icon :name="InfoIcon" :size="13" class="opacity-80!" />
							</div>
						</template>
					</Badge>
				</template>
				<div class="flex flex-col gap-1">
					<div>
						agent_id:
						<code
							class="text-primary cursor-pointer"
							@click.stop="routeAgent(alert._source.agent_id).navigate()"
						>
							{{ alert._source.agent_id }}
							<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
						</code>
					</div>
					<div>
						agent_ip:
						<code>{{ alert._source.agent_ip }}</code>
					</div>
					<div>
						agent_name:
						<code>{{ alert._source.agent_name }}</code>
					</div>
					<div>
						agent_labels_customer:
						<code
							class="text-primary cursor-pointer"
							@click.stop="routeCustomer({ code: alert._source.agent_labels_customer }).navigate()"
						>
							{{ alert._source.agent_labels_customer }}
							<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
						</code>
					</div>
				</div>
			</n-popover>

			<Badge type="splitted" color="primary">
				<template #label>syslog</template>
				<template #value>{{ alert._source.syslog_type }} / {{ alert._source.syslog_level }}</template>
			</Badge>
			<Badge type="splitted" color="primary" :class="{ 'hidden! @2xl:flex!': !expanded }">
				<template #label>manager</template>
				<template #value>{{ alert._source.manager_name }}</template>
			</Badge>
			<Badge type="splitted" color="primary" :class="{ 'hidden! @2xl:flex!': !expanded }">
				<template #label>decoder</template>
				<template #value>{{ alert._source.decoder_name }}</template>
			</Badge>
			<Badge type="splitted" color="primary" :class="{ 'hidden! @2xl:flex!': !expanded }">
				<template #label>source</template>
				<template #value>{{ alert._source.source }}</template>
			</Badge>
			<Badge v-if="expanded && alert._index" type="splitted">
				<template #label>Index</template>
				<template #value>
					<code class="font-mono">{{ alert._index }}</code>
				</template>
			</Badge>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/alerts"
import { NPopover } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const {
	alert,
	expanded = false,
	part = "all"
} = defineProps<{
	alert: Alert
	expanded?: boolean
	part?: "all" | "meta" | "badges"
}>()

const showMeta = computed(() => part === "all" || part === "meta")
const showBadges = computed(() => part === "all" || part === "badges")

const InfoIcon = "carbon:information"
const TargetIcon = "zondicons:target"
const DisabledIcon = "carbon:subtract"
const MailIcon = "carbon:email"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"

const { routeCustomer, routeAgent } = useNavigation()
</script>
