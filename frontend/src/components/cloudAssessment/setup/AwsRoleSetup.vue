<template>
	<!--
		How to create the read-only role an AWS account is scanned through: Prowler's own CloudFormation
		template, with the External ID CoPilot generated for this account. The template's AccountId default
		is Prowler Cloud's account, so it must be changed: the steps say so in so many words.

		Every sentence ends in plain text: Prettier (htmlWhitespaceSensitivity "ignore") puts an inline
		element and the punctuation after it on separate lines, and the page then shows "word ." instead.
	-->
	<div class="flex flex-col gap-4 text-sm" data-testid="aws-role-setup">
		<ol class="m-0 flex list-decimal flex-col gap-5 pl-5">
			<li>
				<div class="flex flex-col gap-2">
					<span>In the customer's AWS account, create a CloudFormation stack from Prowler's template for its read-only ProwlerScan role.</span>
					<dl class="border-default m-0 grid grid-cols-[8rem_minmax(0,1fr)] overflow-hidden rounded-md border">
						<dt :class="TERM">AWS account</dt>
						<dd :class="VALUE">
							<code class="font-mono text-xs">{{ awsAccount ?? "the one in the role's ARN" }}</code>
						</dd>
						<dt :class="TERM">Console</dt>
						<dd :class="VALUE">CloudFormation → Create stack → With new resources (standard)</dd>
						<dt :class="TERM_LAST">Template</dt>
						<dd :class="VALUE_LAST">
							<span class="flex flex-wrap items-baseline gap-x-2">
								<a :href="templateUrl" target="_blank" rel="noopener noreferrer" class="break-all">prowler-scan-role.yml</a>
								<span v-if="prowlerVersion" class="text-secondary text-xs">Prowler {{ prowlerVersion }}</span>
							</span>
						</dd>
					</dl>
				</div>
			</li>
			<li>
				<div class="flex flex-col gap-2">
					<span>Set these three parameters and leave every other at its default.</span>
					<dl class="border-default m-0 grid grid-cols-[8rem_minmax(0,1fr)] overflow-hidden rounded-md border">
						<dt :class="TERM" class="font-mono">ExternalId</dt>
						<dd :class="VALUE" class="flex items-center gap-2">
							<code class="font-mono text-xs break-all" data-testid="aws-role-external-id">{{ account.external_id }}</code>
							<n-button size="tiny" quaternary aria-label="Copy the External ID" @click="copy(account.external_id)">
								<template #icon><Icon :name="CopyIcon" :size="14" /></template>
							</n-button>
						</dd>
						<dt :class="TERM" class="font-mono">AccountId</dt>
						<dd :class="VALUE" class="flex flex-col gap-1 text-xs">
							<span v-if="account.secret_configured" class="text-secondary">
								The 12-digit AWS account of the IAM user or role whose access keys this account holds.
							</span>
							<span v-else class="text-secondary">The 12-digit AWS account CoPilot's host runs in.</span>
							<b class="text-warning">Replace the default, 232136659152: that is Prowler Cloud's account.</b>
						</dd>
						<dt :class="TERM_LAST" class="font-mono">IAMPrincipal</dt>
						<dd :class="VALUE_LAST" class="flex flex-col gap-1 text-xs">
							<span class="text-secondary">That identity, as user/NAME or role/NAME. For example:</span>
							<code class="font-mono">user/copilot-prowler-scanner</code>
						</dd>
					</dl>
				</div>
			</li>
			<li>Tick the box acknowledging that the stack creates IAM resources, then create the stack.</li>
			<li v-if="account.secret_configured">
				<div class="flex flex-col gap-2">
					<span>
						Let that identity assume the role: give it this policy in IAM (the user or role, then Add
						permissions, Create inline policy, JSON).
					</span>
					<div class="relative">
						<pre
							class="bg-secondary border-default m-0 overflow-x-auto rounded-md border p-3 font-mono text-xs"
							data-testid="aws-role-policy"
						>{{ policy }}</pre>
						<n-button
							size="tiny"
							secondary
							class="absolute! top-2 right-2"
							aria-label="Copy the policy"
							@click="copy(policy)"
						>
							<template #icon><Icon :name="CopyIcon" :size="14" /></template>
							Copy
						</n-button>
					</div>
				</div>
			</li>
			<li>Once the stack shows CREATE_COMPLETE, choose Test connection on the account.</li>
		</ol>
	</div>
</template>

<script setup lang="ts">
import type { CloudAccount } from "@/types/cloud-assessment"
import { useClipboard } from "@vueuse/core"
import { NButton, useMessage } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { prowlerRoleTemplateUrl } from "../utils"

const { account, prowlerVersion = null } = defineProps<{ account: CloudAccount; prowlerVersion?: string | null }>()

const CopyIcon = "carbon:copy"
// One look for every parameter table: a shaded key column, hairlines between rows.
const TERM = "bg-secondary border-default border-b px-3 py-2 text-xs"
const TERM_LAST = "bg-secondary px-3 py-2 text-xs"
const VALUE = "border-default m-0 min-w-0 border-b px-3 py-2"
const VALUE_LAST = "m-0 min-w-0 px-3 py-2"
const message = useMessage()
const clipboard = useClipboard({ legacy: true })

const roleArn = computed(() => account.config.role_arn ?? "")
const awsAccount = computed(() => account.cloud_account)
const templateUrl = computed(() => prowlerRoleTemplateUrl(prowlerVersion))
const policy = computed(() =>
	JSON.stringify(
		{ Version: "2012-10-17", Statement: [{ Effect: "Allow", Action: "sts:AssumeRole", Resource: roleArn.value }] },
		null,
		2
	)
)

async function copy(text: string | null) {
	if (!text) return
	await clipboard.copy(text)
	message.success("Copied")
}
</script>
