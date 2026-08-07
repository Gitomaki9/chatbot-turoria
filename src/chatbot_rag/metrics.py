import numpy as np
import pandas as pd
from typing import List, Dict, Any, Union, Optional
from tqdm import tqdm
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_fscore_support
from rouge_score import rouge_scorer
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from nltk.tokenize import word_tokenize

# Check if bert-score is available
try:
    from bert_score import score as bert_score

    BERT_SCORE_AVAILABLE = True
except ImportError:
    BERT_SCORE_AVAILABLE = False


class RetrievalMetrics:
    """Class to evaluate retrieval performance in RAG pipelines."""

    def __init__(self):
        """Initialize the RetrievalMetrics class."""
        self.results = {}
        self.results_df = None

    def calculate_recall_at_k(
        self, relevant_docs: List[str], retrieved_docs: List[str], k: int = 5
    ) -> float:
        """
        Calculate Recall@k: The proportion of relevant documents that are retrieved in the top-k results.

        Args:
            relevant_docs: List of relevant document IDs
            retrieved_docs: List of retrieved document IDs (in order)
            k: Number of top results to consider

        Returns:
            Recall@k value
        """
        if not relevant_docs:
            return 1.0  # If there are no relevant docs, we consider all retrieved to be correct

        retrieved_at_k = retrieved_docs[:k]
        relevant_retrieved = [doc for doc in retrieved_at_k if doc in relevant_docs]

        return len(relevant_retrieved) / len(relevant_docs)

    def calculate_precision_at_k(
        self, relevant_docs: List[str], retrieved_docs: List[str], k: int = 5
    ) -> float:
        """
        Calculate Precision@k: The proportion of retrieved documents in the top-k results that are relevant.

        Args:
            relevant_docs: List of relevant document IDs
            retrieved_docs: List of retrieved document IDs (in order)
            k: Number of top results to consider

        Returns:
            Precision@k value
        """
        if k == 0 or not retrieved_docs:
            return 0.0

        retrieved_at_k = retrieved_docs[:k]
        if not retrieved_at_k:
            return 0.0

        relevant_retrieved = [doc for doc in retrieved_at_k if doc in relevant_docs]

        return len(relevant_retrieved) / min(k, len(retrieved_at_k))

    def calculate_mrr(
        self, relevant_docs: List[str], retrieved_docs: List[str]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR): Reciprocal of the rank of the first relevant document.

        Args:
            relevant_docs: List of relevant document IDs
            retrieved_docs: List of retrieved document IDs (in order)

        Returns:
            MRR value
        """
        for i, doc in enumerate(retrieved_docs):
            if doc in relevant_docs:
                return 1.0 / (i + 1)
        return 0.0

    def calculate_ndcg_at_k(
        self, relevant_docs: List[str], retrieved_docs: List[str], k: int = 5
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (nDCG@k).

        Args:
            relevant_docs: List of relevant document IDs
            retrieved_docs: List of retrieved document IDs (in order)
            k: Number of top results to consider

        Returns:
            nDCG@k value
        """
        retrieved_at_k = retrieved_docs[:k]

        # Binary relevance: 1 if document is relevant, 0 otherwise
        relevance_scores = [1 if doc in relevant_docs else 0 for doc in retrieved_at_k]

        # Calculate DCG
        dcg = 0
        for i, rel in enumerate(relevance_scores):
            dcg += rel / np.log2(i + 2)  # i+2 because i is 0-indexed

        # Calculate ideal DCG (sort documents by relevance)
        ideal_relevance = sorted(
            [1 if doc in relevant_docs else 0 for doc in retrieved_docs[:k]],
            reverse=True,
        )
        idcg = 0
        for i, rel in enumerate(ideal_relevance):
            idcg += rel / np.log2(i + 2)

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def evaluate(
        self, queries: List[Dict[str, Any]], k_values: List[int] = [1, 3, 5, 10]
    ) -> pd.DataFrame:
        """
        Evaluate retrieval performance.

        Args:
            queries: List of dictionaries containing:
                - 'query': The query text
                - 'relevant_docs': List of relevant document IDs
                - 'retrieved_docs': List of retrieved document IDs (in order)
            k_values: List of k values for calculating metrics@k

        Returns:
            DataFrame with metrics for each query
        """
        results = []

        for query_data in tqdm(queries, desc="Evaluating queries"):
            query = query_data["query"]
            relevant_docs = query_data["relevant_docs"]
            retrieved_docs = query_data["retrieved_docs"]

            query_metrics = {"query": query}

            # Calculate metrics for different k values
            for k in k_values:
                if k <= len(retrieved_docs) or len(retrieved_docs) > 0:
                    query_metrics[f"precision@{k}"] = self.calculate_precision_at_k(
                        relevant_docs, retrieved_docs, k
                    )
                    query_metrics[f"recall@{k}"] = self.calculate_recall_at_k(
                        relevant_docs, retrieved_docs, k
                    )
                    query_metrics[f"ndcg@{k}"] = self.calculate_ndcg_at_k(
                        relevant_docs, retrieved_docs, k
                    )

            # MRR doesn't depend on k
            query_metrics["mrr"] = self.calculate_mrr(relevant_docs, retrieved_docs)

            results.append(query_metrics)

        # Create DataFrame
        self.results_df = pd.DataFrame(results)

        # Add average metrics row
        avg_metrics = {"query": "AVERAGE"}
        for col in self.results_df.columns:
            if col != "query":
                avg_metrics[col] = self.results_df[col].mean()

        self.results_df = pd.concat(
            [self.results_df, pd.DataFrame([avg_metrics])], ignore_index=True
        )

        return self.results_df

    def plot_metrics(self, metric_name: str = "precision"):
        """
        Plot metrics at different k values.

        Args:
            metric_name: Base name of the metric (e.g., 'precision', 'recall', 'ndcg')
        """
        if self.results_df is None:
            print("No results available for plotting")
            return

        # Get columns that match the metric name
        metric_cols = [
            col for col in self.results_df.columns if col.startswith(metric_name + "@")
        ]
        if not metric_cols:
            print(f"No {metric_name}@k metrics found")
            return

        # Extract k values
        k_values = [int(col.split("@")[1]) for col in metric_cols]

        # Get average values (from the last row)
        avg_values = [self.results_df.iloc[-1][col] for col in metric_cols]

        plt.figure(figsize=(10, 6))
        plt.plot(k_values, avg_values, marker="o", linestyle="-")
        plt.title(f"Average {metric_name.capitalize()}@k")
        plt.xlabel("k")
        plt.ylabel(metric_name.capitalize())
        plt.grid(True)
        plt.show()


