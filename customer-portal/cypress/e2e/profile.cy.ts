import type { PortalSeed } from "../support/e2e"

/**
 * The profile page (#1192): the profile-picture editor, switched off by a hard-coded
 * flag and never shown, was removed along with its cropper dependency. The page still
 * shows the user and both of its tabs.
 */
describe("profile page", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	it("shows the user and its settings and security tabs, without an image editor", () => {
		cy.visit("/profile")
		cy.contains("h1", seed.portal_user)
		cy.contains(".n-tabs-tab", "Settings")
		cy.contains(".n-tabs-tab", "Security").click()
		cy.contains("Change Password")
		cy.contains("Edit profile image").should("not.exist")
	})
})
