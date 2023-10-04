<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Flag Icons</div>
		</div>
		<div class="main">
			<strong>Pinx</strong>
			uses the
			<a href="https://flagicons.lipis.dev/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">
				flag-icons
			</a>
			as its svg flag library, so you can import only the flags you need
			<div class="groups grid gap-5 mt-8">
				<n-card class="group">
					<div class="list">
						<div v-for="icon of Flags" :key="icon.name" class="icon-box">
							<n-icon :size="20" :color="'#000'">
								<component :is="icon.name" />
							</n-icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button
								tag="a"
								href="https://flagicons.lipis.dev/"
								target="_blank"
								type="primary"
								alt="docs"
							>
								See more
							</n-button>
						</div>
					</template>
				</n-card>
			</div>
		</div>
	</div>
</template>

<script lang="ts">
import { NIcon, NCard, NButton } from "naive-ui"
import Flags from "./icons-set/flags"

import nz from "flag-icons/flags/4x3/nz.svg"
import md from "flag-icons/flags/4x3/md.svg"
import sn from "flag-icons/flags/4x3/sn.svg"
import it from "flag-icons/flags/4x3/it.svg"
import az from "flag-icons/flags/4x3/az.svg"
import ws from "flag-icons/flags/4x3/ws.svg"
import us from "flag-icons/flags/4x3/us.svg"
import nc from "flag-icons/flags/4x3/nc.svg"
import fr from "flag-icons/flags/4x3/fr.svg"
import by from "flag-icons/flags/4x3/by.svg"
import gq from "flag-icons/flags/4x3/gq.svg"
import es from "flag-icons/flags/4x3/es.svg"
import lu from "flag-icons/flags/4x3/lu.svg"
import mg from "flag-icons/flags/4x3/mg.svg"
import de from "flag-icons/flags/4x3/de.svg"
import vg from "flag-icons/flags/4x3/vg.svg"
import st from "flag-icons/flags/4x3/st.svg"
import cg from "flag-icons/flags/4x3/cg.svg"
import gb from "flag-icons/flags/4x3/gb.svg"
import sa from "flag-icons/flags/4x3/sa.svg"
import gd from "flag-icons/flags/4x3/gd.svg"
import tv from "flag-icons/flags/4x3/tv.svg"
import jp from "flag-icons/flags/4x3/jp.svg"
import ky from "flag-icons/flags/4x3/ky.svg"
import ne from "flag-icons/flags/4x3/ne.svg"
import sl from "flag-icons/flags/4x3/sl.svg"
import ge from "flag-icons/flags/4x3/ge.svg"
import as from "flag-icons/flags/4x3/as.svg"
import sg from "flag-icons/flags/4x3/sg.svg"
import pa from "flag-icons/flags/4x3/pa.svg"

import { type Component, defineComponent } from "vue"

export default defineComponent({
	name: "FlagIcons",
	data: () => ({
		Flags
	}),
	components: {
		NIcon,
		NCard,
		NButton,
		nz: nz as unknown as Component,
		md: md as unknown as Component,
		sn: sn as unknown as Component,
		it: it as unknown as Component,
		az: az as unknown as Component,
		ws: ws as unknown as Component,
		us: us as unknown as Component,
		nc: nc as unknown as Component,
		fr: fr as unknown as Component,
		by: by as unknown as Component,
		gq: gq as unknown as Component,
		es: es as unknown as Component,
		lu: lu as unknown as Component,
		mg: mg as unknown as Component,
		de: de as unknown as Component,
		vg: vg as unknown as Component,
		st: st as unknown as Component,
		cg: cg as unknown as Component,
		gb: gb as unknown as Component,
		sa: sa as unknown as Component,
		gd: gd as unknown as Component,
		tv: tv as unknown as Component,
		jp: jp as unknown as Component,
		ky: ky as unknown as Component,
		ne: ne as unknown as Component,
		sl: sl as unknown as Component,
		ge: ge as unknown as Component,
		as: as as unknown as Component,
		sg: sg as unknown as Component,
		pa: pa as unknown as Component
	}
})
</script>

<style lang="scss" scoped>
.page {
	.main {
		.groups {
			grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));

			@media (max-width: 450px) {
				grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
			}
			.group {
				max-width: 500px;
				.list {
					margin-top: 10px;
					display: grid;
					gap: 12px;
					align-items: start;
					grid-template-columns: repeat(auto-fit, minmax(45px, 1fr));

					.icon-box {
						background-color: rgba(var(--bg-body-rgb), 0.5);
						border-radius: 10px;
						aspect-ratio: 1;
						display: flex;
						align-items: center;
						justify-content: center;
					}
				}
			}
		}
	}
}
</style>