class GenerationMetrics:
    """Class to evaluate text generation quality in RAG pipelines."""

    def __init__(self):
        """Initialize the GenerationMetrics class."""
        self.results_df = None

        # Download necessary NLTK resources
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)

    def calculate_rouge(self, reference: str, hypothesis: str) -> Dict[str, float]:
        """
        Calculate ROUGE-1, ROUGE-2, and ROUGE-L scores.

        Args:
            reference: Reference text (ground truth)
            hypothesis: Generated text to evaluate

        Returns:
            Dictionary with ROUGE-1, ROUGE-2, and ROUGE-L F1 scores
        """
        scorer = rouge_scorer.RougeScorer(
            ["rouge1", "rouge2", "rougeL"], use_stemmer=True
        )
        scores = scorer.score(reference, hypothesis)

        return {
            "rouge1": scores["rouge1"].fmeasure,
            "rouge2": scores["rouge2"].fmeasure,
            "rougeL": scores["rougeL"].fmeasure,
        }

    def calculate_bleu(self, reference: str, hypothesis: str) -> float:
        """
        Calculate BLEU score.

        Args:
            reference: Reference text (ground truth)
            hypothesis: Generated text to evaluate

        Returns:
            BLEU score
        """
        reference_tokens = word_tokenize(reference.lower())
        hypothesis_tokens = word_tokenize(hypothesis.lower())

        # Handle empty tokens
        if not reference_tokens or not hypothesis_tokens:
            return 0.0

        smoothing = SmoothingFunction().method1
        return sentence_bleu(
            [reference_tokens], hypothesis_tokens, smoothing_function=smoothing
        )

    def calculate_bert_score(
        self, references: List[str], hypotheses: List[str]
    ) -> Dict[str, List[float]]:
        """
        Calculate BERTScore if available.

        Args:
            references: List of reference texts (ground truths)
            hypotheses: List of generated texts to evaluate

        Returns:
            Dictionary with precision, recall, and F1 scores for each text pair
        """
        if not BERT_SCORE_AVAILABLE:
            return None

        P, R, F1 = bert_score(hypotheses, references, lang="en")

        return {"precision": P.tolist(), "recall": R.tolist(), "f1": F1.tolist()}

    def evaluate(self, data: List[Dict[str, str]]) -> pd.DataFrame:
        """
        Evaluate generation quality.

        Args:
            data: List of dictionaries containing:
                - 'reference': The ground truth answer
                - 'hypothesis': The generated answer

        Returns:
            DataFrame with metrics for each generation
        """
        results = []

        references = [item["reference"] for item in data]
        hypotheses = [item["hypothesis"] for item in data]

        # Calculate BERTScore in batch if available
        bert_scores = None
        if BERT_SCORE_AVAILABLE:
            bert_scores = self.calculate_bert_score(references, hypotheses)

        for i, item in enumerate(tqdm(data, desc="Evaluating generations")):
            reference = item["reference"]
            hypothesis = item["hypothesis"]

            metrics = {}

            # ROUGE scores
            rouge_scores = self.calculate_rouge(reference, hypothesis)
            metrics.update(rouge_scores)

            # BLEU score
            metrics["bleu"] = self.calculate_bleu(reference, hypothesis)

            # BERTScore
            if bert_scores:
                metrics["bert_precision"] = bert_scores["precision"][i]
                metrics["bert_recall"] = bert_scores["recall"][i]
                metrics["bert_f1"] = bert_scores["f1"][i]

            metrics["reference"] = reference
            metrics["hypothesis"] = hypothesis

            results.append(metrics)

        # Create DataFrame
        self.results_df = pd.DataFrame(results)

        # Add average metrics row
        avg_metrics = {
            col: self.results_df[col].mean()
            for col in self.results_df.columns
            if col not in ["reference", "hypothesis"]
        }
        avg_metrics["reference"] = "AVERAGE"
        avg_metrics["hypothesis"] = "AVERAGE"

        self.results_df = pd.concat(
            [self.results_df, pd.DataFrame([avg_metrics])], ignore_index=True
        )

        return self.results_df


