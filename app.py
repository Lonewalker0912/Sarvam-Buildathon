"""Generational Kitchen Wealth: Gradio UI. Run: .venv/bin/python app.py"""

from html import escape

import gradio as gr

from pipeline import LANGUAGE_NAMES, LANGUAGES, run

SCRIPTS = "தமிழ் · తెలుగు · हिन्दी · ಕನ್ನಡ · മലയാളം · বাংলা · मराठी · ગુજરાતી · ਪੰਜਾਬੀ · ଓଡ଼ିଆ"

HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,400&display=swap" rel="stylesheet">
"""

# Recipe books are paper: keep the page in light mode even if the OS is dark
FORCE_LIGHT = """
() => {
  document.body.classList.remove('dark');
  document.querySelector('.gradio-container')?.classList.remove('dark');
}
"""

CSS = """
:root {
  --paper: #FBF5EA; --card: #FFFDF8; --line: #EADFCB;
  --ink: #3B2A1E; --muted: #7A6553;
  --turmeric: #D99A1E; --chili: #B5482A; --leaf: #4F6B3A;
}
.gradio-container { max-width: 1120px !important; margin: 0 auto !important; }
footer { display: none !important; }

/* hero */
.hero { text-align: center; padding: 36px 16px 8px; }
.hero .eyebrow { display: inline-block; font-size: 12px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--chili); background: #F6E4D3; padding: 5px 12px; border-radius: 999px; }
.hero h1 { font-family: 'Fraunces', Georgia, serif; font-weight: 700; color: var(--ink);
  font-size: clamp(34px, 5.5vw, 56px); line-height: 1.05; margin: 16px 0 10px; }
.hero h1 em { font-style: italic; font-weight: 400; color: var(--chili); }
.hero p { color: var(--muted); font-size: 17px; max-width: 560px; margin: 0 auto; }
.hero .scripts { color: var(--turmeric); font-size: 15px; margin-top: 14px; opacity: .9; }

/* how it works */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 22px 0 6px; }
.step { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px;
  display: flex; gap: 12px; align-items: flex-start; }
.step .num { flex: none; width: 30px; height: 30px; border-radius: 50%; background: var(--turmeric); color: #fff;
  font-weight: 700; display: grid; place-items: center; font-family: 'Fraunces', serif; }
.step b { color: var(--ink); display: block; font-size: 15px; }
.step span { color: var(--muted); font-size: 13.5px; }
@media (max-width: 720px) { .steps { grid-template-columns: 1fr; } }

/* panels */
.panel-title { font-family: 'Fraunces', Georgia, serif; font-size: 22px; color: var(--ink); margin: 4px 0 2px; }
.hint { color: var(--muted); font-size: 13.5px; margin-bottom: 4px; }
#go-btn { font-size: 17px !important; padding: 14px !important; border-radius: 12px !important; }

/* recipe card */
.recipe { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 28px 30px;
  box-shadow: 0 1px 0 var(--line), 0 12px 32px -18px rgba(59,42,30,.35); position: relative; color: var(--ink); }
.recipe::before { content: ""; position: absolute; left: 0; top: 24px; bottom: 24px; width: 4px;
  border-radius: 0 4px 4px 0; background: var(--chili); }
