# Gen AI Chatbot with Amazon Bedrock Knowledge Base + Aurora (pgvector) + Streamlit

This project demonstrates a **Retrieval-Augmented Generation (RAG)**-powered **Gen AI Chatbot** that integrates:
- **Amazon Bedrock** for Large-Language-Model inference using **Anthropic Claude**
- **Amazon RDS Aurora (PostgreSQL)** with **pgvector** extension for vector storage and semantic retrieval
- **Amazon Bedrock Knowledge Base** for retrieval orchestration
- **Streamlit** UI for local experimentation on your Mac  
All components connect securely to AWS using environment-based credentials.

---

## 📊 Architecture Diagram

**Flow:**  
`User Query → Streamlit App → Bedrock Knowledge Base (pgvector + Aurora) → Anthropic Claude → SQL response → Run SQL against Amazon Aurora postgres & retrieve data --> Return formatted data --> Streamlit UI`

---

## Key Features
- **Retrieval-Augmented Generation (RAG)** via Amazon Bedrock Knowledge Base  
- **pgvector**-based semantic embedding search in Aurora PostgreSQL  
- **Anthropic Claude** LLM for intelligent contextual responses  
- **Streamlit UI** for interactive conversation and visualization  
- **Secure AWS authentication** using environment variables  

---

## 🧩 Tech Stack
| Component | Technology |
|------------|-------------|
| **Frontend/UI** | Streamlit |
| **Backend (AI)** | Amazon Bedrock + Anthropic Claude |
| **Knowledge Base & RAG** | Amazon Bedrock Knowledge Base + Aurora (pgvector) |
| **Database** | Amazon RDS Aurora PostgreSQL |
| **Language** | Python 3 |
| **Libraries** | `boto3`, `psycopg2-binary`, `streamlit` |
| **Environment** | Local Mac virtual environment |

---

## Setup Instructions

### Clone the Repository
```bash
git clone https://github.com/nehar1106/GenAI_SQL_chatbot.git
cd GenAI_SQL_chatbot

python3 -m venv myenv
source myenv/bin/activate
pip install boto3 psycopg2-binary
pip3 install streamlit 

# Export the AWS access_key, secret_key, session_token
# Open RDS (5432 ) port to your IP, as streamlit is running on your laptop

export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export AWS_SESSION_TOKEN=
```

### Run the application
streamlit run nl2sql_chatbot_app_anthropic.py

