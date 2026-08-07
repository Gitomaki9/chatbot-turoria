import os
import ollama
import re
from huggingface_hub import InferenceClient


class BaseChatbot:
    def __init__(self, name: str, *args, **kwargs):
        self.system_prompt_with_context = """
                    Cuando se te proporciona un contexto, asumes el rol de un asistente virtual especializado. En este caso:

                    Da prioridad al uso del contexto para generar respuestas precisas, relevantes, fundamentadas y amigables.

                    Si la pregunta no está directamente cubierta por la información del contexto, puedes complementarla con tu conocimiento general.

                    Si el contexto está presente pero no contiene información útil para responder la pregunta, responde con la frase:
                    "El contexto proporcionado no contiene información relevante sobre esa pregunta."

                    Importante: Responde siempre en el mismo idioma en que se formule la pregunta.

        """

        self.system_prompt_without_context = """
                    Actúas como un chatbot general. Utiliza tu conocimiento preentrenado para responder las preguntas de forma muy amigable, clara, 
                    concisa y formal.

                    Importante: Responde siempre en el mismo idioma en que se formule la pregunta.
                    """
        self.name = name

    def __call__(self, context: str, question: str) -> str:
        response = self._generate_answer(context, question)
        response = self._posprocessing_answer(response)
        return response

    def _generate_answer(self, context: str, question: str) -> str:
        pass

    def _generate_prompt_with_context(self, context: str, question: str) -> str:
        prompt = f"""{self.system_prompt_with_context}
                    Contexto:
                    {context}

                    Pregunta:
                    {question}

                    Respuesta:
                    """
        return prompt

    def _generate_prompt_without_countext(self, question: str) -> str:
        prompt = f"""{self.system_prompt_without_context}

                    Pregunta:
                    {question}

                    Respuesta:
                    """

        return prompt

    def _posprocessing_answer(self, response, return_thinking=False):
        match = re.search(r"<think>(.*?)</think>\s*(.*)", response, flags=re.DOTALL)

        if match:
            thinking = match.group(1).strip()
            response = match.group(2).strip()
        else:
            thinking = None
            response = response
        if return_thinking:
            return response, thinking
        else:
            return response


class OllamaChatbot(BaseChatbot):
    def __init__(self, name: str, *args, **kwargs):
        bots_names = [model.model for model in ollama.list()["models"]]
        if name not in bots_names:
            raise ValueError(
                f"The model '{name}' is not available. Available models in Ollama are: {', '.join(bots_names)}"
            )
        super().__init__(name, *args, **kwargs)

    def _generate_answer(self, context: str, question: str) -> str:
        if context:
            prompt = self._generate_prompt_with_context(context, question)
        else:
            prompt = self._generate_prompt_without_countext(question)

        response = ollama.chat(
            model=self.name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        return response["message"]["content"]


class HuggingFaceChatbot(BaseChatbot):
    def __init__(
        self,
        name: str = "deepseek-ai/DeepSeek-V3-0324",
        token: str = None,
        provider: str = "hyperbolic",
        *args,
        **kwargs,
    ):
        name = kwargs.get(
            "model_name",
        )
        self.token = token
        self.provider = provider
        self.client = InferenceClient(
            api_key=token,
            model="deepseek-ai/DeepSeek-V3-0324",
            provider="hyperbolic",
        )

        if self.token is None:
            raise ValueError(
                "You must provide a token for Hugging Face models. Use the 'token' argument."
            )
        super().__init__(name, *args, **kwargs)

    def _generate_answer(self, context: str, question: str) -> str:
        if context:
            prompt = self._generate_prompt_with_context(context, question)
        else:
            prompt = self._generate_prompt_without_countext(question)

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"]
