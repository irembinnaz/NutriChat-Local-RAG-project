# 🥗 NutriChat - Local RAG Nutrition Assistant

NutriChat is a local AI-powered nutrition assistant developed using **Microsoft Foundry Local**, **Retrieval-Augmented Generation (RAG)**, **SQLite**, and **Streamlit**.

The application allows users to calculate meal nutrition values, track daily nutrition totals, check individual foods, and ask nutrition-related questions using a local knowledge base.

## ✨ Features

- Meal calorie and macronutrient calculation
- Single food calorie checking
- Daily nutrition tracking
- Local nutrition question-answering
- SQLite-based data storage
- RAG-based retrieval from local nutrition documents
- Local LLM inference with Foundry Local

## 🧠 How It Works

The nutrition documents are divided into smaller text chunks and converted into vector representations using an embedding model.

When the user asks a nutrition question, the system creates an embedding for the question and compares it with the stored document embeddings using cosine similarity.

The most relevant information is then provided as context to a local language model, which generates the final response.

## 🤖 Models and Technologies

- Microsoft Foundry Local
- Phi-3.5 Mini
- Qwen3 Embedding 0.6B
- Retrieval-Augmented Generation (RAG)
- Python
- SQLite
- Streamlit
- Cosine Similarity
- USDA FNDDS food data

## 🧪 Testing

The project was tested with:

- Complete meal calculations
- Single food calculations
- Daily nutrition tracking
- Nutrition-related questions
- Questions outside the nutrition knowledge base
- Unknown and ambiguous food inputs

During testing, an issue was identified where incomplete meals could still affect the daily nutrition log. A validation step was added so that meals containing an unidentified food are not saved.

## 📚 What I Learned

During this project, I gained practical experience with:

- RAG systems
- Text chunking
- Embeddings
- Information retrieval
- Cosine similarity
- Prompt engineering
- Local LLM usage
- SQLite integration
- Streamlit interface development
- Testing and debugging AI applications

## ⚠️ Limitations

Since the language model runs locally on CPU, some RAG responses may take longer to generate.

NutriChat is developed for educational purposes and is not intended to replace professional medical or dietary advice.

## 👩‍💻 Author

Developed as part of a Microsoft Foundry Local summer project.
