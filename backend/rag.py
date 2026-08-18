from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import gemini_is_configured, settings
from database import DatabaseError
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

        context_text = "\n---\n".join(context_blocks)

        system_prompt = (
            "You are an advanced document intelligence assistant specialized in multi-document analysis and retrieval-augmented generation (RAG).\n"
            "You are provided with retrieved context from uploaded files (e.g. price lists, guides, FAQs, policies, manuals, etc.).\n\n"
            "INSTRUCTIONS:\n"
            "1. Answer the query thoroughly, objectively, and accurately using ONLY the provided document context.\n"
            "2. MULTI-DOCUMENT ANALYSIS: If the user query asks to compare, analyze, or synthesize details from different documents or categories:\n"
            "   - Group your analysis clearly and reference the source files by name.\n"
            "   - Highlight similarities, differences, pricing details, requirements, or services specific to each document.\n"
            "3. ACCURATE CITATIONS: Cite your sources inline using square brackets matching the source number, e.g., '[1]', '[2]'. If multiple sources support a point, cite them together (e.g. '[1][2]').\n"
            "4. FORMATTING: Use clean markdown headers (#### Header) and bullet points for high legibility.\n"
            "5. GROUNDING & FIDELITY: Base your response strictly on the retrieved context below. If context for the query is missing, state clearly that it is not present in the uploaded files.\n\n"
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

    def _answer_from_general_knowledge(self, user_query: str, partial_context: str = "") -> Dict[str, Any]:
        """
        Generate an answer using general knowledge when uploaded documents do not contain sufficient context.
        """
        if partial_context:
            system_prompt = (
                "You are a professional document intelligence assistant.\n\n"
                "The user asked a question. The uploaded documents contain partial information "
                "but do not fully answer the query. Below is the partial context found:\n\n"
                "--- PARTIAL DOCUMENT CONTEXT ---\n"
                "{context}\n"
                "--- END PARTIAL CONTEXT ---\n\n"
                "INSTRUCTIONS:\n"
                "1. Share relevant findings from the uploaded documents first.\n"
                "2. Supplement with general knowledge to provide a comprehensive answer.\n"
                "3. Clearly mark the general knowledge section with:\n"
                "   '> **Note:** The following details are based on general knowledge, not your uploaded files.'\n"
                "4. Use clean headers (#### Header) and bullet points.\n"
            )
        else:
            system_prompt = (
                "You are a professional document intelligence assistant.\n\n"
                "The user asked a question, but no relevant information was found in the uploaded documents.\n\n"
                "INSTRUCTIONS:\n"
                "1. Answer using general knowledge.\n"
                "2. Begin your response with:\n"
                "   '> **Note:** This response is generated from general knowledge. "
                "It is not based on your uploaded documents.'\n"
                "3. Use clean headers (#### Header) and bullet points.\n"
            )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        chain = prompt | self._get_llm() | StrOutputParser()

        inputs = {"question": user_query}
        if partial_context:
            inputs["context"] = partial_context

        answer = self._invoke_with_fallback(chain, inputs)

        return {
            "answer": answer,
            "sources": [],
            "index_names": [],
            "companies": [],
            "response_type": "general_knowledge"
        }

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        chain = prompt | self._get_llm() | StrOutputParser()

        inputs = {"question": user_query}
        if partial_context:
            inputs["context"] = partial_context

        answer = self._invoke_with_fallback(chain, inputs)

        return {
            "answer": answer,
            "sources": [],
            "index_names": [],
            "companies": [],
            "response_type": "general_knowledge"
        }

    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Main query pipeline implementing multi-document balanced retrieval & multi-company RAG synthesis.
        """
        # Retrieve up to 16 candidate chunks across all uploaded documents with balanced sampling
        try:
            retrieved_chunks = vector_store.similarity_search(user_query, k=16, per_doc_k=4)
        except DatabaseError as exc:
            # Chat remains useful when Supabase is unavailable. The response is
            # explicitly marked as general knowledge because no policy context
            # could be retrieved or cited.
            print(f"[RAG] Document retrieval unavailable: {exc}")
            return self._answer_from_general_knowledge(user_query)

        if not retrieved_chunks:
            print(f"[RAG] No indexed documents found. Fallback to general knowledge for: '{user_query[:80]}...'")
            return self._answer_from_general_knowledge(user_query)

        strong_matches = [c for c in retrieved_chunks if c["score"] >= RELEVANCE_THRESHOLD]
        weak_matches = [c for c in retrieved_chunks if c["score"] < RELEVANCE_THRESHOLD]

        print(f"[RAG] Multi-Doc Retrieval: {len(retrieved_chunks)} candidate chunks found. "
              f"{len(strong_matches)} strong (>={RELEVANCE_THRESHOLD}), {len(weak_matches)} weak. "
              f"Top score: {retrieved_chunks[0]['score']:.3f}")

        if strong_matches:
            # Use top strong matches (up to 10 chunks across documents for multi-company context)
            top_chunks = strong_matches[:10]
            return self._answer_from_documents(user_query, top_chunks)

        if weak_matches:
            partial_parts = []
            for chunk in weak_matches[:4]:
                company = chunk.get("company") or "Corporate Policy"
                partial_parts.append(
                    f"[Company: {company} | File: {chunk['filename']} | Section: {chunk['metadata'].get('section', 'N/A')} | Score: {int(chunk['score'] * 100)}%]\n{chunk['content']}"
                )
            partial_context = "\n---\n".join(partial_parts)

            print(f"[RAG] Weak matches only. Generating hybrid response.")
            return self._answer_from_general_knowledge(user_query, partial_context=partial_context)

        return self._answer_from_general_knowledge(user_query)


rag_pipeline = PolicyRAGPipeline()
