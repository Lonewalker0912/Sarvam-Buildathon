"""Generational Kitchen Wealth pipeline: grandparent's voice -> recipe card -> spoken back in their voice.

Stages (each one Sarvam call, or a few for long audio):
  transcribe  Saaras STT, auto-detects the spoken language
  structure   sarvam-105b turns the rambling transcript into a recipe card (JSON)
  translate   Sarvam Translate puts the narration in the grandchild's language
  speak       voice cloning in the grandparent's voice, Bulbul TTS as fallback

Results are cached in cache/ so replaying a clip during rehearsal costs no credits.
"""

import base64
import hashlib
import io
import json
import os
import re
import wave
from pathlib import Path

import numpy as np
from sarvamai import SarvamAI

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "cache"

# Saaras REST only accepts clips under 30s. The first chunk doubles as the
# voice-cloning reference, so keep it short; the rest can be longer.
FIRST_CHUNK_SEC = 15
CHUNK_SEC = 25

LANGUAGES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Kannada": "kn-IN",
    "Malayalam": "ml-IN",
    "Bengali": "bn-IN",
    "Marathi": "mr-IN",
    "Gujarati": "gu-IN",
    "Punjabi": "pa-IN",
    "Odia": "od-IN",
}
LANGUAGE_NAMES = {code: name for name, code in LANGUAGES.items()}

# Fallback Bulbul voices (used only if voice cloning fails)
FALLBACK_SPEAKER = "anushka"


def _load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_client() -> SarvamAI:
    _load_env()
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not set. Add it to .env first.")
    return SarvamAI(api_subscription_key=api_key)


# ---------- audio helpers ----------

def to_mono_int16(samples: np.ndarray) -> np.ndarray:
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if np.issubdtype(samples.dtype, np.floating):
        samples = np.clip(samples, -1.0, 1.0) * 32767
    return samples.astype(np.int16)


