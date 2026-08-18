from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import gemini_is_configured, settings
from database import DatabaseError, get_document_by_id, get_all_documents
from vector_store import vector_store

# Relevance threshold: cosine similarity score threshold for document grounding
RELEVANCE_THRESHOLD = settings.RELEVANCE_THRESHOLD


class PolicyRAGPipeline:
    def __init__(self):
        self.llm = None

    def _create_llm(self, model_name: str) -> ChatGoogleGenerativeAI:
        """Create a Gemini LLM instance with the specified model."""
        if not gemini_is_configured():
            raise RuntimeError("GEMINI_API_KEY is not configured. Add it to backend/.env before using the chat endpoint.")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.1
        )

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        if self.llm is None:
            self.llm = self._create_llm(settings.LLM_MODEL)
        return self.llm

    def _invoke_with_fallback(self, chain, inputs: dict) -> str:
        """
        Invoke the LLM chain with automatic fallback to secondary model
        if primary model is unavailable.
        """
        try:
            return chain.invoke(inputs)
        except Exception as primary_err:
            print(f"Primary LLM ({settings.LLM_MODEL}) failed: {primary_err}")
            print(f"Falling back to {settings.LLM_FALLBACK_MODEL}...")
            try:
                fallback_llm = self._create_llm(settings.LLM_FALLBACK_MODEL)
                fallback_chain = chain.first | fallback_llm | StrOutputParser()
                return fallback_chain.invoke(inputs)
            except Exception as fallback_err:
                print(f"Fallback LLM also failed: {fallback_err}")
                raise primary_err

    def _answer_from_documents(self, user_query: str, retrieved_chunks: List[Dict]) -> Dict[str, Any]:
        """
        Generate an answer strictly grounded in retrieved document chunks across multiple source files.
        """
        context_blocks = []
        sources_list = []
        index_names_set = set()
        companies_set = set()

        for idx, chunk in enumerate(retrieved_chunks):
            citation_num = idx + 1
            filename = chunk["filename"]
            company = chunk.get("company") or chunk.get("metadata", {}).get("company") or "Document Library"
            tag = chunk["tag"] or "DOCUMENT"
            content = chunk["content"]
            score = chunk["score"]
            meta = chunk["metadata"] or {}
            section = meta.get("section", f"Page {meta.get('page', 1)}")

            context_blocks.append(
                f"Source [{citation_num}]:\n"
                f"Document Title: {filename} (Category: {tag})\n"
                f"Namespace / Category: {company}\n"
                f"Section: {section}\n"
                f"Content Snippet: {content}\n"
            )

            sources_list.append({
                "id": citation_num,
                "company": company,
                "filename": filename,
                "tag": tag,
                "section": section,
                "score": f"{int(score * 100)}%",
                "content": content
            })

            index_names_set.add(tag)
            companies_set.add(company)

        context_text = "\n---\n".join(context_blocks) if context_blocks else "[No relevant text snippets retrieved from the documents]"

        system_prompt = (
            "You are an advanced document intelligence assistant specialized in multi-document analysis and retrieval-augmented generation (RAG).\n"
            "You are provided with retrieved context from uploaded files (e.g. price lists, guides, FAQs, policies, manuals, etc.).\n\n"
            "INSTRUCTIONS:\n"
            "1. Answer the query thoroughly, objectively, and accurately using ONLY the provided document context. Do NOT use general knowledge or make assumptions not supported by the context.\n"
            "2. MULTI-DOCUMENT ANALYSIS: If the user query asks to compare, analyze, or synthesize details from different documents or categories:\n"
            "   - Group your analysis clearly and reference the source files by name.\n"
            "   - Highlight similarities, differences, pricing details, requirements, or services specific to each document.\n"
            "3. ACCURATE CITATIONS: Cite your sources inline using square brackets matching the source number, e.g., '[1]', '[2]'. If multiple sources support a point, cite them together (e.g. '[1][2]').\n"
            "4. FORMATTING: Use clean markdown headers (#### Header) and bullet points for high legibility.\n"
            "5. GROUNDING & FIDELITY: Base your response strictly on the retrieved context below. If the context does not contain the answer, state clearly and explicitly: 'I could not find the answer to this question in the uploaded document(s).'\n\n"
            "RETRIEVED DOCUMENT CONTEXT:\n"
            "{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        chain = prompt | self._get_llm() | StrOutputParser()
        answer = self._invoke_with_fallback(chain, {
            "context": context_text,
            "question": user_query
        })

        return {
            "answer": answer,
            "sources": sources_list,
            "index_names": sorted(list(index_names_set)),
            "companies": sorted(list(companies_set)),
            "response_type": "document_grounded"
        }

    def _answer_from_selected_document(self, user_query: str, retrieved_chunks: List[Dict], document_name: str) -> Dict[str, Any]:
        """
        Generate an answer strictly grounded in the selected document, verifying if the requested details are available.
        """
        context_blocks = []
        sources_list = []

        for idx, chunk in enumerate(retrieved_chunks):
            citation_num = idx + 1
            filename = chunk["filename"]
            company = chunk.get("company") or chunk.get("metadata", {}).get("company") or "Document Library"
            tag = chunk["tag"] or "DOCUMENT"
            content = chunk["content"]
            score = chunk["score"]
            meta = chunk["metadata"] or {}
            section = meta.get("section", f"Page {meta.get('page', 1)}")

            context_blocks.append(
                f"Source [{citation_num}]:\n"
                f"Document Title: {filename}\n"
                f"Section: {section}\n"
                f"Content: {content}\n"
            )

            sources_list.append({
                "id": citation_num,
                "company": company,
                "filename": filename,
                "tag": tag,
                "section": section,
                "score": f"{int(score * 100)}%",
                "content": content
            })

        context_text = "\n---\n".join(context_blocks) if context_blocks else "[No text retrieved from the document]"

        system_prompt = (
            f"You are an advanced document intelligence assistant. Your task is to analyze the selected document '{document_name}' "
            "and answer the user's question. You must verify whether the requested information is actually available in that document.\n\n"
            "INSTRUCTIONS:\n"
            "1. IDENTIFY: Identify clearly what the user is asking for in their question.\n"
            "2. VERIFY & ANALYZE: Review the provided context blocks below (which contain snippets from the selected document). "
            "Verify if the information needed to answer the user's question is actually present in the document. "
            "Gather all the relevant details (like rules, requirements, figures) to answer the query.\n"
            "3. RESPONSE GROUNDING:\n"
            "   - If the information IS available in the document: Answer the question thoroughly, citing the source snippets using square brackets (e.g., '[1]', '[2]'). Use clean markdown formatting.\n"
            "   - If the information IS NOT available or only partially available in this document: State clearly and explicitly that the requested details could not be found or verified in the selected document '{document_name}'. Explain what is missing and answer only what is supported by the document. Do not use external knowledge to invent information that is not in the document.\n"
            "4. STRICT FIDELITY: Rely ONLY on the provided context below. Do not use general knowledge or assume details not present in the document.\n\n"
            "RETRIEVED DOCUMENT CONTEXT:\n"
            "{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        chain = prompt | self._get_llm() | StrOutputParser()
        answer = self._invoke_with_fallback(chain, {
            "context": context_text,
            "question": user_query
        })

        return {
            "answer": answer,
            "sources": sources_list,
            "index_names": [document_name],
            "companies": [],
            "response_type": "document_grounded"
        }

    def query(self, user_query: str, document_id: int | None = None) -> Dict[str, Any]:
        """
        Main query pipeline implementing strictly document-grounded RAG synthesis.
        """
        # 1. Verify that there are documents in the database
        try:
            all_docs = get_all_documents()
            if not all_docs:
                return {
                    "answer": "No documents found in the database. Please upload a document in the Knowledge Base first before asking questions.",
                    "sources": [],
                    "index_names": [],
                    "companies": [],
                    "response_type": "document_grounded"
                }
        except Exception as exc:
            print(f"[RAG] Database connection failed while checking documents: {exc}")
            return {
                "answer": "I cannot answer your question because the database is currently offline or unreachable.",
                "sources": [],
                "index_names": [],
                "companies": [],
                "response_type": "document_grounded"
            }

        # Fetch document name if document_id is provided
        document_name = None
        if document_id is not None:
            try:
                doc = get_document_by_id(document_id)
                if doc:
                    document_name = doc.get("filename")
            except Exception as e:
                print(f"[RAG] Error fetching document metadata: {e}")

        # 2. Retrieve candidate chunks
        try:
            retrieved_chunks = vector_store.similarity_search(user_query, k=16, per_doc_k=4, document_id=document_id)
        except DatabaseError as exc:
            print(f"[RAG] Document retrieval unavailable: {exc}")
            target_name = document_name or "uploaded document(s)"
            return {
                "answer": f"I cannot analyze the {target_name} because the vector store is currently offline.",
                "sources": [],
                "index_names": [document_name] if document_name else [],
                "companies": [],
                "response_type": "document_grounded"
            }

        if document_id is not None:
            target_name = document_name or f"Document ID {document_id}"
            return self._answer_from_selected_document(user_query, retrieved_chunks, target_name)

        if not retrieved_chunks:
            return {
                "answer": "I could not find any relevant information in the uploaded document(s) to answer this question.",
                "sources": [],
                "index_names": [],
                "companies": [],
                "response_type": "document_grounded"
            }

        # General multi-document search across all retrieved chunks
        return self._answer_from_documents(user_query, retrieved_chunks)


rag_pipeline = PolicyRAGPipeline()
