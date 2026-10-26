import type { PortalSeed } from "../support/e2e"
import deCommon from "../../src/lang/locales/de/common.json"
import enCommon from "../../src/lang/locales/en/common.json"
import enNavigation from "../../src/lang/locales/en/navigation.json"
import itCommon from "../../src/lang/locales/it/common.json"
import itNavigation from "../../src/lang/locales/it/navigation.json"

/**
 * The portal's languages (#1310), on the real backend and the seed. With nothing enabled the
 * portal is English and offers no choice. Once the SOC enables Italian for customer A, the user
 * picks it from the avatar menu: the portal turns Italian, and stays so after a reload and on
 * another device (a fresh sign-in), since the pick is kept on their account. Profile → Settings
 * switches back. Until the user picks, the browser's language is used when it is enabled. When
 * the SOC turns a picked language off, the portal falls back to English.
 */
describe("portal languages", () => {
	let seed: PortalSeed

	function setLanguages(languages: string[]) {
		return cy.adminApi(seed, "PUT", `/customer_portal/languages/settings/${seed.customers.a}`, { languages })
	}

	/** A new device: no saved session, so the portal reads `/me` again at sign-in. */
	function freshLogin(browserLanguages?: string[]) {
		Cypress.session.clearAllSavedSessions()
		cy.loginToPortal(seed)
		cy.visit("/overview", {
			onBeforeLoad(win) {
				if (browserLanguages) Object.defineProperty(win.navigator, "languages", { value: browserLanguages })
			}
		})
	}

	function openAvatarMenu() {
		cy.get("[data-testid=toolbar-avatar]:visible").click()
	}

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	after(() => {
		// Leave the seed as the other specs expect it: English only.
		setLanguages(["en"])
	})

	it("is English with no choice while the SOC has enabled nothing else", () => {
		setLanguages(["en"])
		freshLogin(["it-IT", "it"])
		cy.get("html").should("have.attr", "lang", "en")
		openAvatarMenu()
		cy.get("[data-testid=toolbar-user]").should("be.visible")
		cy.contains(".n-dropdown-option", enCommon.language.label).should("not.exist")

		cy.visit("/profile")
		cy.get("[data-testid=profile-language]").should("contain.text", enCommon.language.englishOnly)
	})

	it("follows the browser's language until the user picks, when the customer offers it", () => {
		setLanguages(["en", "de"])
		freshLogin(["de-DE", "de", "en"])
		cy.get("html").should("have.attr", "lang", "de")
		openAvatarMenu()
		cy.contains(".n-dropdown-option", deCommon.language.label).should("be.visible")
	})

	it("switches to a language the user picks, and keeps it across a reload and another device", () => {
		setLanguages(["en", "it"])
		freshLogin(["en-US", "en"])
		cy.get("html").should("have.attr", "lang", "en")

		cy.intercept("PUT", "**/api/customer_portal/languages/me").as("pick")
		openAvatarMenu()
		cy.contains(".n-dropdown-option", enCommon.language.label).trigger("mouseenter")
		cy.contains(".n-dropdown-option", "Italiano").click()
		cy.wait("@pick").its("request.body").should("deep.equal", { locale: "it" })
		cy.get("html").should("have.attr", "lang", "it")
		cy.contains(".n-message", itCommon.language.saved).should("be.visible")
		// The menu reads in Italian at once, without a reload.
		cy.contains("nav", itNavigation.routes.eventSearch).should("exist")

		cy.reload()
		cy.get("html").should("have.attr", "lang", "it")

		// Another device, whose browser is English: the account's pick wins.
		freshLogin(["en-US", "en"])
		cy.get("html").should("have.attr", "lang", "it")

		// Back to English from Profile → Settings.
		cy.visit("/profile")
		cy.get("[data-testid=profile-language]").should("contain.text", itCommon.language.hint)
		cy.get("[data-testid=language-picker]").click()
		cy.contains(".n-base-select-option", "English").click()
		cy.wait("@pick").its("request.body").should("deep.equal", { locale: "en" })
		cy.get("html").should("have.attr", "lang", "en")
		cy.get("[data-testid=profile-language]").should("contain.text", enCommon.language.hint)
		cy.contains("nav", enNavigation.routes.eventSearch).should("exist")
	})

	it("falls back to English once the SOC turns the picked language off", () => {
		setLanguages(["en", "it"])
		freshLogin()
		cy.request({
			method: "POST",
			url: "/api/auth/token/customer-portal",
			form: true,
			body: { username: seed.portal_user, password: seed.password }
		})
			.its("body.access_token")
			.then(token =>
				cy.request({
					method: "PUT",
					url: "/api/customer_portal/languages/me",
					body: { locale: "it" },
					headers: { Authorization: `Bearer ${token}` }
				})
			)
		cy.reload()
		cy.get("html").should("have.attr", "lang", "it")

		setLanguages(["en"])
		cy.reload()
		cy.get("html").should("have.attr", "lang", "en")
		openAvatarMenu()
		cy.contains(".n-dropdown-option", enCommon.language.label).should("not.exist")

		// Turned on again, the user's pick is back.
		setLanguages(["en", "it"])
		cy.reload()
		cy.get("html").should("have.attr", "lang", "it")
	})
})
