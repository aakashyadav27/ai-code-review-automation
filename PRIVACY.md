# Privacy Policy for CodeLens AI

**Last Updated: December 28, 2025**

## 1. Introduction
CodeLens AI ("we", "our", or "us") provides an automated code review service integration for GitHub. We are committed to protecting your privacy and code security.

## 2. Data We Collect
We collect the minimum data necessary to provide our service:
- **GitHub Metadata**: Repository names, PR numbers, commit hashes, and file names (to perform reviews).
- **Code Content**: We temporarily process the code in your Pull Requests to generate reviews. **We do not store your code.**
- **API Keys**: If you provide your own Google Gemini or Groq API key, we store it in an **encrypted** format.
- **Usage Logs**: Basic logs of success/failure rates for debugging.

## 3. How We Use Data
- To perform code analysis using Large Language Models (LLMs) via Google Gemini or Groq APIs.
- To post review comments on your GitHub Pull Requests.
- To maintain your configuration settings (enabled reviewers, preferences).

## 4. Data Storage & Security
- **Encryption**: All API keys are encrypted at rest using industry-standard Fernet (AES) encryption.
- **No Code Retention**: Your code is sent to the LLM provider for analysis and immediately discarded. We do not use your code to train our own models.
- **Database**: Data is stored in Supabase (PostgreSQL) with Row Level Security (RLS) enabled.

## 5. Third-Party Services
We use the following third-party processors:
- **Google Gemini API**: For code analysis (LLM).
- **Groq API**: For code analysis (LLM backup).
- **Supabase**: For database hosting.
- **Vercel**: For serverless hosting.

## 6. Your Rights
Você can revoke access at any time by uninstalling the GitHub App. Upon uninstallation, we can delete your configuration data upon request via GitHub Issues.

## 7. Contact
For privacy concerns, please open an issue in our [GitHub Repository](https://github.com/aakashyadav27/ai-code-review-automation).