.recipe h2 { font-family: 'Fraunces', Georgia, serif; font-size: 30px; line-height: 1.15; margin: 0 0 8px; color: var(--ink); }
.recipe h3 { font-family: 'Fraunces', Georgia, serif; font-size: 18px; color: var(--chili); margin: 22px 0 10px;
  padding-bottom: 6px; border-bottom: 1px dashed var(--line); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
.chip { font-size: 12.5px; padding: 3px 10px; border-radius: 999px; background: #F3EBDD; color: var(--muted); }
.chip.leaf { background: #E6EDDD; color: var(--leaf); }
.story { font-family: 'Fraunces', Georgia, serif; font-style: italic; font-size: 16.5px; color: var(--muted);
  border-left: 3px solid var(--turmeric); padding: 4px 0 4px 14px; margin: 16px 0 0; }
.ingredients { list-style: none; padding: 0; margin: 0; columns: 2; column-gap: 24px; }
.ingredients li { break-inside: avoid; padding: 6px 0; border-bottom: 1px solid #F3EBDD; font-size: 15px; }
.ingredients .qty { color: var(--chili); font-weight: 600; }
@media (max-width: 600px) { .ingredients { columns: 1; } }
.method { list-style: none; padding: 0; margin: 0; counter-reset: s; }
.method li { counter-increment: s; position: relative; padding: 4px 0 12px 42px; font-size: 15px; line-height: 1.55; }
.method li::before { content: counter(s); position: absolute; left: 0; top: 2px; width: 28px; height: 28px;
  border-radius: 50%; border: 1.5px solid var(--turmeric); color: var(--turmeric); font-weight: 700;
  display: grid; place-items: center; font-size: 13px; }
.tips { list-style: none; padding: 0; margin: 0; }
.tips li { padding: 4px 0 4px 26px; position: relative; font-size: 15px; }
.tips li::before { content: "🌿"; position: absolute; left: 0; }

/* empty state */
.empty { text-align: center; padding: 56px 28px; border: 2px dashed var(--line); border-radius: 18px;
  background: repeating-linear-gradient(var(--card) 0 31px, #F3EBDD 31px 32px); color: var(--muted); }
.empty .icon { font-size: 44px; }
.empty h2 { font-family: 'Fraunces', Georgia, serif; color: var(--ink); font-size: 24px; margin: 10px 0 6px; }

/* footer */
.made-with { text-align: center; color: var(--muted); font-size: 13px; padding: 18px 0 30px; }
.made-with .chip { margin: 2px; }
"""

EMPTY_CARD = """
<div class="empty">
  <div class="icon">🍲</div>
  <h2>Your family's first recipe will appear here</h2>
  <div>Ask a grandparent to tell you how they make their signature dish.<br>
  Stories, detours and "a little bit of this" are all welcome.</div>
</div>
"""


def render_card(result: dict) -> str:
    card = result["card"]
    lang = LANGUAGE_NAMES.get(result["language"], result["language"])
    chips = [f'<span class="chip">Heard in {escape(lang)} · {result["language_confidence"]:.0%}</span>']
    if card.get("serves"):
        chips.append(f'<span class="chip">Serves {escape(card["serves"])}</span>')
    voice = "In their own voice" if result["voice"] == "cloned" else "Read by Bulbul"
    chips.append(f'<span class="chip leaf">🔊 {voice}</span>')

    parts = [
        '<div class="recipe">',
        f'<div class="chips">{"".join(chips)}</div>',
        f'<h2>{escape(card.get("title", "Family recipe"))}</h2>',
    ]
    if card.get("story"):
        parts.append(f'<div class="story">"{escape(card["story"])}"</div>')
    parts.append("<h3>Ingredients</h3><ul class='ingredients'>")
    for i in card.get("ingredients", []):
        parts.append(f'<li><span class="qty">{escape(i.get("quantity", ""))}</span> {escape(i.get("item", ""))}</li>')
    parts.append("</ul><h3>Method</h3><ol class='method'>")
    parts += [f"<li>{escape(s)}</li>" for s in card.get("steps", [])]
    parts.append("</ol>")
    if card.get("tips"):
        parts.append("<h3>Family secrets</h3><ul class='tips'>")
        parts += [f"<li>{escape(t)}</li>" for t in card["tips"]]
        parts.append("</ul>")
    parts.append("</div>")
    return "".join(parts)


def process(audio, target_name, progress=gr.Progress()):
    if audio is None:
        raise gr.Error("Record or upload a recipe first.")
    sr, samples = audio
    steps = []

    def log(msg):
        steps.append(msg)
        progress(len(steps) / 5, desc=msg)

    try:
        result = run(samples, sr, LANGUAGES[target_name], log=log)
    except Exception as e:
        raise gr.Error(str(e))

    return render_card(result), result["audio_path"], result["narration_translated"], result["transcript"]


with gr.Blocks(title="Generational Kitchen Wealth") as demo:
    gr.HTML(f"""
    <div class="hero">
      <span class="eyebrow">Built with Sarvam AI</span>
      <h1>Generational <em>Kitchen</em> Wealth</h1>
      <p>Family recipes, passed down in the voice that taught them.
      Record a grandparent in their own language and keep the recipe forever.</p>
      <div class="scripts">{SCRIPTS}</div>
    </div>
    <div class="steps">
      <div class="step"><div class="num">1</div><div><b>Record</b>
        <span>A grandparent tells the recipe, in any Indian language.</span></div></div>
      <div class="step"><div class="num">2</div><div><b>Preserve</b>
        <span>We turn the story into a clear recipe card.</span></div></div>
      <div class="step"><div class="num">3</div><div><b>Pass it on</b>
        <span>Grandkids hear it in their language, in the grandparent's voice.</span></div></div>
    </div>
    """)

    with gr.Row(equal_height=False):
        with gr.Column(scale=5):
            gr.HTML('<div class="panel-title">Tell the recipe</div>'
                    '<div class="hint">Speak naturally, for up to 90 seconds. The first 15 seconds are used '
                    'to learn the voice, so start with clear speech.</div>')
            audio_in = gr.Audio(sources=["microphone", "upload"], type="numpy", show_label=False)
            target = gr.Dropdown(list(LANGUAGES), value="English", label="Who is it for? Pick the grandchild's language")
            go = gr.Button("✨ Preserve this recipe", variant="primary", elem_id="go-btn")

            gr.HTML('<div class="panel-title" style="margin-top:18px">Hear it again</div>')
            audio_out = gr.Audio(type="filepath", autoplay=True, show_label=False, interactive=False)
            with gr.Accordion("Narration text", open=False):
                narration = gr.Markdown()
            with gr.Accordion("What we heard (original words)", open=False):
                heard = gr.Markdown()

        with gr.Column(scale=7):
            card = gr.HTML(EMPTY_CARD)

    gr.HTML("""
    <div class="made-with">Powered by
      <span class="chip">Saaras · speech &amp; language ID</span>
      <span class="chip">sarvam-105b-conversations · recipe writing</span>
      <span class="chip">Mayura · translation</span>
      <span class="chip">Voice cloning · Bulbul</span>
    </div>
    """)

    go.click(process, [audio_in, target], [card, audio_out, narration, heard])

THEME = gr.themes.Base(
    primary_hue="orange",
    neutral_hue="stone",
    radius_size="lg",
    font=[gr.themes.GoogleFont("DM Sans"), "ui-sans-serif", "system-ui", "sans-serif"],
).set(
    body_background_fill="#FBF5EA",
    body_text_color="#3B2A1E",
    block_background_fill="#FFFDF8",
    block_border_color="#EADFCB",
    block_label_text_color="#7A6553",
    input_background_fill="#FFFDF8",
    input_border_color="#EADFCB",
    button_primary_background_fill="#B5482A",
    button_primary_background_fill_hover="#9A3B22",
    button_primary_text_color="#FFFFFF",
    button_secondary_background_fill="#F3EBDD",
    button_secondary_text_color="#3B2A1E",
)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2)
    demo.launch(theme=THEME, css=CSS, head=HEAD, js=FORCE_LIGHT)
