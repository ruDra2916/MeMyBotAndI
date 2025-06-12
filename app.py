from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr

load_dotenv(override=True)

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
         {"type": "function", "function": record_unknown_question_json}]

class Me:
    def __init__(self):
        self.openai = OpenAI()
        self.name = "Dhanush Rudra"
        reader = PdfReader("me/Dhanush_Rudra_Resume.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
        return results

    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool."

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt

    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content

if __name__ == "__main__":
    me = Me()
    with gr.Blocks(css="""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

body {
    background-color: #0f172a;
    font-family: 'Inter', sans-serif;
    color: #f8fafc;
    margin: 0;
    padding: 0;
}

#main-layout {
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: flex-start;
    gap: 2rem;
    margin: 3rem auto;
    flex-wrap: wrap;
    width: 90%;
}

#branding {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-radius: 1.5rem;
    padding: 2rem;
    width: 25%;
    min-width: 250px;
    max-width: 300px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    text-align: center;
}

#branding h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #facc15;
    margin-bottom: 0.75rem;
}

#branding p {
    font-size: 0.95rem;
    color: #cbd5e1;
}

#chatbox {
    background-color: #1e293b;
    border-radius: 1rem;
    padding: 1.5rem;
    width: 75%;
    max-width: 850px;
    min-width: 300px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}
""") as demo:

        with gr.Row(elem_id="main-layout"):
            with gr.Column(elem_id="branding"):
                gr.Markdown("""
                <h1>🤖 MeMyBotAndI</h1>
                <p>Personal AI assistant trained on Dhanush Rudra's career and experience.  
                Ask about projects, skills, achievements, and more.</p>
                """)

            with gr.Column(elem_id="chatbox"):
                gr.ChatInterface(me.chat, type="messages")

    demo.launch()
