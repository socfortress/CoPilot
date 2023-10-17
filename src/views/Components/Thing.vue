<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Thing</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/thing"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic" class="max-w-lg">
				<n-row>
					<n-col :span="12">
						<n-checkbox v-model:checked="indented">Indented</n-checkbox>
					</n-col>
				</n-row>
				<n-row>
					<n-col :span="12">
						<n-checkbox v-model:checked="avatar">Avatar</n-checkbox>
					</n-col>
					<n-col :span="12">
						<n-checkbox v-model:checked="action">Action</n-checkbox>
					</n-col>
				</n-row>
				<n-row>
					<n-col :span="12">
						<n-checkbox v-model:checked="header">Header</n-checkbox>
					</n-col>
					<n-col :span="12">
						<n-checkbox v-model:checked="headerExtra">Header Extra</n-checkbox>
					</n-col>
				</n-row>
				<n-row>
					<n-col :span="12">
						<n-checkbox v-model:checked="description">Description</n-checkbox>
					</n-col>
					<n-col :span="12">
						<n-checkbox v-model:checked="footer">Footer</n-checkbox>
					</n-col>
				</n-row>
				<n-divider />
				<n-thing :content-indented="indented">
					<template v-if="avatar" #avatar>
						<n-avatar>
							<Icon :name="CashIcon" />
						</n-avatar>
					</template>
					<template v-if="header" #header>Money</template>
					<template v-if="headerExtra" #header-extra>
						<n-button circle size="small">
							<template #icon>
								<Icon :name="CashIcon" />
							</template>
						</n-button>
					</template>
					<template v-if="description" #description>Description</template>
					Money is any item or verifiable record that is generally accepted as payment for goods and services
					and repayment of debts, such as taxes, in a particular country or socio-economic context.
					<template v-if="footer" #footer>Footer</template>
					<template v-if="action" #action>
						<n-space>
							<n-button size="small">
								<template #icon>
									<Icon :name="CashIcon" />
								</template>
								1$
							</n-button>
							<n-button size="small">
								<template #icon>
									<Icon :name="CashIcon" />
								</template>
								10$
							</n-button>
							<n-button size="small">
								<template #icon>
									<Icon :name="CashIcon" />
								</template>
								100$
							</n-button>
						</n-space>
					</template>
				</n-thing>

				<template #code="{ html, js }">
					{{ html(`
					<n-row>
						<n-col :span="12">
							<n-checkbox v-model:checked="indented">Indented</n-checkbox>
						</n-col>
					</n-row>
					<n-row>
						<n-col :span="12">
							<n-checkbox v-model:checked="avatar">Avatar</n-checkbox>
						</n-col>
						<n-col :span="12">
							<n-checkbox v-model:checked="action">Action</n-checkbox>
						</n-col>
					</n-row>
					<n-row>
						<n-col :span="12">
							<n-checkbox v-model:checked="header">Header</n-checkbox>
						</n-col>
						<n-col :span="12">
							<n-checkbox v-model:checked="headerExtra">Header Extra</n-checkbox>
						</n-col>
					</n-row>
					<n-row>
						<n-col :span="12">
							<n-checkbox v-model:checked="description">Description</n-checkbox>
						</n-col>
						<n-col :span="12">
							<n-checkbox v-model:checked="footer">Footer</n-checkbox>
						</n-col>
					</n-row>
					<n-divider />
					<n-thing :content-indented="indented">
						<template v-if="avatar" #avatar>
							<n-avatar>
								<n-icon>
									<cash-icon />
								</n-icon>
							</n-avatar>
						</template>
						<template v-if="header" #header>Money</template>
						<template v-if="headerExtra" #header-extra>
							<n-button circle size="small">
								<template #icon>
									<cash-icon />
								</template>
							</n-button>
						</template>
						<template v-if="description" #description>Description</template>
						Money is any item or verifiable record that is generally accepted as payment for goods and
						services and repayment of debts, such as taxes, in a particular country or socio-economic
						context.
						<template v-if="footer" #footer>Footer</template>
						<template v-if="action" #action>
							<n-space>
								<n-button size="small">
									<template #icon>
										<n-icon>
											<cash-icon />
										</n-icon>
									</template>
									1$
								</n-button>
								<n-button size="small">
									<template #icon>
										<n-icon>
											<cash-icon />
										</n-icon>
									</template>
									10$
								</n-button>
								<n-button size="small">
									<template #icon>
										<n-icon>
											<cash-icon />
										</n-icon>
									</template>
									100$
								</n-button>
							</n-space>
						</template>
					</n-thing>
					`) }}
					{{
						js(`
						import { CashOutline as CashIcon } from "@vicons/ionicons5"
						const avatar = ref(true)
						const header = ref(true)
						const headerExtra = ref(true)
						const description = ref(true)
						const footer = ref(true)
						const action = ref(true)
						const indented = ref(true)
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NRow, NCol, NCheckbox, NDivider, NThing, NAvatar, NSpace, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { ref } from "vue"

const ExternalIcon = "tabler:external-link"
const CashIcon = "ion:cash-outline"

const avatar = ref(true)
const header = ref(true)
const headerExtra = ref(true)
const description = ref(true)
const footer = ref(true)
const action = ref(true)
const indented = ref(true)
</script>
