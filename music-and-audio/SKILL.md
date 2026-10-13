---
name: music-and-audio
description: "Music and audio production — songwriting craft, AI music generation prompts, music model orchestration (HeartMuLa, Suno), and audio visualization (spectrograms, MFCC)"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [music, audio, songwriting, suno, heartmula, generation, spectrogram, visualization]
---

# Music & Audio Production

Covers the full music/audio pipeline: **songwriting and lyric craft**, **AI music generation prompts** (Suno), **open-source model generation** (HeartMuLa), and **audio visualization/analysis** (spectrograms, MFCC, chroma).

---

## Section 1: Songwriting & Lyric Craft

### Song Structure (Pick or Invent)

```
ABABCB  Verse/Chorus/Verse/Chorus/Bridge/Chorus    (most pop/rock)
AABA    Verse/Verse/Bridge/Verse                    (jazz standards)
ABAB    Verse/Chorus alternating                     (simple/direct)
AAA     Verse/Verse/Verse (strophic)                 (folk, storytelling)
```

Six building blocks: **Intro** → **Verse** → **Pre-Chorus** → **Chorus** → **Bridge** → **Outro**

### Rhyme Types (from tight to loose)

- **Perfect**: lean/mean
- **Family**: crate/braid
- **Assonance**: had/glass (same vowels)
- **Consonance**: scene/when (similar endings)
- **Near/slant**: enough to suggest connection

Mix them. All perfect rhymes sound like a nursery rhyme. All slant rhymes sound lazy.

### Key Songwriting Tips

- **Show, don't tell**: "Your hoodie's still on the hook by the door" > "I was sad"
- **Internal rhyme**: Rhyming within a line, not just at ends
- **Meter**: Stressed syllables matter more than total count. Say it out loud.
- **Energy mapping**: Intro 2-3 → Verse 5-6 → Pre-Chorus 7 → Chorus 8-9 → Bridge varies → Final Chorus 9-10
- **Contrast**: Whisper before a scream hits harder. Silence is an instrument.

### Parody/Adaptation

1. Map the original structure (count syllables per line, mark rhyme scheme, note stressed syllables)
2. Match stressed syllables to the same beats
3. On long held notes, match the VOWEL SOUND of the original
4. Monosyllabic swaps keep rhythm intact (Crime → Code, Snake → Noose)
5. Keep some original lines intact for recognizability

---

## Section 2: Suno AI Prompt Engineering

### Style/Genre Description

**Formula:** Genre + Mood + Era + Instruments + Vocal Style + Production + Dynamics

**Bad:** `"sad rock song"`
**Good:** `"Cinematic orchestral spy thriller, 1960s Cold War era, smoky sultry female vocalist, big band jazz, brass section with trumpets, sweeping strings, minor key, vintage analog warmth"`

Describe the journey, not just the genre:
```
"Begins as a haunting whisper over sparse piano. Gradually layers in muted brass. Builds through the chorus with full orchestra. Second verse erupts with raw belting intensity. Outro strips back to a lone piano and a fragile whisper."
```

**Tips:**
- No artist names/trademarks. Describe the sound instead.
- Specify BPM and key when possible
- Use **Exclude Styles** for what you DON'T want
- Unexpected combos: "bossa nova trap", "Appalachian gothic", "chiptune jazz"
- Build a vocal PERSONA: "A weathered torch singer with a smoky alto"

### Metatags (in [brackets] in lyrics field)

| Category | Tags |
|----------|------|
| Structure | `[Intro] [Verse] [Pre-Chorus] [Chorus] [Bridge] [Outro] [Interlude] [Instrumental] [Guitar Solo] [Build-up] [Breakdown]` |
| Vocal | `[Whispered] [Spoken Word] [Belted] [Falsetto] [Raspy] [Breathy] [Soulful] [Harmonies] [Choir]` |
| Dynamics | `[High Energy] [Low Energy] [Building Energy] [Explosive] [Emotional Climax] [Gradual swell]` |
| Atmosphere | `[Melancholic] [Euphoric] [Nostalgic] [Aggressive] [Dreamy] [Intimate] [Dark Atmosphere]` |
| SFX | `[Vinyl Crackle] [Rain] [Applause] [Static] [Thunder]` |

