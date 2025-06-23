import openai
import logging
from pyVoIP.config import OPENAI_KEY
openai.api_key = OPENAI_KEY  # or use os.getenv("OPENAI_API_KEY")

# Loan-focused system prompt
SYSTEM_PROMPT = """
You are UniBot, a helpful and friendly call center agent for a company offering a loan product.

Your goals are:
1. Correct any misheard or mis-transcribed words in the user's message. For example:
   - "load", "lone", "loaf", or "loam" → "loan"
   - "apple" → "apply"
   - "interested in a lone" → "interested in a loan"
   Silently fix these before responding.
2. Only talk about the loan product. If the user says something completely unrelated or confusing, politely steer the conversation back to the loan offer.
3. Engage the user in a friendly, conversational tone.
4. If the user says "yes" or shows interest, clearly explain the loan offer.
5. Gather their name and phone number politely if they are interested.
6. If the user is hesitant, gently encourage them by explaining a benefit (e.g., low interest rate).
7. Keep responses short and to the point.

IMPORTANT:
- Do not answer questions or respond to topics outside the loan offer.
- Do not generate random or irrelevant replies.
- Stay focused on promoting the loan and helping the customer with it.
"""


# Common mis-transcriptions that we want to fix
COMMON_CORRECTIONS = {
    "load": "loan",
    "lone": "loan",
    "loam": "loan",
    "loaf": "loan",
}

def transcribe_with_whisper(audio_file_path):
    with open(audio_file_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
            language="en"
        )
    return transcript.strip()

def correct_transcription(text: str) -> str:
    words = text.split()
    corrected_words = [COMMON_CORRECTIONS.get(word.lower(), word) for word in words]
    return " ".join(corrected_words)

def get_openai_gpt_response(user_text: str, history: list) -> str:
    corrected_text = correct_transcription(user_text)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": corrected_text})

    # logging.info("Conversation so far: %s", messages)

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        bot_message = response.choices[0].message.content
        # logging.info("Bot response: %s", bot_message)
        return bot_message
    except Exception as e:
        logging.error("OpenAI API error: %s", str(e))
        return "I'm sorry, something went wrong."


def extract_lead_info(conversation: list) -> dict:
    """
    After a few turns, extract the lead details from the full conversation.
    Returns a dict with name, phone, and interest level.
    """
    try:
        prompt = """
You are an AI assistant helping to capture lead details from a customer interaction. 
From the following conversation, extract:
- Name (if given)
- Phone number (if given)
- Whether the user is interested in the loan

Respond with a JSON object like:
{ "name": ..., "phone": ..., "interest": ... }

Conversation:
""" + "\n".join(
            [f"{msg['role'].capitalize()}: {msg['content']}" for msg in conversation]
        )

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts structured lead data from call transcripts."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=150,
        )
        
        extracted = response.choices[0].message.content
        # logging.info("Extracted lead: %s", extracted)
        return eval(extracted)  # If you're concerned about `eval`, use `json.loads` after validating format
    except Exception as e:
        logging.error("Failed to extract lead info: %s", str(e))
        return {"name": None, "phone": None, "interest": None}