class RAGEvaluator:
    """Class to evaluate the entire RAG pipeline, including retrieval and generation."""

    def __init__(self):
        """Initialize the RAGEvaluator class."""
        self.retrieval_metrics = RetrievalMetrics()
        self.generation_metrics = GenerationMetrics()
        self.combined_results = None

    def evaluate_retrieval(self, rag_instance, test_data, k_values=[1, 3, 5, 10]):
        """
        Evaluate retrieval performance of a RAG pipeline.

        Args:
            rag_instance: An instance of the RAG class
            test_data: List of dictionaries containing:
                - 'query': The query text
                - 'relevant_docs': List of relevant document IDs or content
            k_values: List of k values for calculating metrics@k

        Returns:
            DataFrame with retrieval metrics
        """
        processed_queries = []

        for item in tqdm(test_data, desc="Processing retrieval queries"):
            query = item["query"]
            relevant_docs = item["relevant_docs"]

            # Use the RAG instance to retrieve documents
            if hasattr(rag_instance, "db") and rag_instance.db is not None:
                retrieved_docs = rag_instance.db.similarity_search(
                    query, k=max(k_values)
                )
                retrieved_doc_ids = [
                    doc.metadata.get("source", "") for doc in retrieved_docs
                ]
            else:
                raise ValueError(
                    "RAG instance doesn't have a document database or it's not initialized"
                )

            processed_queries.append(
                {
                    "query": query,
                    "relevant_docs": relevant_docs,
                    "retrieved_docs": retrieved_doc_ids,
                }
            )

        return self.retrieval_metrics.evaluate(processed_queries, k_values)

    def evaluate_generation(self, rag_instance, chatbot_instance, test_data, k=3):
        """
        Evaluate generation quality of a RAG pipeline.

        Args:
            rag_instance: An instance of the RAG class
            chatbot_instance: An instance of a chatbot class
            test_data: List of dictionaries containing:
                - 'query': The query text
                - 'reference_answer': The ground truth answer
            k: Number of documents to retrieve for context

        Returns:
            DataFrame with generation metrics
        """
        generation_data = []

        for item in tqdm(test_data, desc="Generating answers"):
            query = item["query"]
            reference_answer = item.get("reference_answer", "")

            # Get context using RAG
            if hasattr(rag_instance, "_search_context"):
                context = rag_instance._search_context(query, k=k)
            else:
                context = ""

            # Generate answer using chatbot
            generated_answer = chatbot_instance(context, query)

            generation_data.append(
                {"reference": reference_answer, "hypothesis": generated_answer}
            )

        return self.generation_metrics.evaluate(generation_data)

    def evaluate(
        self,
        rag_instance,
        chatbot_instance,
        test_data,
        retrieval_k=[1, 3, 5, 10],
        generation_k=3,
    ):
        """
        Evaluate the complete RAG pipeline (retrieval + generation).

        Args:
            rag_instance: An instance of the RAG class
            chatbot_instance: An instance of a chatbot class
            test_data: List of dictionaries containing:
                - 'query': The query text
                - 'relevant_docs': List of relevant document IDs
                - 'reference_answer': The ground truth answer
            retrieval_k: List of k values for retrieval metrics
            generation_k: Number of documents to retrieve for context in generation

        Returns:
            Dictionary with retrieval and generation results DataFrames
        """
        # Evaluate retrieval
        retrieval_results = self.evaluate_retrieval(
            rag_instance, test_data, retrieval_k
        )

        # Evaluate generation
        generation_results = self.evaluate_generation(
            rag_instance, chatbot_instance, test_data, generation_k
        )

        # Store combined results
        self.combined_results = {
            "retrieval": retrieval_results,
            "generation": generation_results,
        }

        return self.combined_results

    def get_summary_df(self) -> pd.DataFrame:
        """
        Create a summary DataFrame with all metrics.

        Returns:
            DataFrame with all metrics combined
        """
        if self.combined_results is None:
            return pd.DataFrame()

        # Get retrieval metrics (excluding 'query' column)
        retrieval_metrics = (
            self.combined_results["retrieval"].iloc[-1].drop("query").to_dict()
        )

        # Get generation metrics (excluding 'reference' and 'hypothesis' columns)
        generation_metrics = (
            self.combined_results["generation"]
            .iloc[-1]
            .drop(["reference", "hypothesis"], errors="ignore")
            .to_dict()
        )

        # Combine with prefixes to avoid name collisions
        all_metrics = {}
        all_metrics.update({f"retrieval_{k}": v for k, v in retrieval_metrics.items()})
        all_metrics.update(
            {f"generation_{k}": v for k, v in generation_metrics.items()}
        )

        return pd.DataFrame([all_metrics])


if __name__ == "__main__":
    # Example usage
    from RAG import RAG, BasePreprocessing
    from chat import OllamaChatbot

    # Create a simple test case
    test_data = [
        {
            "query": "What is RAG?",
            "relevant_docs": ["chunk_0", "chunk_5", "chunk_10"],
            "reference_answer": "RAG (Retrieval Augmented Generation) is a technique that combines information retrieval with text generation.",
        }
    ]

    # Initialize RAG and chatbot
    rag = RAG(path="path/to/docs", debug=True)
    rag()  # Initialize the database

    chatbot = OllamaChatbot(name="llama3")

    # Evaluate
    evaluator = RAGEvaluator()
    results = evaluator.evaluate(rag, chatbot, test_data)

    # Print summary
    print(evaluator.get_summary_df())
