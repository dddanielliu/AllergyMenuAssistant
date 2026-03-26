# 🥗 AllergyMenuAssistant | Smart Allergy Menu Assistant

> **Protect your dining safety—order with confidence, not anxiety.**
> A smart assistant that detects allergens in restaurant menus using OCR and multi-agent LLMs.

---

## Introduction

**AllergyMenuAssistant** is an intelligent assistant powered by LLMs (Large Language Models) and OCR technology. It is designed to solve a common pain point for people with food allergies—difficulty identifying ingredients when dining out.

Users simply upload a photo of a restaurant menu. The system then uses multiple AI agents to automatically recognize dish names, analyze potential allergens, and generate a “traffic light” style recommendation list based on the user’s predefined allergies.

### Key Features

* **Personalized Allergy Settings**: Store user-specific allergens (e.g., peanuts, shellfish, dairy).
* **Menu Image Recognition**: Upload menu photos directly from a phone and convert them into text using OCR.
* **Multi-Agent Analysis**: Three specialized LLM agents collaborate to clean, analyze, and match data for higher accuracy.
* **Real-Time Feedback**: Provides three categories:

  * ✅ Safe to eat
  * ❌ Not safe to eat
  * ⚠️ Use caution

---

## Architecture & Workflow

This project adopts a **multi-agent architecture**, breaking down the complex allergen analysis task into three stages to improve accuracy.

### Workflow Overview

1. User inputs personal allergens
2. User uploads a menu photo
3. OCR (Tesseract) extracts text
4. LLM processing pipeline:

   * Agent 1: Cleans OCR output and extracts dish names
   * Agent 2: Analyzes ingredients and potential allergens
   * Agent 3: Matches results with user allergy data and produces final recommendations
5. Results are returned to the user

---

## Agent Responsibilities

1. **Agent 1 (Dish Name Extractor)**
   Handles noisy OCR output and formatting errors to accurately extract dish names from the menu.

2. **Agent 2 (Allergen Analyzer)**
   Uses LLM knowledge to infer possible ingredients and allergens for each dish.

3. **Agent 3 (Allergy Matcher)**
   Compares analyzed ingredients with the user’s allergy profile and outputs final recommendations.

---

## Project Structure

This project follows a microservices architecture and is mainly divided into:

* `menu-analysis` (core analysis service)
* `telegram-bot` (user interface service)
* `line-bot` (user interface service)

```
AllergyMenuAssistant
├── Dockerfile                  # Root Docker configuration
├── README.md                   # Project documentation
├── database
│   └── init.sql                # Database initialization script
├── docker-compose.dev.yml      # Development environment Docker Compose
├── docker-compose.yml          # Production environment Docker Compose
├── menu-analysis               # [Core Service] Handles OCR and LLM analysis
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src
│   │   ├── db_connection.py    # Database connection
│   │   ├── llm.py              # LLM agent logic implementation
│   │   ├── main.py             # Service entry point
│   │   ├── ocr.py              # OCR image processing
│   │   └── user_data_handler.py
│   └── uv.lock                 # uv package lock file
├── telegram-bot                # [Interface Service] Handles user interaction
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src
│   │   ├── db_connection.py
│   │   ├── main.py             # Bot entry point
│   │   ├── send_analysis.py    # Send requests for analysis
│   │   └── user_data_handler.py
│   └── uv.lock
└── line-bot                    # [Interface Service] Handles user interaction
    ├── Dockerfile
    ├── pyproject.toml
    ├── src
    │   ├── db_connection.py
    │   ├── main.py             # Bot entry point
    │   ├── send_analysis.py    # Send requests for analysis
    │   └── user_data_handler.py
    └── uv.lock
```

---

## 🛠️ Tech Stack

* **Language**: Python 3.13+
* **Package Manager**: `uv` (fast Python package installer)
* **Interfaces**: Telegram Bot API, LINE Bot API
* **AI/ML**:

  * OCR (Tesseract)
  * LLM (Gemini)
* **Database**: PostgreSQL
* **Infrastructure**: Docker, Docker Compose

---

## Getting Started

### Prerequisites

* Docker & Docker Compose installed
* Telegram Bot Token (from @BotFather)
* LINE Channel Access Token & Secret
* LLM API Key (e.g., OPENAI_API_KEY)

---

### 1. Clone the Project

```bash
git clone https://github.com/dddanielliu/AllergyMenuAssistant.git
cd AllergyMenuAssistant
```

---

### 2. Environment Variables

Create a `.env` file in the root directory and fill in the required API keys (see `.env.example`):

```env
TELEGRAM_BOT_TOKEN=Example-token
TELEGRAM_BOT_USERNAME=@example

LINE_CHANNEL_ACCESS_TOKEN=Example-token
LINE_CHANNEL_SECRET=Example-secret

DB_DATABASE=AllergyMenuAssistant
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_HOSTNAME=db
DB_PORT=5432

USER_GEMINI_API_ENCRYPTION_KEY=
```

`USER_GEMINI_API_ENCRYPTION_KEY` is used to encrypt the Gemini API key provided by users during conversations. Be sure to generate and use a strong key.

---

### 3. Start the Services

#### Production Mode

```bash
docker compose up -d --build
```

#### Development Mode

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

---

### 4. Stop Services

```bash
docker compose down
```

---

### 5. Usage

1. Open Telegram and find your bot
2. Type `/start`
3. Enter your allergens (e.g., peanuts, shrimp)
4. Upload a clear menu photo
5. Wait for the analysis results

---

## Example Results

|               Step 1: Setup & Upload              |                Step 2: System Analysis                |                                                Step 3: Get Recommendations                                                |
| :-----------------------------------------------: | :---------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------------: |
| User enters allergens<br>and uploads a menu image | System performs OCR and<br>three-stage agent analysis | **✅ Safe**: Stir-fried cabbage<br>**❌ Not safe**: Kung Pao Chicken (contains peanuts)<br>**⚠️ Caution**: Seafood tofu pot |

<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/a2ecf429-a31b-46b2-86bb-818c2c420c5d" width="250"></td>
    <td><img src="https://github.com/user-attachments/assets/9b389085-3c4b-47d3-87c4-d9be391cbb8a" width="250"></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/c299957b-cf7d-4b51-a682-05081332abec" width="250"></td>
    <td><img src="https://github.com/user-attachments/assets/c6e7e991-24e5-4e96-8027-dd87747ee9df" width="250"></td>
  </tr>
</table>
