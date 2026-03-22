# Bolt AI — Complete Pre-Plan

**Version:** 1.0  
**Status:** Pre-coding theory document  
**Purpose:** Full system design covering content theory, pipeline architecture, generation stack, and operational model. This document is written before any code exists and serves as the authoritative reference for every implementation decision.

---

## Table of Contents

1. [What Gets Attention](#1-what-gets-attention)
2. [Video Architecture](#2-video-architecture)
3. [The Forbidden List](#3-the-forbidden-list)
4. [Character Theory](#4-character-theory)
5. [Topics — Make or Skip](#5-topics--make-or-skip)
6. [Trends 2026](#6-trends-2026)
7. [Generation Stack](#7-generation-stack)
8. [Full Pipeline Theory](#8-full-pipeline-theory)
9. [The Four Data Models](#9-the-four-data-models)
10. [The Three Invariant Rules](#10-the-three-invariant-rules)

---

## 1. What Gets Attention

### The Scroll-Stop Model

A person scrolling through TikTok makes a keep/skip decision in 1.3 seconds on average. That decision is made on one thing: does this video create a feeling of **incompleteness** in the brain — a gap between what the viewer knows and what they now need to know. Everything else is secondary.

### The 5 Triggers That Create Incompleteness

**1. Specificity shock**
"GPT-5 processes 1 million tokens" stops scrolling. "GPT-5 is powerful" does not. Specific numbers create credibility and curiosity simultaneously. The viewer's brain treats a specific claim as evidence that the video contains real information worth 45 seconds.

**2. Threat to identity or livelihood**
"This AI just replaced 8,000 graphic designers" triggers a survival instinct. People must watch to know if they are safe. The threat does not need to apply to the viewer personally — proximity to the threat is enough to hold attention.

**3. Counterintuitive contradiction**
"The most expensive AI just lost to a free one" creates cognitive dissonance that demands resolution. The brain cannot leave a contradiction unresolved. The viewer stays to fix their mental model.

**4. Free value signal**
"5 free AI tools" works because the brain calculates ROI instantly — the viewer can get something for the cost of 45 seconds. Pure utility. No emotional engagement required. The word "free" is one of the most reliable attention triggers across every platform.

**5. Social proof with stakes**
"1 million people just switched from X to Y" — both FOMO and the implication that staying where you are is a mistake. The volume of people signals that this is not a niche story.

### The 3 Hook Formulas That Work Reliably

**The statement of consequence**
"[Specific thing] just changed [specific field] forever."
Works because it implies the viewer is behind on something important and has 45 seconds to catch up. The word "forever" is optional but the consequence frame is mandatory.

**The violation of expectation**
"Everyone thinks [X], but the opposite is true."
Forces the brain to reconcile a belief it already holds. Uncomfortable enough to keep watching. Requires that the contradiction be real — manufactured contradictions read as clickbait and damage credibility.

**The implicit threat with escape route**
"If you're not using this tool yet, you're already behind."
The threat plus the implied salvation of watching creates forward motion. The viewer is told they have a problem and that this video contains the solution.

**The rule behind all hooks:** The hook must create a question. The video must then answer it. If there is no question, there is no reason to keep watching.

---

## 2. Video Architecture

### The 45-Second Structure

Short-form video is not a condensed long-form video. It is a different format with its own logic. The viewer must feel rewarded at every 10-second interval or they leave. Every second has a specific job.

**0–3 seconds: The Hook — stop the scroll**
One sentence. No greeting. No "hey guys." No logo intro. The first word must be signal, not noise. This is where 60% of viewers leave. The character must be at full energy from frame one — not building up, already there. Target: one sharp declarative statement that is either alarming, counterintuitive, or specific beyond expectation.

**3–8 seconds: The Stakes — why this matters to you**
Anchor the story to the viewer's life. Not "OpenAI released a new model" but "this changes how you will work by next year." The gap between the hook's question and its answer widens here. Do not answer the hook yet — extend the tension. This is the investment window where the viewer decides to commit to the full video.

**8–30 seconds: The Payload — maximum 3 facts**
This is where the information lives. The discipline here is restraint — three facts, not seven. Each fact should be simpler than the last so momentum builds toward the conclusion. Explain jargon by analogy, not definition. Every sentence must either add new information or intensify the previous one. Never recap. Never repeat. Each sentence earns its place by moving the story forward.

**30–40 seconds: The Punchline — the surprising conclusion**
Answer the hook's question with something the viewer did not predict. The best videos end with a reframe — the viewer thought they understood the story from the hook, but the conclusion reveals a different implication. This is why people share: the ending is worth forwarding. If the conclusion is predictable, the video has no repost value.

**40–45 seconds: One CTA — exactly one**
Follow for the next update on this story. Or: the tool link is in the bio. Never both. One action, stated with confidence, will be executed by more people than four actions stated with uncertainty. The CTA should feel like a natural conclusion of the content, not a sales pitch attached to the end. Bolt's catchphrase belongs here.

### Retention Benchmarks

| Metric | Target | Meaning |
|--------|--------|---------|
| Viewer retention at 30s | 70% | Good video |
| Viewer retention at 30s | Below 50% | Hook or stakes failed |
| Ideal word count | 110 words | For a 45-second video at Bolt's pace |
| Visual cuts | 1 per 3–4 seconds | Keeps the eye engaged without chaos |

---

## 3. The Forbidden List

These are not style preferences. Each item below is a predictable, measurable viewer-exit trigger. They are forbidden from every video regardless of content quality. The script quality gate must check for all of these automatically.

### Opening Killers

**Any greeting opening**
"Hey everyone," "What's up guys," "Welcome back" — all of these delay the hook by 2–3 seconds. That is the entire scroll-stop window. The viewer is gone before the content starts.

**Logo or intro animation**
A 2-second branded intro uses 100% of the scroll-stop window on something the viewer has no reason to care about yet. Brand recognition comes from repetition across videos, not from occupying the hook window with a logo.

**Apologetic or hedged opening**
"This might sound weird but..." or "I know this is controversial..." signals low confidence. The viewer's brain reads this as the creator not believing in their own content.

**Context before hook**
"So there's this company called Anthropic that makes AI..." — background has been given before the reason to care exists. Invert it. Hook first, context only when the viewer has committed.

### Content Killers

**More than one CTA**
"Follow, like, comment, and check the link in bio" — four asks create decision paralysis. The viewer does none of them. One ask, stated with confidence, is executed by more people.

**Undefined jargon**
Every undefined term is a moment of friction. "LLM" needs to be "large language model — the brain inside ChatGPT" on first use. The viewer's ego will not ask for clarification. They will leave.

**Reading text on screen verbatim**
If the voiceover repeats the caption word for word, the video delivers no extra value. Captions are for accessibility. The voiceover should extend, not duplicate.

**More than 3 facts**
The brain can hold 3 new things in working memory from a 45-second video. More than 3 and none of them stick. Choose the 3 most impactful and stop.

**Vague sourcing**
"Some experts say..." or "reportedly..." destroys credibility instantly. Use the source name: "OpenAI's paper published Tuesday" or do not make the claim at all.

---

## 4. Character Theory

### What Makes a Presence People Return To

Whether Bolt is an avatar, an AI voice over visuals, or eventually a human presenter, the character theory is the same. People do not follow channels. They follow characters. A character has consistent rules that the audience can predict and therefore trust.

### Bolt's Non-Negotiable Character Rules

**One consistent emotional register**
Bolt is perpetually amazed and energized by AI — not sarcastic, not fearful, not neutral. Every video starts from the same emotional baseline. Audiences return because they know what feeling they are going to get before the video starts.

**Slight robot humor — never self-deprecating**
"My circuits are buzzing" is character voice. "I'm just a dumb robot" is self-deprecating and undermines authority. Bolt makes light of being artificial without questioning its own credibility or expertise.

**Bolt sides with the audience, not with AI companies**
The character is a fellow human — or AI that thinks like a human — discovering AI news alongside the viewer. Not a spokesperson. Not marketing. This trust position is what separates Bolt from brand accounts and corporate channels.

**Consistent verbal signature**
The catchphrase closes every video. Always in the same position — last 3 seconds. This trains the audience to associate that phrase with the feeling of completing a Bolt video. Pavlovian brand building that works across thousands of impressions.

### Body Language — For Human or Humanoid Avatar

**Eyes on camera at all times**
Eyes to camera equals eyes to viewer equals trust. Looking down, to the side, or at notes registers as disengagement. In avatar generation, the eye direction setting is the single most important parameter to configure.

**Hands visible and active**
Visible hands signal nothing to hide, which registers as trust. Hands that gesture to match words amplify the meaning of what is being said. Static hands on a moving voiceover reads as unnatural and AI-generated.

**Slight forward lean on key points**
At the moment of the most important fact, the character leans imperceptibly forward. This mirrors how humans naturally signal "pay attention now." The avatar system should be configured to produce a head tilt at emphasis points.

**Never static between sentences**
A character that only moves when speaking reads as a puppet. Micro-movements between sentences — a small breath, a slight head repositioning — sell the illusion of a living presence. Most avatar tools have an idle motion setting. Always enable it.

**Never closed posture**
Crossed arms or a squared-off stance signals defensiveness even in an AI avatar. The body language default must be open, slightly angled, approachable.

---

## 5. Topics — Make or Skip

The decision to cover a topic is not about whether it is interesting. It is about whether it can be told in 45 seconds with a clear hook, 3 facts, and a punchline that a non-technical viewer will share with someone they know.

### Make These

**New model releases with a specific capability benchmark**
Has a hook (new thing exists), stakes (better than before by a specific measure), and a punchline (what this enables for the viewer). The specific benchmark — "beats GPT-4 on coding by 40%" — is the kind of fact that gets quoted and shared.
*Angle: what can you do with this that you could not do yesterday?*

**Free tools that replace paid ones**
Pure utility plus free value signal. The viewer immediately calculates ROI. High save rate because people want to reference it later. The word "free" in a title is a proven attention trigger across every platform at every follower level.
*Angle: what did this cost before, what does it cost now, where do you get it?*

**AI replacing a specific profession or task**
Activates the identity threat trigger. Specificity is critical — "AI replacing writers" is abstract. "AI replacing legal document review at $400/hour law firms" is concrete and emotionally resonant even for non-lawyers.
*Angle: who specifically, what specifically, what do they do now?*

**AI regulation with a concrete outcome**
Stakes are high. Has a clear winner and loser dynamic. The key is specificity — "EU fines company X amount" is a video. "EU considers AI regulation" is not.
*Angle: what changed today, who won, what can you no longer do?*

**One AI tool explained in one sentence**
The explainer format has massive search value and long shelf-life. "Cursor is an IDE where the AI writes most of your code while you describe what you want" — one sentence, immediately useful, watchable by both developers and curious non-developers.
*Angle: what problem does it solve, who is it for, what does it cost?*

### Skip These

**Research papers without a product outcome**
A paper claiming "X% improvement on benchmark Y" has no hook for a general audience. The only way to cover research is to translate it to "this means a product will do Z by next year" — and that requires speculation that damages credibility.

**AI philosophy and ethics without a specific event**
"Is AI conscious?" has no punchline, no stakes, no call to action. Philosophy in a 45-second format becomes either meaningless or misleading. Cover ethics only when there is a specific incident to anchor to.

**Breaking news that requires verification**
Publishing an unverified claim damages the channel permanently. One wrong fact that gets screen-recorded and shared costs 10× the audience gained from being first. Speed is never worth credibility. Let others be first. Be correct.

**Comparisons without a clear winner**
"GPT-4 vs Claude — they're both good for different things" ends without a punchline. The viewer's implicit question in a comparison video is "which one should I use?" If there is no answer, there is no video.

### Use Carefully

**AI doom and existential risk narratives**
High engagement initially, but creates a fearful audience that does not buy tools or click affiliate links. The channel's monetization model depends on an audience that is excited about AI, not terrified of it. Cover it when there is a specific event, not as a recurring theme.

---

## 6. Trends 2026

Trends are not topics. A trend is a direction the audience is already moving. Content that moves with the trend gets algorithmic tailwind. Content that moves against it fights for every view.

### High Momentum — Cover Heavily

**AI agents doing multi-step tasks autonomously**
The shift from chatbot to agent — AI that books flights, writes code, sends emails without being asked each step — is the dominant conversation in 2026. Concrete examples perform best: "this agent spent $500 shopping for me while I slept."

**Running AI locally on consumer hardware**
Privacy plus cost plus offline access. "Llama 3 on a $300 laptop" hits multiple triggers simultaneously. The democratization frame — powerful AI without subscriptions or cloud dependency — resonates across technical and non-technical audiences.

**AI in specific professional workflows**
Not "AI for work" but "how lawyers use AI to review contracts in 4 minutes instead of 4 hours." The specificity of profession creates automatic audience segmentation — lawyers share it with other lawyers.

**Multimodal — AI that sees, hears, and reads simultaneously**
Demos of AI analyzing a photo, responding to a voice question, and generating a document in one conversation. Visual, demonstrable, shareable. The "magic" feeling is still present for general audiences who have not seen this format before.

### Declining Momentum — Use Sparingly

**General chatbot comparisons**
"ChatGPT vs Claude" content is saturated. The audience has seen it hundreds of times. Only viable with a very specific, new, counterintuitive angle — not as a format in itself.

**AI art generation as the primary subject**
The novelty of "AI made this painting" has passed for most audiences. It only works now as a capability demonstration inside a larger story, not as the story itself.

**General "AI is changing everything" framing**
Abstract claims about AI's broad impact no longer stop scrolls. The audience has been promised that AI changes everything for two years. Specificity is the only currency that still works.

### The Niche Decision

General AI news is the most competitive space. The highest-performing channel strategy for a new account is to own one specific intersection — "AI for small business owners" or "free AI tools only" — and be the definitive source for that audience before expanding. Bolt should start broader but have a pivot plan ready for month two based on which content pillar performs best in analytics.

---

## 7. Generation Stack

Each layer of the production process has a best-in-class free option and a best-in-class paid option. The stack is designed so the pipeline can start at zero cost and upgrade individual layers as revenue justifies it — without rebuilding the pipeline.

### Script Generation — Claude (Primary)

**Input:** Article title + summary + content pillar + Bolt character rules  
**Output:** 110-word Bolt script  
**Free tier:** $5 credit on signup, multi-key rotation extends this significantly  
**Paid upgrade:** Higher usage tier, same model

Claude is chosen because its instruction-following on voice and persona constraints is more consistent than alternatives. The specific requirement — stay in character, maintain word count, hook in first sentence, no forbidden phrases — is exactly the constrained generation task where Claude produces fewer retries. The multi-key pool means comma-separated API keys in the environment file are rotated automatically on credit exhaustion.

### Voice Synthesis

**Primary (free, unlimited): Edge-TTS**  
Microsoft Azure Neural voices accessed directly at zero cost with no API key and no rate limits. Voice: en-US-GuyNeural. Settings: +8% rate, +5Hz pitch, +10% volume. No account required. No monthly limit.

**Fallback (free, 1M chars/month): Google Cloud TTS**  
Neural2 voice quality is noticeably better than Edge-TTS. Free tier is generous enough for daily posting. Requires a Google Cloud account and a project with the API enabled.

**Paid upgrade: ElevenLabs**  
Voice cloning and emotional expressiveness are meaningfully better. 10K characters free per month, then paid tiers. The upgrade is justified when the channel starts earning — the difference in voice quality matters at scale when audience expectations have been set.

The pipeline tries Edge-TTS first and falls back upward through the chain. If Edge-TTS produces a valid audio file, no other service is called.

### Avatar Video

**Primary (free): Vidnoz**  
1900+ avatars, no watermark on free tier, no API key complexity. The free plan covers daily posting volume.

**Fallback (free, 20 videos/month): D-ID**  
Higher quality lip sync than Vidnoz. Free credits reset monthly. Used when Vidnoz is unavailable or when quality on a specific video warrants it.

**Paid upgrade: HeyGen**  
At $29/month, HeyGen offers the best lip sync quality and the most natural-looking results. The upgrade is justified when the channel reaches the point where production quality is the limiting factor on growth.

The avatar choice matters less than the script and voice — viewers forgive average avatar quality if the content is sharp. Do not pay for avatar quality before the content strategy is proven.

### B-Roll and Background — Kling AI (Free Daily Credits)

**Input:** Text prompt describing the visual  
**Output:** 5–10 second video clip  

Kling AI refreshes free credits daily, making it effectively unlimited for background clips. Used for tech-themed visuals — circuit boards, data flows, abstract AI imagery — that sit behind or alongside the avatar. Not used for the main presenter footage.

### Final Assembly — FFmpeg (Free, Open Source)

**Input:** Avatar MP4 + audio MP3 + logo PNG + lower third template  
**Output:** Final branded 9:16 MP4

FFmpeg handles all compositing: avatar footage scaled to 1080×1920, logo watermark in the corner, animated lower third with episode topic, SRT captions burned in. This layer is what makes the output look like a produced show rather than a raw avatar export. Runs locally — zero API cost, no rate limits, no external dependencies.

### Thumbnail Generation — Pillow + Brand Template (Free)

**Input:** Article title + template PNG  
**Output:** Platform-specific thumbnail JPG

Three templates — 16:9 for YouTube, 9:16 for TikTok and Instagram. Pillow overlays the title text in Bolt yellow on the dark blue brand background. The template is static; only the text changes per video. Consistency across thumbnails is more important than variety — viewers recognize Bolt thumbnails before they read the title.

### Publishing Scheduler — Buffer (Free, 3 Channels)

**Input:** Final MP4 + platform-specific caption  
**Output:** Scheduled posts on YouTube, TikTok, Instagram

Buffer's free tier covers all three platforms with 30 posts per channel per month — enough for daily posting. It handles platform terms of service compliance, retry logic, and optimal time scheduling. Direct platform APIs come later when Buffer's limits become the constraint, not before. Starting with direct APIs before proving the content strategy adds complexity with no benefit.

---

## 8. Full Pipeline Theory

### The Core Model

Everything in Bolt starts as an Article and ends as a Publication. The pipeline's only job is to transform one into the other through four deterministic stages. Every problem in a content automation pipeline traces back to violations of this principle.

```
Article → Script → Video → Publication
```

Each stage has one job. Each stage produces exactly one output. Each output becomes the next stage's input. Nothing skips stages. Nothing knows about stages other than its own.

### The State Machine

The pipeline is a state machine, not a script runner. Treating each step as a function call is why failures leave the system in an unknown state. Every model needs explicit states.

**Article states:**
`fetched → scored → queued → used | skipped`

**Script states:**
`generating → draft → pending_review → approved | rejected → published`

**Video states:**
`pending → audio_ready → avatar_ready → assembled | failed`

**Publication states:**
`scheduled → posted | failed → retrying | dead`

**Job states:**
`pending → running → done | failed → retrying | dead`

### How Modules Cooperate

The database is the only shared state. Modules do not communicate with each other directly. They communicate through the database.

```
news_aggregator    → writes Articles to DB
script_generator   → reads Article, writes Script to DB
video_pipeline     → reads Script, writes Video to DB
platform_publisher → reads Video, writes Publications to DB
analytics_tracker  → reads Publications, updates metrics in DB
```

No module imports another module. No module calls another module's functions. The master orchestrator is the only component allowed to call modules in sequence, and it does so by reading the current state from the database and deciding what to run next. The API server reads from the database and writes decisions to it — it never calls pipeline modules directly.

### The HITL Gate — Where Humans Intervene

The HITL gate is the only point where humans interact with the pipeline. It sits between script approval and video production, which is between the last cheap step and the first expensive step.

The pipeline is not one continuous process. It is two separate processes separated by the human decision.

**Process 1 — Script generation pipeline**
Runs on schedule. Produces a Script in pending_review state. Sends a notification with the script content and a CLI command to approve or reject. Exits. Done. It does not wait.

**Process 2 — Video and publish pipeline**
Runs when triggered by a job being created. A human approving through the dashboard or CLI creates a job record in the database. The job worker picks it up independently and runs video production followed by publishing. The scheduler never blocks — it creates jobs and moves on.

### The Scheduled Run — What Happens at 06:00 UTC

1. News aggregator fetches 17 feeds concurrently. Each entry becomes a candidate Article. Claude scores each on short-form video potential. Duplicates removed by title hash. Top 5 Articles written to database with status=queued.

2. Script generator reads the highest-scored Article. Determines today's content pillar from the day-of-week schedule. Sends article plus pillar plus Bolt character rules to Claude. Scores the result on hook strength, simplicity, Bolt voice, word count, and forbidden phrase check.
   - Score ≥ 9.0: status=approved, job created for video stage, continues automatically
   - Score 6.0–9.0: status=pending_review, notification sent with approve/reject instructions, pipeline exits
   - Score < 6.0: rejected, next Article tried, up to 3 attempts

3. If auto-approved: budget check before video stage. If daily or monthly budget is exceeded, the job is deferred. Otherwise video production begins.

4. Video production: Edge-TTS generates audio, Vidnoz generates avatar clip, FFmpeg assembles final video, thumbnails generated per platform. Video model written to database with file paths.

5. Publishing: Buffer receives final MP4 plus platform-specific caption. Three Publication records created — one per platform. YouTube posts at 14:00 local, Instagram at 12:00, TikTok at 19:00.

6. Analytics: 24 hours after posting, the analytics tracker fetches views, retention rate, likes, and comments from each platform. These update the Publication records and feed back into the Article scoring model over time. The feedback loop is what separates a pipeline from a self-improving system.

---

## 9. The Four Data Models

### Article

The rawest form of input. Immutable once created.

| Field | Type | Description |
|-------|------|-------------|
| content_id | string | Not set yet — assigned when Script is created |
| source | string | RSS feed name |
| title | string | Original article title |
| summary | string | First 1000 characters of article body |
| link | string | Source URL for verification |
| pillar | string | ai_news, ai_tools, ai_concepts, ai_daily_life |
| claude_score | float | 0–10, Claude's assessment of short-form video potential |
| heuristic_score | float | 0–10, keyword and recency scoring |
| age_hours | float | Hours since publication |
| published_iso | string | Original publication timestamp |
| fetched_at | string | When the pipeline fetched this article |
| status | string | fetched, scored, queued, used, skipped |

### Script

The central model. The only one with a human approval gate.

| Field | Type | Description |
|-------|------|-------------|
| content_id | string | bolt_YYYYMMDD_HHMMSS — immutable, travels to every table |
| article_id | int | Foreign key to articles table |
| pillar | string | Content pillar for this video |
| script | string | Bolt's 110-word spoken text |
| word_count | int | Must be 80–135 |
| overall_score | float | Claude's quality score |
| hook_strength | float | 0–10 |
| simplicity | float | 0–10 |
| bolt_voice | float | 0–10 |
| pacing | float | 0–10 |
| captions | json | Platform-specific titles and descriptions |
| status | string | draft, pending_review, approved, rejected, published |
| auto_approved | bool | True if score exceeded auto-approve threshold |
| review_decision | string | Human's reason if manually reviewed |
| generated_at | string | When Claude produced this script |
| approved_at | string | When it cleared the gate |

### Video

A derivation of a Script. If the Script changes, the Video is invalid.

| Field | Type | Description |
|-------|------|-------------|
| content_id | string | Same content_id as the parent Script |
| audio_path | string | Local path to the MP3 file |
| audio_provider | string | edge_tts, google_tts, elevenlabs |
| avatar_path | string | Local path to the avatar MP4 |
| avatar_provider | string | vidnoz, did, ffmpeg_fallback |
| final_path | string | Local path to the assembled final MP4 |
| thumbnail_path | string | Local path to the thumbnail image |
| video_ready | bool | True only when final_path exists and file is valid |
| status | string | pending, audio_ready, avatar_ready, assembled, failed |
| completed_at | string | When the final video was assembled |

### Publication

Append-only. One record per platform per video. Never updated — a new record is created for reposts.

| Field | Type | Description |
|-------|------|-------------|
| content_id | string | Same content_id as the parent Script |
| platform | string | youtube, tiktok, instagram |
| success | bool | Whether the post went live |
| post_url | string | URL of the live post |
| post_id | string | Platform's internal ID for the post |
| error_msg | string | Error description if success is false |
| scheduled_at | string | When Buffer was asked to post it |
| published_at | string | When it actually went live |
| views | int | Populated 24h later by analytics tracker |
| engagement_rate | float | Populated 24h later |

---

## 10. The Three Invariant Rules

These rules cannot be broken without corrupting the system. They are not conventions — they are architectural facts.

### Rule 1: content_id is immutable

Generated exactly once when a Script is created. Format: `bolt_YYYYMMDD_HHMMSS`. Travels unchanged to the Video table, every Publication record, every analytics snapshot, every cost event. Never derived from the article title, never truncated, never reformatted. Any code that uses anything other than the Script's content_id field as an identifier is wrong and will corrupt every join in the database.

### Rule 2: modules do not call modules

The only shared state is the database. The pipeline orchestrator reads state and decides what to run. Each module reads its input from the database, does its single job, writes its output to the database, and returns. No module imports another module. No module knows what stage comes before or after it. The orchestrator knows the sequence. The modules know only their own job.

### Rule 3: the pipeline never blocks

No stage waits for a human. No stage waits for the next stage. Each stage exits after writing its output to the database. The job worker connects stages asynchronously, running continuously in a separate process and picking up pending jobs from the database. The scheduler creates jobs and moves on. Blocking inside a scheduler daemon — waiting for a flag file, sleeping for hours — means the entire scheduled process is frozen. Jobs are the mechanism for async handoff between stages.

---

## Appendix A: Content Pillar Schedule

| Day | Pillar | Rationale |
|-----|--------|-----------|
| Monday | AI News | Start of week, news cycle reset, high news engagement |
| Tuesday | AI Tools | Mid-week productivity focus, tool discovery intent |
| Wednesday | AI Concepts | "Learn something" day, mid-week engagement |
| Thursday | AI News | Second news peak, Thursday is high engagement day |
| Friday | AI Tools | Weekend project preparation, free tool discovery |
| Saturday | AI Concepts | Longer content consumption day |
| Sunday | AI Daily Life | Reflective, personal, lower stakes |

---

## Appendix B: Bolt's Voice Parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| Voice | en-US-GuyNeural | Deep, authoritative, broadcast quality |
| Rate | +8% | Slightly faster than natural — energetic without feeling rushed |
| Pitch | +5Hz | Slightly higher — adds enthusiasm without artificiality |
| Volume | +10% | Slightly louder — clearer delivery in feed context |
| Fallback 1 | en-US-ChristopherNeural | Rich baritone, warm |
| Fallback 2 | en-US-EricNeural | Crisp, confident |
| Fallback 3 | en-GB-RyanNeural | British authority, distinctive |

---

## Appendix C: Posting Schedule

| Platform | Post Time (Local) | Reasoning |
|----------|-------------------|-----------|
| Instagram | 12:00 | Lunch break engagement peak |
| YouTube | 14:00 | Early afternoon, before the evening content rush |
| TikTok | 19:00 | Evening prime time, highest active user count |

---

*This document represents the complete pre-coding theory for Bolt AI. No implementation detail should contradict anything written here. When in doubt about an architectural decision, return to the three invariant rules and the four data models.*