def wav_bytes(samples: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


def chunk_audio(samples: np.ndarray, sr: int) -> list[bytes]:
    first = FIRST_CHUNK_SEC * sr
    chunks = [samples[:first]]
    step = CHUNK_SEC * sr
    for start in range(first, len(samples), step):
        chunks.append(samples[start:start + step])
    # Drop a trailing sliver under half a second; it is usually silence
    chunks = [c for c in chunks if len(c) >= sr // 2]
    return [wav_bytes(c, sr) for c in chunks]


# ---------- stages ----------

def transcribe(client: SarvamAI, chunks: list[bytes]) -> dict:
    """Transcribe every chunk; language is auto-detected (no extra call)."""
    texts, langs = [], []
    for i, chunk in enumerate(chunks):
        res = client.speech_to_text.transcribe(
            file=(f"chunk{i}.wav", chunk, "audio/wav"),
            model="saaras:v3",
            mode="transcribe",
            language_code="unknown",
        )
        texts.append(res.transcript.strip())
        if res.language_code:
            langs.append((res.language_code, res.language_probability or 0.0))

    # Pick the language detected with the highest total confidence
    scores: dict[str, float] = {}
    for code, prob in langs:
        scores[code] = scores.get(code, 0.0) + prob
    language = max(scores, key=scores.get) if scores else "unknown"
    confidence = scores.get(language, 0.0) / max(1, sum(1 for c, _ in langs if c == language))

    return {
        "transcript": " ".join(t for t in texts if t),
        "first_chunk_text": texts[0] if texts else "",
        "language": language,
        "language_confidence": round(confidence, 2),
    }


STRUCTURE_PROMPT = """You are helping a family preserve a grandparent's recipe.
Below is a transcript of the grandparent speaking naturally, in {language}. It may ramble,
mix languages, tell stories, and use vague quantities ("konjam", "andaaz se", "a fistful").

Return ONLY a JSON object with these keys:
- "title": dish name (English, with the original name in brackets if there is one)
- "serves": best guess, e.g. "4 people", or "" if unknown
- "ingredients": list of {{"item": str, "quantity": str}}. Convert vague quantities to a
  sensible estimate and keep the original phrase in brackets, e.g. "1 tsp (konjam)".
- "steps": list of short, clear instruction strings in order
- "tips": list of special tricks or warnings the grandparent mentioned
- "story": 1-3 sentences about any memory or story they shared, or "" if none
- "narration": a warm spoken version of the recipe for a grandchild, written in English in
  the grandparent's own first-person voice ("Kanna, first take..."). Include ingredients and
  steps. Plain sentences only, no lists or symbols. At most 1200 characters.

Do not invent ingredients or steps that are not in the transcript.

Transcript:
{transcript}"""


def _parse_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError(f"Model did not return JSON:\n{text[:500]}")
    return json.loads(match.group(0))


def structure(client: SarvamAI, transcript: str, language: str) -> dict:
    res = client.chat.completions(
        model="sarvam-105b",
        messages=[{
            "role": "user",
            "content": STRUCTURE_PROMPT.format(
                language=LANGUAGE_NAMES.get(language, "an Indian language"),
                transcript=transcript,
            ),
        }],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return _parse_json(res.choices[0].message.content)


def translate(client: SarvamAI, text: str, target: str) -> str:
    if target == "en-IN":
        return text
    res = client.text.translate(
        input=text[:2000],
        source_language_code="en-IN",
        target_language_code=target,
        model="sarvam-translate:v1",
        mode="modern-colloquial",
    )
    return res.translated_text


def speak(client: SarvamAI, text: str, target: str, ref_wav: bytes, ref_text: str) -> tuple[bytes, str]:
    """Return (wav bytes, which voice was used). Tries the cloned voice first."""
    try:
        res = client.voice_cloning.convert(
            text=text,
            language_code=target,
            ref_audio=("reference.wav", ref_wav, "audio/wav"),
            ref_text=ref_text[:500] or None,
            output_audio_codec="wav",
        )
        return base64.b64decode(res.audio_b64), "cloned"
    except Exception as e:  # beta API or not enabled on this account
        print(f"[speak] voice cloning failed, falling back to Bulbul: {e}")

    res = client.text_to_speech.convert(
        text=text[:2500],
        language_code=target,
        speaker=FALLBACK_SPEAKER,
        model="bulbul:v3",
        output_audio_codec="wav",
    )
    return base64.b64decode("".join(res.audios)), "bulbul"


# ---------- full run ----------

def run(samples: np.ndarray, sr: int, target: str, log=print) -> dict:
    samples = to_mono_int16(samples)
    key = hashlib.sha256(samples.tobytes() + target.encode()).hexdigest()[:16]
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        log("Loaded from cache (no credits used)")
        return json.loads(cached.read_text())

    client = get_client()
    chunks = chunk_audio(samples, sr)
    if not chunks:
        raise ValueError("Recording is too short.")

    log(f"Transcribing {len(chunks)} chunk(s)...")
    heard = transcribe(client, chunks)
    log(f"Detected {LANGUAGE_NAMES.get(heard['language'], heard['language'])} "
        f"({heard['language_confidence']:.0%})")

    log("Writing recipe card...")
    card = structure(client, heard["transcript"], heard["language"])

    log(f"Translating to {LANGUAGE_NAMES[target]}...")
    narration = translate(client, card.get("narration", ""), target)

    log("Speaking it back...")
    audio, voice = speak(client, narration, target, chunks[0], heard["first_chunk_text"])

    CACHE_DIR.mkdir(exist_ok=True)
    audio_path = CACHE_DIR / f"{key}.wav"
    audio_path.write_bytes(audio)
    result = {**heard, "card": card, "narration_translated": narration,
              "target": target, "voice": voice, "audio_path": str(audio_path)}
    cached.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    # CLI test: python pipeline.py recording.wav [Hindi]
    import sys

    path = sys.argv[1]
    target = LANGUAGES[sys.argv[2]] if len(sys.argv) > 2 else "en-IN"
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        if w.getsampwidth() != 2:
            raise SystemExit("Please use a 16-bit WAV file.")
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        if w.getnchannels() > 1:
            data = data.reshape(-1, w.getnchannels())
    out = run(data, sr, target)
    print(json.dumps({k: v for k, v in out.items() if k != "transcript"}, ensure_ascii=False, indent=2))
