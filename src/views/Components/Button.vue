<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Button</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/button"
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
			<CardCodeExample title="Basic">
				<template #description>
					There are
					<n-text code>default</n-text>
					,
					<n-text code>primary</n-text>
					,
					<n-text code>tertiary</n-text>
					,
					<n-text code>info</n-text>
					,
					<n-text code>success</n-text>
					,
					<n-text code>warning</n-text>
					and
					<n-text code>error</n-text>
					button types.
				</template>
				<n-space>
					<n-button>Default</n-button>
					<n-button type="tertiary">Tertiary</n-button>
					<n-button type="primary">Primary</n-button>
					<n-button type="info">Info</n-button>
					<n-button type="success">Success</n-button>
					<n-button type="warning">Warning</n-button>
					<n-button type="error">Error</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-button>Default</n-button>
					<n-button type="tertiary">Tertiary</n-button>
					<n-button type="primary">Primary</n-button>
					<n-button type="info">Info</n-button>
					<n-button type="success">Success</n-button>
					<n-button type="warning">Warning</n-button>
					<n-button type="error">Error</n-button>

					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Secondary">
				<n-space>
					<n-button strong secondary>Default</n-button>
					<n-button strong secondary type="tertiary">Tertiary</n-button>
					<n-button strong secondary type="primary">Primary</n-button>
					<n-button strong secondary type="info">Info</n-button>
					<n-button strong secondary type="success">Success</n-button>
					<n-button strong secondary type="warning">Warning</n-button>
					<n-button strong secondary type="error">Error</n-button>
					<n-button strong secondary round>Default</n-button>
					<n-button strong secondary round type="primary">Primary</n-button>
					<n-button strong secondary round type="info">Info</n-button>
					<n-button strong secondary round type="success">Success</n-button>
					<n-button strong secondary round type="warning">Warning</n-button>
					<n-button strong secondary round type="error">Error</n-button>
					<n-button strong secondary circle>
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
					</n-button>
					<n-button strong secondary circle type="primary">
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
					</n-button>
					<n-button strong secondary circle type="info">
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
					</n-button>
					<n-button strong secondary circle type="success">
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
					</n-button>
					<n-button strong secondary circle type="warning">
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
					</n-button>
					<n-button strong secondary circle type="error">
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
					</n-button>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-button strong secondary>Default</n-button>
					<n-button strong secondary type="tertiary">Tertiary</n-button>
					<n-button strong secondary type="primary">Primary</n-button>
					<n-button strong secondary type="info">Info</n-button>
					<n-button strong secondary type="success">Success</n-button>
					<n-button strong secondary type="warning">Warning</n-button>
					<n-button strong secondary type="error">Error</n-button>
					<n-button strong secondary round>Default</n-button>
					<n-button strong secondary round type="primary">Primary</n-button>
					<n-button strong secondary round type="info">Info</n-button>
					<n-button strong secondary round type="success">Success</n-button>
					<n-button strong secondary round type="warning">Warning</n-button>
					<n-button strong secondary round type="error">Error</n-button>
					<n-button strong secondary circle>
						<template #icon>
							<n-icon><cash-icon /></n-icon>
						</template>
					</n-button>
					<n-button strong secondary circle type="primary">
						<template #icon>
							<n-icon><cash-icon /></n-icon>
						</template>
					</n-button>
					<n-button strong secondary circle type="info">
						<template #icon>
							<n-icon><cash-icon /></n-icon>
						</template>
					</n-button>
					<n-button strong secondary circle type="success">
						<template #icon>
							<n-icon><cash-icon /></n-icon>
						</template>
					</n-button>
					<n-button strong secondary circle type="warning">
						<template #icon>
							<n-icon><cash-icon /></n-icon>
						</template>
					</n-button>
					<n-button strong secondary circle type="error">
						<template #icon>
							<n-icon><cash-icon /></n-icon>
						</template>
					</n-button>
					`) }}
					{{
						js(`
								import { CashOutline as CashIcon } from '@vicons/ionicons5'`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Size">
				<template #description>
					Buttons can be
					<n-text code>tiny</n-text>
					,
					<n-text code>small</n-text>
					,
					<n-text code>medium</n-text>
					and
					<n-text code>large</n-text>
					in size.
				</template>
				<n-space align="baseline">
					<n-button size="tiny">Small Small</n-button>
					<n-button size="small">Small</n-button>
					<n-button size="medium">Not Small</n-button>
					<n-button size="large">Not Not Small</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-button size="tiny">Small Small</n-button>
					<n-button size="small">Small</n-button>
					<n-button size="medium">Not Small</n-button>
					<n-button size="large">Not Not Small</n-button>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Ghost">
				<template #description>Ghost buttons have transparent backgrounds.</template>
				<n-space align="baseline">
					<n-button ghost>Default</n-button>
					<n-button type="primary" ghost>Primary</n-button>
					<n-button type="info" ghost>Info</n-button>
					<n-button type="success" ghost>Success</n-button>
					<n-button type="warning" ghost>Warning</n-button>
					<n-button type="error" ghost>Error</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-button ghost>Default</n-button>
					<n-button type="primary" ghost>Primary</n-button>
					<n-button type="info" ghost>Info</n-button>
					<n-button type="success" ghost>Success</n-button>
					<n-button type="warning" ghost>Warning</n-button>
					<n-button type="error" ghost>Error</n-button>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Shape">
				<template #description>Buttons can have different shapes.</template>
				<n-space>
					<n-button circle>
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
					</n-button>
					<n-button round>Round</n-button>
					<n-button>Rect</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-button circle>
						<template #icon>
							<n-icon><cash-icon /></n-icon>
						</template>
					</n-button>
					<n-button round>Round</n-button>
					<n-button>Rect</n-button>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Loading">
				<template #description>Buttons can have loading states.</template>
				<n-space>
					<n-button :loading="loading" @click="handleClick">
						<template #icon>
							<Icon :name="CashIcon" />
						</template>
						Click Me
					</n-button>
					<n-button :loading="loading" icon-placement="left" @click="handleClick">Click Me</n-button>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-button :loading="loading" @click="handleClick">
						<template #icon>
							<n-icon>
								<cash-icon />
							</n-icon>
						</template>
						Click Me
					</n-button>
					<n-button :loading="loading" icon-placement="left" @click="handleClick">Click Me</n-button>
					`) }}
					{{
						js(`
								const loading = ref(false)
								function handleClick() {
									loading.value = true
									setTimeout(() => {
										loading.value = false
									}, 2000)
								}
								`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Button group">
				<template #description>Buttons can be grouped.</template>
				<n-space>
					<n-button-group vertical>
						<n-button round>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Live a
						</n-button>
						<n-button ghost>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Sufficient
						</n-button>
						<n-button>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Life
						</n-button>
					</n-button-group>
					<n-button-group vertical size="large">
						<n-button>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							With
						</n-button>
						<n-button>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Enough
						</n-button>
						<n-button ghost round>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Happiness
						</n-button>
					</n-button-group>
					<n-button-group size="small">
						<n-button round>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Life
						</n-button>
						<n-button>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Is
						</n-button>
						<n-button>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Good
						</n-button>
					</n-button-group>
					<n-button-group>
						<n-button ghost>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Eat
						</n-button>
						<n-button ghost>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							One More
						</n-button>
						<n-button round>
							<template #icon>
								<Icon :name="LogInIcon" />
							</template>
							Apple
						</n-button>
					</n-button-group>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-button-group vertical>
						<n-button round>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Live a
						</n-button>
						<n-button ghost>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Sufficient
						</n-button>
						<n-button>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Life
						</n-button>
					</n-button-group>
					<n-button-group vertical size="large">
						<n-button>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							With
						</n-button>
						<n-button>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Enough
						</n-button>
						<n-button ghost round>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Happiness
						</n-button>
					</n-button-group>
					<n-button-group size="small">
						<n-button round>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Life
						</n-button>
						<n-button>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Is
						</n-button>
						<n-button>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Good
						</n-button>
					</n-button-group>
					<n-button-group>
						<n-button ghost>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Eat
						</n-button>
						<n-button ghost>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							One More
						</n-button>
						<n-button round>
							<template #icon>
								<n-icon><log-in-icon /></n-icon>
							</template>
							Apple
						</n-button>
					</n-button-group>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NButton, NButtonGroup, NSpace, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const LogInIcon = "ion:log-in-outline"
const CashIcon = "ion:cash-outline"

import { ref } from "vue"

const loading = ref(false)
function handleClick() {
	loading.value = true
	setTimeout(() => {
		loading.value = false
	}, 2000)
}
</script>
