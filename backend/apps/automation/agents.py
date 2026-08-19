"""
LangChain-based agents for automation features.

generate_caption()   — LangChain agent with DuckDuckGo web search →
                       produces trending, human-like FB post captions.
moderate_comment()   — LangChain chain → classifies comment as
                       spam / abusive / valid and drafts a reply.
"""

import json
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Caption generation with web search ───────────────────────────────────────

def generate_caption(niche: str, media_type: str, custom_prompt: str = "") -> str:
    """
    Use a LangChain ReAct agent (Groq LLM + DuckDuckGo search) to:
    1. Search for current trending news/topics related to `niche`
    2. Generate a human-like, engaging Facebook post caption

    Falls back to a simple LLM-only caption if LangChain/search fails.
    """
    try:
        from langchain_groq import ChatGroq
        from langchain_community.tools import DuckDuckGoSearchRun
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.85,
            max_tokens=600,
        )

        tools = [DuckDuckGoSearchRun(name="web_search", max_results=3)]

        system_msg = custom_prompt or (
            "You are a creative social media manager for a Facebook page. "
            "Your job is to write engaging, human-like post captions that drive likes and comments. "
            "ALWAYS start by using the web_search tool to find what is trending right now related to the topic. "
            "Then write a caption that: (1) naturally weaves in the trending angle, "
            "(2) includes 2-3 relevant emojis, (3) ends with a question to spark engagement, "
            "(4) sounds personal and authentic — NOT like a robot. "
            "Return ONLY the final caption text. No preamble, no explanation."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=4,
            handle_parsing_errors=True,
        )

        niche_clean = niche.strip() or "general lifestyle"
        result = executor.invoke({
            "input": (
                f"Topic / niche: {niche_clean}. "
                f"This post will include a {media_type}. "
                "Search for what is trending on this topic today, then write the caption."
            )
        })

        caption = result.get("output", "").strip()
        if caption:
            logger.info("Caption generated for niche=%s (len=%d)", niche_clean, len(caption))
            return caption

    except Exception as exc:
        logger.warning("LangChain agent failed, falling back to plain LLM: %s", exc)

    # ── Fallback: plain Groq call without web search ──────────────────────────
    return _caption_fallback(niche, media_type, custom_prompt)


def _caption_fallback(niche: str, media_type: str, custom_prompt: str = "") -> str:
    """Simple Groq call when the agent/search fails."""
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        system = custom_prompt or (
            "You are a creative social media manager. "
            "Write engaging Facebook captions with emojis that end with a question."
        )
        resp = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Write a Facebook post caption for a {media_type} about: {niche}. "
                        "Make it human, include 2-3 emojis, end with an engaging question. "
                        "Return ONLY the caption."
                    ),
                },
            ],
            max_tokens=300,
            temperature=0.85,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Caption fallback also failed: %s", exc)
        return f"🌟 Check out this amazing {media_type}! What do you think? 👇"


# ── Comment moderation ────────────────────────────────────────────────────────

def moderate_comment(comment_text: str, niche: str = "", extra_rules: str = "") -> dict:
    """
    Classify a Facebook comment and optionally draft a reply.

    Returns:
        {
            "verdict": "spam" | "abusive" | "valid",
            "reply": "reply text or empty string",
            "reason": "brief explanation"
        }
    """
    try:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import JsonOutputParser

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.1,
            max_tokens=400,
        )

        rules = extra_rules or "Standard community guidelines apply."
        niche_ctx = f"The page is about: {niche}. " if niche else ""

        system = f"""You are a strict but fair Facebook page comment moderator.
{niche_ctx}Page rules: {rules}

Classify the comment into one of three categories:
- "spam": promotional content, unrelated links, fake giveaways, follow-for-follow
- "abusive": hate speech, harassment, profanity, personal attacks
- "valid": genuine question, opinion, compliment, or on-topic discussion

Respond ONLY with valid JSON in this exact format:
{{"verdict": "<spam|abusive|valid>", "reason": "<one sentence>", "reply": "<friendly reply if valid, else empty string>"}}

If valid, write a warm, human-like reply (1-2 sentences) as the page owner."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", "Comment to moderate: {comment}"),
        ])

        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({"comment": comment_text})

        # Validate shape
        verdict = result.get("verdict", "valid")
        if verdict not in ("spam", "abusive", "valid"):
            verdict = "valid"

        return {
            "verdict": verdict,
            "reason": result.get("reason", ""),
            "reply": result.get("reply", "") if verdict == "valid" else "",
        }

    except Exception as exc:
        logger.exception("Comment moderation failed: %s", exc)
        # Safe default: don't delete, don't reply
        return {"verdict": "valid", "reason": "moderation error", "reply": ""}