### Phonetic Tricks for AI Vocalists

- Spell words as they sound: "through" → "thru", "Nous" → "Noose"
- ALL CAPS = louder, more intense
- Vowel extension: "lo-o-o-ove" = melisma
- Hyphenated stretch: "ne-e-ed" = emotional stretch
- Spell out numbers: "24/7" → "twenty four seven"

---

## Section 3: HeartMuLa — Open-Source Music Generation

Generate music from lyrics + tags. Apache-2.0 model family.

### Hardware
- Minimum: 8GB VRAM with `--lazy_load true`
- Recommended: 16GB+ VRAM
- 3B model with lazy_load peaks at ~6.2GB VRAM

### Installation

```bash
git clone https://github.com/HeartMuLa/heartlib.git && cd heartlib
uv venv --python 3.10 .venv && . .venv/bin/activate
uv pip install -e .
uv pip install --upgrade datasets transformers  # fix dependency conflicts
```

### Download Checkpoints

```bash
hf download --local-dir './ckpt' 'HeartMuLa/HeartMuLaGen'
hf download --local-dir './ckpt/HeartMuLa-oss-3B' 'HeartMuLa/HeartMuLa-oss-3B-happy-new-year'
hf download --local-dir './ckpt/HeartCodec-oss' 'HeartMuLa/HeartCodec-oss-20260123'
```

### Usage

```bash
python ./examples/run_music_generation.py \
  --model_path=./ckpt --version="3B" \
  --lyrics="./assets/lyrics.txt" --tags="./assets/tags.txt" \
  --save_path="./assets/output.mp3" --lazy_load true
```

**Tags format** (comma-separated, no spaces): `piano,happy,wedding,synthesizer,romantic`

**Lyrics format** (use bracketed structural tags):
```
[Verse]
Your lyrics here...
[Chorus]
Chorus lyrics...
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--max_audio_length_ms` | 240000 | Max length (240s) |
| `--topk` | 50 | Top-k sampling |
| `--temperature` | 1.0 | Sampling temperature |
| `--cfg_scale` | 1.5 | Classifier-free guidance |
| `--lazy_load` | false | Load/unload on demand |
| `--mula_dtype` | bfloat16 | HeartMuLa dtype |
| `--codec_dtype` | float32 | HeartCodec dtype (fp32!) |

### Pitfalls

- **Do NOT use bf16 for HeartCodec** — degrades quality. Use fp32.
- Tags may be ignored (known issue #90); lyrics tend to dominate
- Triton not available on macOS
- Need source patches for transformers 5.x compatibility (ROPE cache + VQ codebook mismatch)

---

## Section 4: Audio Visualization (Songsee)

Generate spectrograms and multi-panel audio feature visualizations from audio files.

### Installation

```bash
go install github.com/steipete/songsee/cmd/songsee@latest
```

Or: download the static binary from the releases page.

### Usage

```bash
# Basic spectrogram
songsee track.mp3

# Multi-panel visualization grid
songsee track.mp3 --viz spectrogram,mel,chroma,hpss,selfsim,loudness,tempogram,mfcc,flux

# Time slice
songsee track.mp3 --start 12.5 --duration 8 -o slice.jpg

# From stdin
cat track.mp3 | songsee - --format png -o out.png
```

### Visualization Types

| Type | Description |
|------|-------------|
| `spectrogram` | Standard frequency spectrogram |
| `mel` | Mel-scaled spectrogram |
| `chroma` | Pitch class distribution |
| `hpss` | Harmonic/percussive separation |
| `selfsim` | Self-similarity matrix |
| `loudness` | Loudness over time |
| `tempogram` | Tempo estimation |
| `mfcc` | Mel-frequency cepstral coefficients |
| `flux` | Spectral flux (onset detection) |

### Common Flags

`--style classic|magma|inferno|viridis|gray`, `--width`, `--height`, `--window`, `--hop`, `--min-freq`, `--max-freq`, `--format jpg|png`

### Notes

- WAV and MP3 decoded natively; other formats require ffmpeg
- Output images can be inspected with `vision_analyze` for automated audio analysis