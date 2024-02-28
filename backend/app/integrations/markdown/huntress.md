# [Huntress Integration](https://api.huntress.io/docs#introduction)

Huntress is a cloud-based managed detection and response (MDR) solution that provides continuous monitoring and threat detection for endpoints. This integration allows you to ingest Huntress incidents into the SOCFortress SIEM stack.

## Introduction

The Huntress API follows a RESTful pattern. Requests are made via resource-oriented URLs as described in this document and API responses are formatted as JSON data.

To test out the Huntress APIs quickly, use the [Swagger Interface](https://api.huntress.io/docs/preview).

## API Overview

### Authentication

To begin, generate your API Key at `<your_account_subdomain>.huntress.io`. Once you are logged into your account on the Huntress site, check the dropdown menu at the top-right corner of the site header. You should see API Credentials among the options if your account has been granted access to the Huntress API. Click on the option to continue to the API Key generation page.

Once on the API Key generation page, click on the green Setup button to begin the process to generate your API Key. You will be redirected to a page where you will be prompted to generate your API Key. Click the Generate button to generate a public and private key pair for Huntress API access. The inputs on the page will be filled in with your access credentials once you have done so.

**Your API Private Key will only be visible at this stage of API Key generation. Be sure to save the value provided somewhere secure, as once you navigate away from this page, this value will no longer be accessible and you must regenerate your API credentials if your secret key value is lost.**

If necessary, you can repeat the process to regenerate your API credentials with a new API Key and API Secret Key on the same API Key generation page, at `<your_account_subdomain>.huntress.io/account/api_credentials`.

The Huntress API implements basic access authentication. Once you have your API Key and API Secret Key, provide these values as the result of a Base64 encoded string in every request to the Huntress API via the `Authorization` header. Your request header should look something like `Authorization: Basic [Base64Encode(<your_api_key>:<your_api_secret_key>)]`.
