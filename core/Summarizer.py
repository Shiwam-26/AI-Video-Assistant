
import os

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda


def get_llm():
    api_key = os.getenv("MISTRAL_API_KEY")

    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY is missing. Check your .env file."
        )

    return ChatMistralAI(
        model="codestral-2508",
        mistral_api_key=api_key,
        temperature=0.3
    )


def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200
    )

    return splitter.split_text(transcript)


def summarize(transcript: str) -> str:
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty. Cannot summarize.")

    print("Generating transcript summary...")

    llm = get_llm()

    # Step 1: Create map prompt
    map_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Summarize this portion of a meeting transcript concisely."
        ),
        ("human", "{text}")
    ])

    # IMPORTANT: StrOutputParser() must be instantiated
    map_chain = map_prompt | llm | StrOutputParser()

    # Step 2: Split transcript into chunks
    chunks = split_transcript(transcript)

    print(f"Transcript split into {len(chunks)} chunks.")

    # Step 3: Summarize each individual chunk
    chunk_summaries = []

    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i + 1}/{len(chunks)}...")

        summary = map_chain.invoke({"text": chunk})
        chunk_summaries.append(summary)

    combined = "\n\n".join(chunk_summaries)

    # Step 4: Combine partial summaries
    combined_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert meeting summarizer. Combine these partial "
            "summaries into one final professional meeting summary in "
            "clear bullet points. Preserve the important details."
        ),
        ("human", "{text}")
    ])

    combined_chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"text": x})
        | combined_prompt
        | llm
        | StrOutputParser()
    )

    print("Combining partial summaries...")

    final_summary = combined_chain.invoke(combined)

    print("Summary generated successfully.")

    return final_summary


def generate_title(transcript: str) -> str:
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty. Cannot generate a title.")

    llm = get_llm()

    title_chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"text": x})
        | ChatPromptTemplate.from_messages([
            (
                "system",
                "Based on the meeting transcript, generate a short "
                "professional title (maximum 8 words). "
                "Only return the title, nothing else."
            ),
            ("human", "{text}")
        ])
        | llm
        | StrOutputParser()
    )