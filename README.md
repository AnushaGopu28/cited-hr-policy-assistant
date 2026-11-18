# Cited HR Policy Assistant (RAG)



**Training project only.** Pine Harbor Analytics and its consultant handbook are fictional. This project is an educational prototype, not legal, tax, immigration, payroll, employment, or HR advice.



\## 1. Project Overview



The Cited HR Policy Assistant is a retrieval-augmented generation (RAG) project designed to answer questions using approved reference documents.



The project demonstrates how a document-based assistant can:



- Ingest fictional company handbook content and selected public reference sources.

- Split documents into smaller text chunks.

- Generate semantic embeddings.

- Store and search document embeddings using FAISS.

- Retrieve relevant passages for a user question.

- Provide source-aware responses and a fallback when information is unavailable.

- Evaluate retrieval and answer quality using a manually reviewed question set.

- Apply basic security principles when handling retrieved content.



The project uses fictional company information and public reference material. Public government sources are general references and must not be treated as Pine Harbor Analytics company policy.



\## 2. Technology Stack



- **Language:** Python

- **Embeddings:** Sentence Transformers

- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`

- **Vector search:** FAISS

- **Data processing:** Python, JSON, CSV

- **Document sources:** Markdown, PDF, and selected public web pages

- **Environment:** Python virtual environment

- **Evaluation:** CSV-based question set and manual review

- **Local language model:** Ollama with `llama3.2:3b`



\## 3. Architecture



The project follows a document ingestion, retrieval, and answer-generation workflow.



1. **Document ingestion:** `app/ingest.py` processes the fictional consultant handbook, local PDF documents, and selected public reference pages.

2. **Text chunking:** Documents are divided into smaller chunks to support retrieval. The configured starting approach uses approximately 900 characters per chunk with 150 characters of overlap.

3. **Embedding generation:** Sentence Transformers converts document chunks into numerical vectors using `all-MiniLM-L6-v2`.

4. **Vector indexing:** FAISS stores normalized vectors and supports similarity search.

5. **Retrieval:** `app/retrieval.py` retrieves relevant document chunks for a question. The default retrieval setting is `top_k=3`.

6. **Answer handling:** `app/answer.py` uses retrieved context and answer rules to produce a response or fallback.

7. **Evaluation:** The evaluation workflow runs a set of questions and records outputs for human review.



Retrieved document content is treated as untrusted data. Instructions embedded inside retrieved passages should not override the assistant's instructions.



\## 4. Document Ingestion Results



The ingestion process was executed locally.



Observed results from the completed ingestion run:



| Item | Result |

|---|---|

| Successfully processed sources | 10 |

| Failed sources | 1 |

| Total indexed chunks | 667 |

| Embedding generation | Completed |

| FAISS index creation | Completed |



One public source, an OSHA page, returned HTTP 403 during ingestion. This means that source was not successfully retrieved in that run.



The indexed content included the fictional consultant handbook, local PDF documents, and selected public government references.



The generated index and chunk data are stored locally. The ingestion process can be rerun when source documents or ingestion settings change.



\## 5. Running the Project



\### Prerequisites



- Python 3.10 or later recommended.

- Project dependencies installed from `requirements.txt`.

- Internet access for downloading required public sources or the embedding model during setup, when needed.



\### Activate the virtual environment



On Windows Command Prompt:



```cmd

venv\\Scripts\\activate

```



\### Install dependencies



```cmd

pip install -r requirements.txt

```



\### Build or refresh the document index



Run from the project root:



```cmd

python -m app.ingest

```



This processes the configured documents, generates embeddings, and creates the local search index.



\### Run the evaluation



```cmd

python -m eval.run_eval

```



The evaluation outputs are written to:



```text

eval/run_outputs.csv

