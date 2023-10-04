<template>
	<n-card hoverable content-style="padding: 0;">
		<div class="flex xs:flex-row flex-col xs:items-stretch">
			<div class="basis-3/5 flex flex-col">
				<div class="card-header flex justify-between items-center">
					<div>
						<span>
							{{ title }}
						</span>
					</div>
				</div>
				<div class="card-content grow">
					<div class="mb-3">
						<n-rate readonly :allow-half="true" :default-value="5" color="#FFB600" />
					</div>
					<p v-html="text"></p>
					<div class="divider"></div>
					<div class="features flex justify-around">
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
				</div>
			</div>
			<div class="card-info basis-2/5 flex flex-col justify-between items-center">
				<div class="mb-4">
					<n-radio-group v-model:value="subscription" name="subscription">
						<n-radio-button value="monthly" label="Monthly" />
						<n-radio-button value="yearly" label="Yearly" />
					</n-radio-group>
				</div>
				<div class="text-xl mb-4">
					<div v-if="subscription === 'monthly'">
						<strong>$29</strong>
						<span>/month</span>
					</div>
					<div v-if="subscription === 'yearly'">
						<strong>$299</strong>
						<span>/year</span>
						<br />
						<small class="opacity-60">$24,90/month</small>
					</div>
				</div>
				<n-button type="primary">
					<n-icon class="mr-3">
						<PremiumIcon />
					</n-icon>
					Subscribe now
				</n-button>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NButton, NIcon, NRate, NRadioGroup, NRadioButton } from "naive-ui"
import CheckIcon from "@vicons/fluent/CheckmarkStarburst16Regular"
import StarIcon from "@vicons/fluent/Star16Regular"
import ShieldIcon from "@vicons/fluent/ShieldKeyhole16Regular"
import PremiumIcon from "@vicons/fluent/Premium24Regular"
import EcoIcon from "@vicons/material/EcoOutlined"
import { ref } from "vue"

const subscription = ref("monthly")

const title = faker.lorem.sentence({ min: 2, max: 4 })
const text = faker.lorem.sentences(2, "<br/><br/>") + faker.lorem.paragraph()
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;

	.card-header {
		box-sizing: border-box;
		display: flex;
		align-items: center;
		font-weight: 700;
		font-family: var(--font-family-display);
		font-size: var(--n-title-font-size);
		padding: var(--n-padding-top) var(--n-padding-left) var(--n-padding-bottom) var(--n-padding-left);
	}

	.card-content {
		box-sizing: border-box;
		padding: 0 var(--n-padding-left) var(--n-padding-bottom) var(--n-padding-left);
		font-size: var(--n-font-size);
	}

	.card-info {
		box-sizing: border-box;
		transition:
			background-color 0.3s var(--n-bezier),
			border-color 0.3s var(--n-bezier);
		background-clip: padding-box;
		background-color: var(--n-action-color);
		padding: var(--n-padding-bottom) var(--n-padding-left);
		border-bottom-left-radius: var(--n-border-radius);
		border-bottom-right-radius: var(--n-border-radius);
	}

	.divider {
		background-color: rgba(var(--fg-color-rgb), 0.2);
		width: 80%;
		margin: 20px auto;
		height: 1px;
	}
}
</style>
