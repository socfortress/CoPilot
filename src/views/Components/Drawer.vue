<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Drawer</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/drawer"
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
				<n-button-group>
					<n-button @click="activate('top')">Top</n-button>
					<n-button @click="activate('right')">Right</n-button>
					<n-button @click="activate('bottom')">Bottom</n-button>
					<n-button @click="activate('left')">Left</n-button>
				</n-button-group>
				<n-drawer v-model:show="active" :placement="placement" resizable :default-width="502">
					<n-drawer-content title="Stoner" closable :native-scrollbar="false">
						William Stoner is born on a small farm in 1891. One day his father suggests he should attend the
						University of Missouri to study agriculture. Stoner agrees but, while studying a compulsory
						literature course, he quickly falls in love with literary studies. Without telling his parents,
						Stoner quits the agriculture program and studies only the humanities. He completes his MA in
						English and begins teaching. In graduate school, he is friendly with fellow students Gordon
						Finch and Dave Masters. World War I begins, and Gordon and Dave enlist. Despite pressure from
						Gordon, Stoner decides to remain in school during the war. Masters is killed in France, while
						Finch sees action and becomes an officer. At a faculty party, Stoner meets and becomes
						infatuated with a young woman named Edith, who is staying with an aunt for a few weeks. Stoner
						woos Edith, and she agrees to marry him. Stoner’s marriage to Edith is bad from the start. It
						gradually becomes clear that Edith has profound emotional problems. Significantly, she is bitter
						about having cancelled a trip to Europe with her aunt to marry Stoner. After three years of
						marriage, Edith suddenly informs Stoner that she wants a baby. She suddenly becomes passionate
						sexually, but this period is brief. When their daughter Grace is born, Edith remains bedridden
						for nearly a year, and Stoner largely cares for their child alone. He grows close with his young
						daughter, who spends most of her time with him in his study. Stoner gradually realizes that
						Edith is waging a campaign to separate him from his daughter emotionally. For the most part,
						Stoner accepts Edith's mistreatment. He begins to teach with more enthusiasm, but still, year in
						and year out, his marriage with Edith remains perpetually unsatisfactory and fraught. Grace
						becomes an unhappy, secretive child who smiles and laughs often but is emotionally hollow. At
						the University, Finch becomes the acting dean of the faculty. Stoner feels compelled by his
						conscience to fail a student named Charles Walker. He is a close protégé of a colleague,
						Professor Hollis Lomax, and like him is physically disabled. The student is clearly dishonest
						and cannot fulfil the requirements of Stoner's course but, despite this, the decision to expel
						or retain Walker is put on hold. After his promotion to head of the department, Lomax takes
						every opportunity to exact revenge upon Stoner throughout the rest of his career. A
						collaboration between Stoner and a younger instructor in the department, Katherine Driscoll,
						develops into a romantic love affair. Ironically, after the affair begins, Stoner’s
						relationships with Edith and Grace also improve. At some point, Edith finds out about the
						affair, but does not seem to mind it. When Lomax learns about it, however, he begins to put
						pressure on Katherine, who also teaches in the English department. Stoner and Driscoll agree it
						best to end the affair so as not to derail the academic work they both feel called to follow.
						Katherine quietly slips out of town, never to be seen by him again. Eventually, Stoner, older
						now and hard of hearing, is beginning to become a legendary figure in the English department
						despite Lomax's opposition. He begins to spend more time at home, ignoring Edith's signs of
						displeasure at his presence. Entering adulthood, Grace enrolls at the University of Missouri.
						The following year, Grace announces she is pregnant and marries the father of her child. Grace’s
						husband enlists in the army and dies before the baby is born. Grace goes to St. Louis with the
						baby to live with her husband's parents. She visits Stoner and Edith occasionally, and Stoner
						realizes that Grace has developed a drinking problem. As Stoner’s life is coming to an end, his
						daughter Grace comes to visit him. Deeply unhappy and addicted to alcohol, Grace halfheartedly
						tries to reconcile with Stoner, and he sees that his daughter, like her mother, will never be
						happy. When Grace leaves, Stoner feels as though the young child that he loved died long ago.
						Stoner thinks back over his life. He thinks about where he failed, and wonders if he could have
						been more loving to Edith, if he could have been stronger, or if he could have helped her more.
						Later, he believes that he is wrong to think of himself as a failure. During an afternoon when
						he is alone, he sees various young students passing by on their way to class outside his window,
						and he dies, dropping his copy of the one book that he published years earlier as a young
						professor.
						<template #footer>
							<n-button @click="showInner = true">Show inner!</n-button>
						</template>
					</n-drawer-content>
					<n-drawer v-model:show="showInner" :width="251" :placement="placement">
						<n-drawer-content title="Stoner">
							Stoner is a 1965 novel by the American writer John Williams.
						</n-drawer-content>
					</n-drawer>
				</n-drawer>
				<template #code="{ html, js }">
					{{ html(`
					<n-button-group>
						<n-button @click="activate('top')">Top</n-button>
						<n-button @click="activate('right')">Right</n-button>
						<n-button @click="activate('bottom')">Bottom</n-button>
						<n-button @click="activate('left')">Left</n-button>
					</n-button-group>
					<n-drawer v-model:show="active" :placement="placement" resizable :default-width="502">
						<n-drawer-content title="Stoner" closable :native-scrollbar="false">
							William Stoner is born on a small farm in 1891. One day his father suggests he should attend
							the University of Missouri to study agriculture. Stoner agrees but, while studying a
							compulsory literature course, he quickly falls in love with literary studies. Without
							telling his parents, Stoner quits the agriculture program and studies only the humanities.
							He completes his MA in English and begins teaching. In graduate school, he is friendly with
							fellow students Gordon Finch and Dave Masters. World War I begins, and Gordon and Dave
							enlist. Despite pressure from Gordon, Stoner decides to remain in school during the war.
							Masters is killed in France, while Finch sees action and becomes an officer. At a faculty
							party, Stoner meets and becomes infatuated with a young woman named Edith, who is staying
							with an aunt for a few weeks. Stoner woos Edith, and she agrees to marry him. Stoner’s
							marriage to Edith is bad from the start. It gradually becomes clear that Edith has profound
							emotional problems. Significantly, she is bitter about having cancelled a trip to Europe
							with her aunt to marry Stoner. After three years of marriage, Edith suddenly informs Stoner
							that she wants a baby. She suddenly becomes passionate sexually, but this period is brief.
							When their daughter Grace is born, Edith remains bedridden for nearly a year, and Stoner
							largely cares for their child alone. He grows close with his young daughter, who spends most
							of her time with him in his study. Stoner gradually realizes that Edith is waging a campaign
							to separate him from his daughter emotionally. For the most part, Stoner accepts Edith's
							mistreatment. He begins to teach with more enthusiasm, but still, year in and year out, his
							marriage with Edith remains perpetually unsatisfactory and fraught. Grace becomes an
							unhappy, secretive child who smiles and laughs often but is emotionally hollow. At the
							University, Finch becomes the acting dean of the faculty. Stoner feels compelled by his
							conscience to fail a student named Charles Walker. He is a close protégé of a colleague,
							Professor Hollis Lomax, and like him is physically disabled. The student is clearly
							dishonest and cannot fulfil the requirements of Stoner's course but, despite this, the
							decision to expel or retain Walker is put on hold. After his promotion to head of the
							department, Lomax takes every opportunity to exact revenge upon Stoner throughout the rest
							of his career. A collaboration between Stoner and a younger instructor in the department,
							Katherine Driscoll, develops into a romantic love affair. Ironically, after the affair
							begins, Stoner’s relationships with Edith and Grace also improve. At some point, Edith finds
							out about the affair, but does not seem to mind it. When Lomax learns about it, however, he
							begins to put pressure on Katherine, who also teaches in the English department. Stoner and
							Driscoll agree it best to end the affair so as not to derail the academic work they both
							feel called to follow. Katherine quietly slips out of town, never to be seen by him again.
							Eventually, Stoner, older now and hard of hearing, is beginning to become a legendary figure
							in the English department despite Lomax's opposition. He begins to spend more time at home,
							ignoring Edith's signs of displeasure at his presence. Entering adulthood, Grace enrolls at
							the University of Missouri. The following year, Grace announces she is pregnant and marries
							the father of her child. Grace’s husband enlists in the army and dies before the baby is
							born. Grace goes to St. Louis with the baby to live with her husband's parents. She visits
							Stoner and Edith occasionally, and Stoner realizes that Grace has developed a drinking
							problem. As Stoner’s life is coming to an end, his daughter Grace comes to visit him. Deeply
							unhappy and addicted to alcohol, Grace halfheartedly tries to reconcile with Stoner, and he
							sees that his daughter, like her mother, will never be happy. When Grace leaves, Stoner
							feels as though the young child that he loved died long ago. Stoner thinks back over his
							life. He thinks about where he failed, and wonders if he could have been more loving to
							Edith, if he could have been stronger, or if he could have helped her more. Later, he
							believes that he is wrong to think of himself as a failure. During an afternoon when he is
							alone, he sees various young students passing by on their way to class outside his window,
							and he dies, dropping his copy of the one book that he published years earlier as a young
							professor.
							<template #footer>
								<n-button @click="showInner = true">Show inner!</n-button>
							</template>
						</n-drawer-content>
						<n-drawer v-model:show="showInner" :width="251" :placement="placement">
							<n-drawer-content title="Stoner">
								Stoner is a 1965 novel by the American writer John Williams.
							</n-drawer-content>
						</n-drawer>
					</n-drawer>
					`) }}

					{{
						js(`
						const active = ref(false)
						const showInner = ref(false)
						const placement = ref\<\DrawerPlacement\>\("right")
						const activate = (place: DrawerPlacement) => {
							active.value = true
							placement.value = place
						}

						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Customize display area">
				<template #description>
					You can customize display area by
					<n-text code>to</n-text>
					prop. Remember to set
					<n-text code>:trap-focus="false"</n-text>
					and
					<n-text code>:block-scroll="false"</n-text>
					, otherwise content outside drawer won't be focusable and body won't be scrollable.
				</template>
				<n-button-group>
					<n-button @click="activate1('top')">Top</n-button>
					<n-button @click="activate1('right')">Right</n-button>
					<n-button @click="activate1('bottom')">Bottom</n-button>
					<n-button @click="activate1('left')">Left</n-button>
				</n-button-group>
				<div
					id="drawer-target"
					style="
						position: relative;
						width: 100%;
						height: 300px;
						border: 1px solid rgba(128, 128, 128, 0.2);
						margin-top: 10px;
						display: flex;
						align-items: center;
						justify-content: center;
						overflow: hidden;
					"
				>
					Target Area
				</div>
				<n-drawer
					v-model:show="active1"
					:width="200"
					:height="200"
					:placement="placement"
					:trap-focus="false"
					to="#drawer-target"
				>
					<n-drawer-content title="Stoner">
						Stoner is a 1965 novel by the American writer John Williams.
					</n-drawer-content>
				</n-drawer>
				<template #code="{ html, js }">
					{{ html(`
					<n-button-group>
						<n-button @click="activate1('top')">Top</n-button>
						<n-button @click="activate1('right')">Right</n-button>
						<n-button @click="activate1('bottom')">Bottom</n-button>
						<n-button @click="activate1('left')">Left</n-button>
					</n-button-group>
					<div
						id="drawer-target"
						style="
							position: relative;
							width: 100%;
							height: 300px;
							border: 1px solid rgba(128, 128, 128, 0.2);
							margin-top: 10px;
							display: flex;
							align-items: center;
							justify-content: center;
							overflow: hidden;
						"
					>
						Target Area
					</div>
					<n-drawer
						v-model:show="active1"
						:width="200"
						:height="200"
						:placement="placement"
						:trap-focus="false"
						to="#drawer-target"
					>
						<n-drawer-content title="Stoner">
							Stoner is a 1965 novel by the American writer John Williams.
						</n-drawer-content>
					</n-drawer>
					`) }}

					{{
						js(`
						const active1 = ref(false)
						const showInner = ref(false)
						const placement = ref\<\DrawerPlacement\>\("right")
						const activate1 = (place: DrawerPlacement) => {
							active1.value = true
							placement.value = place
						}

						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NButtonGroup, NDrawer, NDrawerContent, NButton, type DrawerPlacement, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const active = ref(false)
const active1 = ref(false)
const showInner = ref(false)
const placement = ref<DrawerPlacement>("right")
const activate = (place: DrawerPlacement) => {
	active.value = true
	placement.value = place
}
const activate1 = (place: DrawerPlacement) => {
	active1.value = true
	placement.value = place
}
</script>
