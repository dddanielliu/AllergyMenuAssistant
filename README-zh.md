# 🥗 AllergyMenuAssistant | 智能過敏菜單助理

> **守護您的飲食安全，讓點餐不再提心吊膽。**
> A Smart Assistant detecting allergens in restaurant menus using OCR and Multi-Agent LLMs.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED)
![Telegram Bot](https://img.shields.io/badge/Interface-Telegram%20Bot-2CA5E0)
![LINE Bot](https://img.shields.io/badge/Interface-LINE%20Bot-00B900)
![Package Manager](https://img.shields.io/badge/uv-managed-purple)

## 專案簡介 (Introduction)

**AllergyMenuAssistant** 是一個基於 LLM (大型語言模型) 與 OCR 技術的智能助理。旨在解決過敏族群在外出用餐時，難以判斷菜單成份的痛點。

使用者只需上傳餐廳菜單圖片，系統即會透過多重 AI Agent 協作，自動識別菜名、分析潛在過敏原，並根據使用者預設的過敏體質，生成一份紅綠燈式的「食用建議清單」。

### 核心功能
* **個人化過敏設定**：紀錄使用者特定的過敏源（如：花生、蝦蟹、乳製品等）。
* **菜單影像辨識**：支援手機直接拍攝菜單上傳，透過 OCR 轉化為文字。
* **多重 Agent 分析**：透過三個專職的 LLM Agent 進行清洗、分析與比對，確保判斷精準。
* **即時建議回饋**：提供「✅ 可食用」、「❌ 不可食用」、「⚠️ 需注意」三類清單。

---

## 系統架構與工作流 (Architecture & Workflow)

本專案採用 **Multi-Agent** 架構，將複雜的過敏分析任務拆解為三個階段，以提高準確度。

```mermaid
graph TD
    %% 定義樣式
    classDef user fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef ai fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef data fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;

    %% 節點定義
    Start([使用者輸入個人過敏原]):::user
    InputPhoto[使用者拍攝/上傳菜單]:::user
    
    OCR[Tesseract OCR 文字辨識]:::process
    
    subgraph AI_Processing ["LLM 流程"]
        direction TB
        LLM1[LLM Agnet 1: 解析 OCR <br/>提取純淨菜名清單]:::ai
        LLM2[LLM Agent 2: 知識庫檢索 <br/>分析每道菜潛在成分/過敏原]:::ai
        LLM3[LLM Agent 3: 比對使用者過敏原與菜色成分， <br/>輸出最終清單（可食用、不可食用、需注意）]:::ai
    end
    
    Result([回傳使用者]):::data

    %% 流程連接
    Start --> InputPhoto
    
    InputPhoto --> OCR
    OCR -- 雜亂文字數據 --> LLM1
    LLM1 -- 標準化菜名 --> LLM2
    
    LLM2 -- 菜色成分資料庫 --> LLM3
    Start -- 個人過敏資料 --> LLM3
    
    LLM3 --> Result
````

### Agent 職責說明

1.  **Agent 1 (菜名提取器)**：負責處理 OCR 後可能出現的亂碼或排版錯誤，精準提取出菜單上的料理名稱。
2.  **Agent 2 (過敏原列出器)**：利用 LLM 的知識庫，分析每一道菜名可能的食材組成與潛在過敏原。
3.  **Agent 3 (過敏比對判斷器)**：將 Agent 2 的分析結果與使用者的個人過敏資料庫進行比對，輸出最終建議。

-----

## 專案結構 (Project Structure)

本專案採用微服務架構設計，主要分為 `menu-analysis` (核心分析服務) 與 `telegram-bot` (介面服務)。

```bash
AllergyMenuAssistant
├── Dockerfile                  # 根目錄 Docker 配置
├── README.md                   # 專案說明文件
├── database
│   └── init.sql                # 資料庫初始化腳本
├── docker-compose.dev.yml      # 開發環境 Docker Compose
├── docker-compose.yml          # 生產環境 Docker Compose
├── menu-analysis               # [核心服務] 負責 OCR 與 LLM 分析
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src
│   │   ├── db_connection.py    # 資料庫連線
│   │   ├── llm.py              # LLM Agent 邏輯實作
│   │   ├── main.py             # 服務入口點
│   │   ├── ocr.py              # OCR 影像處理
│   │   └── user_data_handler.py
│   └── uv.lock                 # uv 套件鎖定檔
├── telegram-bot                # [介面服務] 負責與使用者互動
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src
│   │   ├── db_connection.py
│   │   ├── main.py             # Bot 啟動入口
│   │   ├── send_analysis.py    # 傳送進行分析
│   │   └── user_data_handler.py
│   └── uv.lock
└── line-bot                    # [介面服務] 負責與使用者互動
    ├── Dockerfile
    ├── pyproject.toml
    ├── src
    │   ├── db_connection.py
    │   ├── main.py             # Bot 啟動入口
    │   ├── send_anaylsis.py    # 傳送進行分析
    │   └── user_data_handler.py
    └── uv.lock
```

-----

## 🛠️ 技術堆疊 (Tech Stack)

  * **語言**: Python 3.13+
  * **套件管理**: `uv` (Fast Python package installer)
  * **介面**: Telegram Bot API, LINE Bot API
  * **AI/ML**:
      * OCR (Tesseract)
      * LLM (Gemini)
  * **資料庫**: PostgreSQL
  * **基礎設施**: Docker, Docker Compose

-----

## 快速開始 (Getting Started)

### 前置需求

  * Docker & Docker Compose installed
  * Telegram Bot Token (From @BotFather)
  * LINE Channel Access Token & Channel Secret (From LINE Developers Console)
  * LLM API Key (e.g., OPENAI\_API\_KEY)

### 1\. Clone 專案

```bash
git clone https://github.com/dddanielliu/AllergyMenuAssistant.git
cd AllergyMenuAssistant
```

### 2\. 環境變數設定

請在根目錄建立 `.env` 檔案，填入必要的 API Keys，您可以參考 `.env.example`

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

# 用於加密使用者 Gemini API Key 的密鑰，請務必更換為您自己的高強度密鑰
# 可使用 openssl rand -hex 32 指令生成
USER_GEMINI_API_ENCRYPTION_KEY=
```

`USER_GEMINI_API_ENCRYPTION_KEY` 用於加密使用者在對話中提供的 Gemini API 金鑰，以提升安全性。請務必設定一個您自己的高強度密鑰。

### 3. 啟動服務

本專案提供生產 (Production) 與開發 (Development) 兩種啟動模式。

#### 生產模式

使用 `docker-compose.yml` 啟動所有服務。此模式下，程式碼會被建置進映像檔中。

```bash
docker compose up -d --build
```

#### 開發模式

使用 `docker-compose.dev.yml` 啟動。此模式會將本地的程式碼目錄掛載 (mount) 到容器中，當您修改程式碼時，服務會自動重啟，適合開發階段使用。

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

### 4. 停止服務

若要停止所有服務並移除容器，請執行：

```bash
docker compose down
# 如果使用開發模式，請指定對應的 compose file
# docker compose -f docker-compose.dev.yml down
```

### 5. 開始使用

1.  打開 Telegram，找到您的 Bot。
2.  輸入 `/start` 開始對話。
3.  依照指示輸入您的過敏原（例如：花生, 蝦子）。
4.  上傳一張清晰的菜單照片。
5.  等待分析結果！

-----

## 實作成果範例

| 步驟 1: 設定與上傳 | 步驟 2: 系統分析 | 步驟 3: 獲得建議 |
| :---: | :---: | :---: |
| 使用者輸入過敏原<br>並上傳菜單圖片 | 系統進行 OCR 與<br>三階段 Agent 分析 | **✅ 可食**: 炒高麗菜<br>**❌ 不可食**: 宮保雞丁(含花生)<br>**⚠️ 需注意**: 海鮮豆腐煲 |

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
