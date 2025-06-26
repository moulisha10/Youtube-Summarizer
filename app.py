import os
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
load_dotenv()


app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def fetch_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([entry["text"] for entry in transcript])
        return full_text
    except Exception as e:
        print(f"❌ Error fetching transcript: {e}")
        return None


def summarize_transcript_with_gemini(transcript):
    client = genai.Client(api_key=GEMINI_API_KEY)
    model = "gemini-2.0-flash"

    prompt = f"""Based on the following YouTube transcript, return a brief summary in the following JSON format only:
{{
  "topic_name": "name of the topic",
  "topic_summary": "summary of the topic"
}}

Transcript:
{transcript}
"""

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    config = types.GenerateContentConfig(response_mime_type="text/plain")

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    return response.text


def extract_youtube_id(url):
    if "youtube.com/watch?v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("/")[-1]
    else:
        raise ValueError("Invalid YouTube URL")


@app.get("/summarize")
def get_summary(url: str = Query(..., description="YouTube video URL")):
    try:
        video_id = extract_youtube_id(url)
        transcript = fetch_youtube_transcript(video_id)

        if transcript:
            summary_text = summarize_transcript_with_gemini(transcript)
            try:
                # Try extracting JSON block from Gemini output
                start = summary_text.find('{')
                end = summary_text.rfind('}') + 1
                json_output = summary_text[start:end]
                return JSONResponse(content=eval(json_output))  # or use json.loads() if valid
            except:
                return {"raw_output": summary_text}
        else:
            return {"error": "Transcript not found."}
    except Exception as e:
        return {"error": str(e)}
