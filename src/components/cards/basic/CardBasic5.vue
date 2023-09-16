<template>
	<n-card
		:title="title"
		:segmented="{
			content: true,
			footer: 'soft'
		}"
	>
		<template #default>
			<p>
				{{ text }}
			</p>
		</template>
		<template #action>
			<div class="flex justify-around">
				<n-icon :size="20">
					<CheckIcon />
				</n-icon>
				<n-icon :size="20">
					<StarIcon />
				</n-icon>
				<n-icon :size="20">
					<ShieldIcon />
				</n-icon>
				<n-icon :size="20">
					<PremiumIcon />
				</n-icon>
				<n-icon :size="20">
					<EcoIcon />
				</n-icon>
			</div>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NIcon } from "naive-ui"
import CheckIcon from "@vicons/fluent/CheckmarkStarburst16Regular"
import StarIcon from "@vicons/fluent/Star16Regular"
import ShieldIcon from "@vicons/fluent/ShieldKeyhole16Regular"
import PremiumIcon from "@vicons/fluent/Premium24Regular"
import EcoIcon from "@vicons/material/EcoOutlined"

const title = faker.lorem.sentence({ min: 2, max: 5 })
const text = faker.lorem.paragraph()
</script>
