"""Measure a single live conversation until three adjacent turns settle."""
from pathlib import Path
import statistics
import sys
import time

import jinja2

WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(WORK / 'basalt-latest' / 'tools'))
from gguf_reader import GGUFFile
from tokenizer import Tokenizer

PACK = WORK.parent / 'strata-deepseek/data/packs/deepseek-v4.1-flash-ist-das-2.00bpw/tokenizer'

def chat_codec(gguf):
    meta = GGUFFile(gguf).metadata
    tokenizer = Tokenizer.from_metadata(meta)
    template = jinja2.Environment(trim_blocks=True, lstrip_blocks=True).from_string(
        (PACK / 'chat_template.jinja').read_text()
    )
    def encode(messages):
        rendered = template.render(messages=messages, add_generation_prompt=True,
                                   enable_thinking=False, thinking=False,
                                   thinking_mode='chat', tools=None)
        return tokenizer.encode(rendered, parse_special=True)
    return encode, tokenizer

QUESTIONS = (
    'How could my neighborhood start a small community library from an empty storefront?',
    'How would we make it welcoming to kids, older adults, and people who work evenings?',
    'What would you say to a neighbor who worries the library might get too noisy?',
    'How can the volunteers divide the work and handle disagreements constructively?',
    'What would you ask the owner of the storefront during a walk-through?',
    'What could we do with a very small budget in the first month?',
    'Tell me how the opening afternoon might go, from a new visitor’s perspective.',
    'How would you gather useful feedback from people who rarely come in?',
    'How can we build a good relationship with the nearby public library?',
    'What would you do if attendance drops after the first few weeks?',
    'What could a volunteer say to welcome someone who seems unsure about entering?',
    'Imagine the library one year later. What signs would tell us it is working?',
)

def measure_chat(proc, line, cfg):
    gguf = cfg['deepseek_storage_evidence']['expert_files'][0]['path']
    encode, tokenizer = chat_codec(gguf)
    messages, rows = [], []
    for question in QUESTIONS:
        messages.append({'role': 'user', 'content': question + ' Give a detailed answer in natural prose.'})
        ids = encode(messages)
        start = time.monotonic()
        proc.stdin.write('GEN 256 temperature=0 seed=42 ' + ','.join(map(str, ids)) + '\n')
        proc.stdin.flush()
        tokens, arrivals = [], []
        while True:
            event = line()
            if event.startswith('ERR'):
                raise RuntimeError(event)
            if event.startswith('T '):
                tokens.append(int(event.split()[1]))
                arrivals.append(time.monotonic())
            if event.startswith('DONE '):
                break
        if len(arrivals) < 2:
            raise RuntimeError('Chat ended before decode could be timed')
        first = min(31, len(arrivals) // 2)
        rate = (len(arrivals) - 1 - first) / (arrivals[-1] - arrivals[first])
        row = dict(turn=len(rows)+1, prompt=len(ids), generated=len(tokens),
                   reused_tokens=int(event.split()[8]) if len(event.split())>8 else 0,
                   ttft_s=arrivals[0]-start, decode_tok_s=rate)
        rows.append(row)
        import json
        print('CHAT', json.dumps(row), flush=True)
        messages.append({'role':'assistant', 'content':tokenizer.decode(tokens).split('<｜end▁of▁sentence｜>')[0]})
        rates = [row['decode_tok_s'] for row in rows[-3:]]
        if len(rows) >= 4 and (max(rates)-min(rates)) <= .05*statistics.median(rates):
            return rows, True
    return rows, False
