import re
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

from utils.audio_processor import process_input
from core.Transcriber import transcribe_all
from core.Summarizer import summarize, generate_title
from core.Extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.Rag_Engine import build_rag_chain, ask_question


load_dotenv()


def get_youtube_video_id(url: str) -> str:
    """Extract the 11-character video ID from common YouTube URLs."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]

    if host == "youtu.be" or host.endswith(".youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]

    elif host == "youtube.com" or host.endswith(".youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            match = re.match(
                r"^/(?:shorts|embed|live)/([^/?]+)",
                parsed.path,
            )
            video_id = match.group(1) if match else ""

    else:
        raise ValueError("Please provide a valid YouTube URL.")

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Could not extract a valid YouTube video ID.")

    return video_id


def get_youtube_transcript(url: str, language: str) -> str:
    """Fetch accessible YouTube captions."""
    video_id = get_youtube_video_id(url)

    languages = (
        ["hi", "en"]
        if language == "hinglish"
        else ["en", "hi"]
    )

    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=languages)

    transcript = " ".join(
        snippet.text for snippet in fetched
    ).strip()

    if not transcript:
        raise ValueError("The video transcript is empty.")

    return transcript


def run_pipeline(source: str, language: str = "english") -> dict:
    print("Starting AI Video Assistant")

    transcript = None

    if source.startswith(("http://", "https://")):
        print("Trying YouTube transcript first...")

        try:
            transcript = get_youtube_transcript(source, language)
            print("YouTube transcript fetched successfully.")

        except Exception as exc:
            print(f"Transcript unavailable: {exc}")
            print("Trying the existing audio-processing workflow...")

    if transcript is None:
        chunks = process_input(source)
        transcript = transcribe_all(chunks, language)

    print(f"Raw transcription (first 300 characters): {transcript[:300]}")

    title = generate_title(transcript)
    summary = summarize(transcript)
    action_item = extract_action_items(transcript)
    decisions = extract_key_decisions(transcript)
    questions = extract_questions(transcript)
    rag_chain = build_rag_chain(transcript)

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_item,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


if __name__ == "__main__":
    source = input("Enter YouTube URL or local file path: ").strip()
    language = input("Language (english/hinglish): ").strip().lower() or "english"

    result = run_pipeline(source, language)

    print("\n" + "=" * 60)
    print(f"Title: {result['title']}")
    print(f"\nSummary:\n{result['summary']}")
    print(f"\nAction Items:\n{result['action_items']}")
    print(f"\nKey Decisions:\n{result['key_decisions']}")
    print(f"\nOpen Questions:\n{result['open_questions']}")
    print("=" * 60)

    print("\nChat with your video (type 'exit' to quit)\n")
    rag_chain = result["rag_chain"]

    while True:
        question = input("You: ").strip()

        if question.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        if not question:
            continue

        answer = ask_question(rag_chain, question)
        print(f"\nAssistant: {answer}\n")
