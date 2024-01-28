# [Mimecast](https://integrations.mimecast.com/documentation/api-overview/authentication-scripts-server-apps/)

# Requirements

-   A Mimecast plan with a Targeted Threat Protection (TTP) license. For more information, see Mimecast Plans.
-   A Mimecast administrator account.

# Steps

1. **Create the API application.**
2. **Configure the API service account user.**
3. **Configure 2-step authentication with SMS.**
4. **Create API keys.**
5. **Provide your Mimecast credentials to CoPilot.**

## Step 1: Create the API Application

1. Sign in to the Mimecast Administration Console.
2. In the Administration menu, click `Services > API and Platform Integrations`.
3. On the Available Integrations tab, click `Generate Keys`.
4. In the Description field, enter a description for this API application.
5. Click `Next`.
6. Configure these settings:
    - Technical Point of Contact — Enter the name of the person who Mimecast should contact if necessary. For example, the active user configuring the API application.
    - Email — Enter the corresponding email for the point of contact.
7. Click `Next`.
8. Verify that your information is correct, and then click the Status toggle to the `Enabled` position.
9. Click `Add`.
10. Click the application that you created to open the information panel.
11. Copy the Application ID and Application Key to a safe, encrypted location to provide to CoPilot later.

## Step 2: Configure the API service account user

To prevent permission overrides during the configuration process, create a dedicated service account user. For more information, see Managing API Applications.

1. Sign in to the Mimecast Administration Console.
2. Create a service account user:
    - In the Administration menu, click `Directories > Internal Directories`.
    - Select the domain the user will be added to.
    - Enter the email address for the user.
    - Create and confirm a password.
    - Click `Save`.
3. Assign the service account user permissions:
    - In the Administration menu, click `Account > Roles`.
    - Click `Basic Administrator`.
    - Click `Add User to Role`.
    - Select the email address of the API service user account.

## Step 3: Configure 2-step authentication with SMS

You must configure 2-step authentication with SMS to create the API keys. After creating the API keys, you can revert to your previous authentication method.

1. In a new browser tab, sign in to the Mimecast Administration Console as the service account user created in Configure the API service account user.
2. Register a phone number for the service account that can be used for 2-step authentication with SMS:
    - Click the flag icon to select the correct country code.
    - Enter the phone number.
    - Click `Next`.
    - Enter the verification sent to the registered phone number.
    - Click `Verify`.
3. Sign out of Mimecast.
4. Return to the previous browser tab.

## Step 4: Create API keys

> **Notes:**
>
> -   You may need to wait a maximum of 30 minutes after creating the API application before creating the API keys.

1. In the browser tab that you just returned to, in the Administration menu, click `Services > API and Platform Integrations`.
2. In the Your Application Integrations tab, select the application that you created in Create the API application.
3. In the information pane, click `Create Keys`.
4. In the Email Address field, enter the email address for the service account that you created in Configure the API service account user.
5. Click `Next`.
6. In the Type menu, click `Cloud`.
7. In the Password field, enter the service account password, and then click `Next`.
8. Follow the prompts to verify the service account, and then click `Next`.
9. Click the eye next to Access Key and Secret Key to reveal each value.
10. Copy the Access Key and Secret Key values and save them in a safe, encrypted location to provide to CoPilot later.
11. Click `Finish`.

## Step 5: Provide your Mimecast credentials to CoPilot

1. In the CoPilot web app, click `Customers > **Select the Customer's details** > Integrations`.
2. Click `Add Integration`.
3. Select `Mimecast` from the list of integrations.
4. Enter the Application ID, Application Key, Access Key, Secret Key, and Email Address that you saved in the previous steps.