```



The local evaluation does not require a paid OpenAI API call when `LOCAL_TEST_MODE=true` is configured.



\## 6. Evaluation Methodology



The project uses a 25-question evaluation set covering:



- Answerable questions (15).

- Unanswerable questions (5).

- Questions requesting personal, legal, or other determinations (5).



The evaluation includes automated retrieval checks, live local Ollama answer generation, and a separate set of manually reviewed answer checks.



\### Evaluation results



| Evaluation measure | Observed result |

|---|---:|

| Questions in retrieval evaluation | 25 |

| Retrieval hits | 25/25 (100%) |

| Live Ollama answers generated | 25 |

| Live Ollama answers with completed numeric quality scores | 0/25 |

| Separate manual answer checks | 10 |

| Manual answer checks marked PASS | 10/10 |

| Live Ollama security tests recorded as passing | 4/4 |



\### How to interpret the results



- **Retrieval hits (25/25):** Every question retrieved at least one expected source in the recorded retrieval evaluation. This does not prove that every generated answer is correct.

- **Live Ollama generation (25 answers):** The local `llama3.2:3b` model generated answers through the application pipeline. These answers are recorded in `eval/run_outputs_ollama.csv`; their numeric groundedness, relevance, citation, and refusal scores remain pending independent review.

- **Manual answer checks (10/10 PASS):** Ten selected answers were manually checked and marked PASS in `eval/manual_answer_checks.csv`. These are qualitative pass/fail checks, not a numeric groundedness or relevance score across all 25 questions.

- **Security tests (4/4 PASS):** Four limited security tests were executed through the live local Ollama path. Their results are in `eval/security_tests.csv`. They do not constitute comprehensive security validation.



The retrieval baseline was 14/25 (56%). The improved retrieval result was 25/25 (100%), an increase of 44 percentage points. Answer-quality scores were not available for a comparable before-and-after numeric evaluation.



These results describe the specific test datasets and checks recorded in this repository. They do not establish production readiness or guarantee performance on other questions or documents.



\## 7. Local Ollama Model and AI Disclosure



The project supports a local Ollama integration for live answer generation without requiring a paid OpenAI API call.



The live local configuration used:



- **Model:** `llama3.2:3b`

- **Provider/runtime:** Ollama

- **Application integration:** Local Ollama chat API

- **Execution mode:** `LOCAL_TEST_MODE=false`



When the local Ollama service is running and the live configuration is enabled, the application sends retrieved document context and the user's question to the local model to generate an answer.



The project also retains a rule-based local test mode. Rule-based responses and live Ollama-generated responses are separate execution paths and should not be described as the same evaluation.



Twenty-five live Ollama answers were generated and saved in `eval/run_outputs_ollama.csv`. Their numeric groundedness, relevance, citation, and refusal scores remain pending independent review.



The local model avoids a paid external API call, but its answers still require evaluation. Local execution does not guarantee factual accuracy, complete security, or production readiness.



\## 8. Security, Privacy, and Responsible Use



The project follows these principles:



- Use fictional or synthetic company information for testing.

- Do not place real consultant personal information in the document corpus.

- Never commit `.env` files, API keys, passwords, or access tokens.

- Treat retrieved passages as untrusted data rather than executable instructions.

- Do not allow retrieved content to override system-level instructions.

- Use citations to make the supporting source passages identifiable.

- Use the fallback response when approved documents do not contain the requested information.

- Do not make individual legal, tax, immigration, payroll, employment, or eligibility determinations.

- The assistant cannot approve expenses, leave, payroll changes, or access requests.



Security test cases are maintained in `eval/security_tests.csv`. Listing a test case does not establish that it passed. Actual execution results must be recorded separately.



\## 9. Known Limitations



- The handbook is fictional and intended only for training.

- Public government reference pages are not company policy.

- One public source failed to download during the recorded ingestion run.

- The project supports both rule-based local test mode and live Ollama generation. Numeric quality evaluation of all live Ollama answers remains pending.

- Evaluation results are based on a limited set of 25 questions.

- Retrieval success does not independently guarantee answer correctness.

- The project is not a production HR assistant and should not be used to make real employment or compliance decisions.



\## 10. Future Improvements



Potential improvements include:



- Expand the evaluation set with additional answerable, unanswerable, and determination questions.

- Complete independent numeric quality scoring of the generated live Ollama answers.

- Improve retrieval quality through measured chunk-size and `top_k` comparisons.

- Add automated regression tests for retrieval, citations, fallback behavior, and security boundaries.

- Retry or replace unavailable public sources and record source freshness.

- Add broader security testing and document the actual results.

- Improve monitoring, error handling, and production-readiness checks.



Any claimed improvement should be supported by measured results from comparable evaluation runs.



\## 11. Project Completion Summary



The project completed its document ingestion and FAISS indexing workflow, with 667 chunks indexed. One attempted public source failed during ingestion, as documented in the project limitations.



The recorded evaluation and testing results are:



- **Retrieval evaluation:** 25/25 expected-source hits (100%), compared with the baseline of 14/25 (56%).

- **Live Ollama generation:** 25 answers generated using the local `llama3.2:3b` model. Numeric answer-quality scores remain pending independent review.

- **Manual answer checks:** 10 selected answers manually reviewed and marked PASS (10/10). These are qualitative checks, not numeric groundedness or relevance scores.

- **Security testing:** Four limited live Ollama security tests recorded as PASS (4/4). These tests do not establish comprehensive security.



Python compilation checks were completed for the modified application and evaluation modules.



The project is an educational RAG prototype. The recorded results do not establish production readiness or guarantee performance on other questions, documents, or security scenarios.



**Project classification:** Educational RAG prototype — local Ollama integration, retrieval evaluation, qualitative answer checks, and limited security testing completed.
